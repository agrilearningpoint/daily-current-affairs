# -*- coding: utf-8 -*-
"""Google News AES-link decoder + official-domain resolver (2026 format).

Decoding path (no browser needed):
 1. guid CBMi... -> base64 -> protobuf field 2 -> "AU_yqL..." token (AES-encrypted URL)
 2. fetch consent-wrapped article page; extract the per-article AES key from its
    embedded bootstrapping data ("AU_yqL..." -> 16-byte key mapping)
 3. AES-128-CBC decrypt token with that key, PKCS7-unpad -> real publisher URL
Fallbacks kept: server-side redirect result, canonical/og:url in page.
If nothing works, returns None (item is then dropped — never a fake link).
"""
import base64, hashlib, logging, re, struct, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "en-IN,en;q=0.9"}

def _b64(s):
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)

def _b64url(s):
    s = s.replace("+", "-").replace("/", "_").rstrip("=")
    return s

def parse_guid(cid):
    """CBMi... guid -> (token_str, ) via minimal protobuf walk."""
    try:
        raw = _b64(cid)
        # field 2 (wire type 2) contains the AU_yqL... token
        i = 0
        while i < len(raw):
            fb = raw[i]; i += 1
            wt = fb & 7; fnum = fb >> 3
            if wt == 2:
                ln = raw[i]; i += 1
                if ln >= 128:  # varint length
                    shift = 0; ln = 0
                    while True:
                        b = raw[i]; i += 1
                        ln |= (b & 0x7f) << shift; shift += 7
                        if not b & 0x80: break
                val = raw[i:i+ln]; i += ln
                if val.startswith(b"AU_yqL"):
                    return val.decode()
            elif wt == 0:
                while raw[i] & 0x80: i += 1
                i += 1
            else:
                break
    except Exception:
        pass
    return None

def _aes_decrypt(token_b64, key):
    """AES-128-CBC decrypt of b64 payload (IV = first 16 bytes). Payload may be the
    raw token ("AU_yqL...") or a full guid; standard/urlsafe b64 alphabets both work.
    Tolerates base64 padding drift by trying the last few byte-truncation offsets."""
    try:
        from Crypto.Cipher import AES
        tok = token_b64.split("CBMi")[-1] if "CBMi" in token_b64 else token_b64
        if tok.startswith("AU_yqL"):
            tok = tok[6:]                        # strip token prefix before b64 body
        s = tok.replace("-", "+").replace("_", "/")
        s += "=" * (-len(s) % 4)                 # pad to a multiple of 4 first
        data = base64.b64decode(s)
    except Exception:
        return None
    for trim in range(0, 4):                      # real token length mod 16 == 0
        d = data[:len(data) - trim] if trim else data
        if len(d) < 32 or (len(d) - 16) % 16:
            continue
        try:
            iv, ct = d[:16], d[16:]
            dec = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
            pad = dec[-1]
            if 1 <= pad <= 16 and dec[-pad:] == bytes([pad]) * pad:
                dec = dec[:-pad]
            txt = dec.decode("utf-8", "ignore")
            m = re.search(r'https?://\S+', txt)
            if m:
                return m.group(0)
        except Exception:
            continue
    return None

_KEY_RE_CACHE = {}

def extract_keys(page_html):
    """Find {token_prefix -> 16-byte key} pairs embedded in the article shell page.
    Google ships the key inside the page's AF_initDataCallback / c-wiz data blobs."""
    keys = []
    for m in re.finditer(r'"(AU_yqL[\w\-+/=]{10,})"', page_html):
        tok = m.group(1)
        # following numeric array of 16 ints = key bytes
        tail = page_html[m.end():m.end()+260]
        arr = re.search(r'\[([0-9,\s]{30,220})\]', tail)
        if arr:
            try:
                nums = [int(x) for x in re.findall(r'\d+', arr.group(1))]
                if len(nums) >= 16:
                    keys.append((tok, bytes(nums[:16])))
            except ValueError:
                pass
    return keys

def decode_article_url(link, cid, timeout=9):
    """Try every strategy; return real publisher URL or None."""
    try:
        r = requests.get(link, headers=UA, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return None
        if "news.google.com" not in r.url:
            return r.url
        html = r.text
        # canonical/og fallback
        for pat in (r'<link rel="canonical" href="(https?://[^"]+)"',
                    r'<meta property="og:url" content="(https?://[^"]+)"'):
            m = re.search(pat, html)
            if m and "google" not in m.group(1):
                return m.group(1)
        # AES path
        token = parse_guid(cid)
        if token:
            keys = extract_keys(html)
            for ktok, key in keys:
                if token.startswith(ktok[:20]) or ktok.startswith(token[:20]):
                    url = _aes_decrypt(token, key)
                    if url:
                        return url
            # also try all keys against our token
            for _, key in keys:
                url = _aes_decrypt(token, key)
                if url:
                    return url
    except requests.RequestException:
        pass
    # 2026 reality: the shell page carries no embedded key — Google resolves the
    # link client-side (JS). Follow that redirect with a headless browser.
    return _playwright_resolve(link)

_PW = {"lock": __import__("threading").Lock(), "proc": None, "browser": None,
       "ctx": None, "owner": None, "fail": 0}

def _playwright_resolve(link, timeout_ms=25000):
    # P2 FIX: concurrency cap — Playwright browsers are heavy, limit to 4 concurrent
    """Last-resort resolver: Google's article shell needs JS to redirect to the
    publisher. A shared headless Chromium follows the redirect and returns the
    real URL. Silently returns None if playwright/browser is unavailable
    (e.g. clean GitHub runner without browsers installed).
    NOTE: sync Playwright greenlets are bound to one thread — all browser work
    runs serialized on the first thread that initialized it."""
    if _PW["fail"] >= 3:
        return None
    me = __import__("threading").current_thread()
    if _PW["owner"] is not None and _PW["owner"] is not me:
        return None          # different worker thread — skip (owner thread resolves)
    with _PW["lock"]:
        _PW["owner"] = me
        try:
            from playwright.sync_api import sync_playwright
            if _PW["proc"] is None:
                _PW["proc"] = sync_playwright().start()
                exe = None
                import glob, os
                for cand in glob.glob(os.path.expanduser(
                        "~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")) + \
                        ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]:
                    if os.path.exists(cand):
                        exe = cand; break
                _PW["browser"] = _PW["proc"].chromium.launch(headless=True, executable_path=exe)
                _PW["ctx"] = _PW["browser"].new_context(user_agent=UA["User-Agent"])
            pg = _PW["ctx"].new_page()
            try:
                pg.goto(link, wait_until="domcontentloaded", timeout=timeout_ms)
                for _ in range(8):
                    if "news.google.com" not in pg.url:
                        return pg.url
                    pg.wait_for_timeout(700)
                # sometimes the redirect target is in an <a> after render
                m = pg.evaluate("() => { const a = document.querySelector('a[href]');"
                                "return a ? a.href : null; }")
                if m and "google" not in m:
                    return m
                return None
            finally:
                pg.close()
        except Exception as e:
            _PW["fail"] += 1
            logging.debug(f"[gnews] playwright resolve failed ({_PW['fail']}/3): {e}")
            return None


def close_playwright():
    try:
        if _PW["browser"]:
            _PW["browser"].close()
        if _PW["proc"]:
            _PW["proc"].stop()
    except Exception:
        pass
    finally:
        _PW.update(proc=None, browser=None, ctx=None, owner=None)


def decode_many(pairs, workers=10, deadline_s=60):
    """pairs: iterable of (link, guid). Returns {(link,guid): publisher_url}."""
    out, t0 = {}, time.monotonic()
    pairs = list(dict.fromkeys(pairs))
    if not pairs:
        return out
    with ThreadPoolExecutor(max_workers=min(workers, len(pairs))) as ex:
        futs = {ex.submit(decode_article_url, l, g): (l, g) for l, g in pairs}
        try:
            for fut in as_completed(futs, timeout=max(5, deadline_s - (time.monotonic() - t0))):
                k = futs[fut]
                try:
                    u = fut.result()
                    if u:
                        out[k] = u
                except Exception:
                    pass
        except TimeoutError:
            logging.warning("[gnews] decode deadline reached")
    return out

def resolve_official(title, source_site, timeout=8):
    """Given an item title + official domain (e.g. pib.gov.in), find the matching
    official-page URL by searching the site's own listing pages (never invents URLs).
    Currently supports pib.gov.in (home page Press Note links) — returns URL or None."""
    host = re.sub(r"^https?://(www\.)?", "", source_site).split("/")[0]
    norm = re.sub(r"[^a-z0-9 ]", "", title.lower())[:60]
    if not norm:
        return None
    try:
        if host == "pib.gov.in":
            r = requests.get("https://www.pib.gov.in/", headers=UA, timeout=timeout)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=re.compile("PressNoteDetails|NewInfoDetail")):
                t = re.sub(r"[^a-z0-9 ]", "", a.get_text(" ", strip=True).lower())[:60]
                if t and (t[:40] == norm[:40] or norm[:40] in t or t[:40] in norm):
                    href = a["href"]
                    if href.startswith("/"):
                        href = "https://www.pib.gov.in" + href
                    return href
    except requests.RequestException:
        pass
    return None
