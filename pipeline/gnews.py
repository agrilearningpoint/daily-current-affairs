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
    """AES-128-CBC decrypt of urlsafe-b64 payload (IV = first 16 bytes)."""
    try:
        from Crypto.Cipher import AES
        data = _b64(token_b64)
        iv, ct = data[:16], data[16:]
        dec = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
        pad = dec[-1]
        if 1 <= pad <= 16 and dec[-pad:] == bytes([pad]) * pad:
            dec = dec[:-pad]
        txt = dec.decode("utf-8", "ignore")
        m = re.search(r'https?://\S+', txt)
        return m.group(0) if m else None
    except ImportError:
        return None
    except Exception:
        return None

_KEY_RE_CACHE = {}

def extract_keys(page_html):
    """Find {token_prefix -> 16-byte key} pairs embedded in the article shell page.
    Google ships the key inside the page's AF_initDataCallback / c-wiz data blobs."""
    keys = []
    for m in re.finditer(r'"(AU_yqL[\w\-]{10,})"', page_html):
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
    return None

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
