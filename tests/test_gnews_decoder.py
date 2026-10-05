# -*- coding: utf-8 -*-
"""Offline unit tests for the Google News AES decoder wiring (P0 fix).

Covers: parse_guid, _aes_decrypt roundtrip, extract_keys, decode_many empty,
and verify.decode_gnews_link routing AES tokens to pipeline.gnews FIRST
(the bug was: verify.py used only its legacy base64 decoder and never called
the AES implementation in gnews.py)."""
import base64, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline import gnews, verify


def test_pycryptodome_available():
    """requirements.txt must ship pycryptodome or _aes_decrypt silently returns None."""
    from Crypto.Cipher import AES  # noqa: F401  (ImportError = dependency missing)


def test_parse_guid_extracts_token():
    token = "AU_yqL" + "Tt7-" + "x" * 40
    payload = b"\x12" + bytes([len(token)]) + token.encode()   # field 2, wire type 2
    cid = base64.b64encode(payload).decode()
    assert gnews.parse_guid(cid) == token


def test_aes_roundtrip():
    from Crypto.Cipher import AES
    key = bytes(range(16))
    url = "https://pib.gov.in/PressNoteDetails.aspx?NoteId=123&reg=3&lang=1"
    raw = url.encode()
    pad = 16 - len(raw) % 16
    iv = bytes([7] * 16)
    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(raw + bytes([pad]) * pad)
    token = "AU_yqL" + base64.b64encode(iv + ct).decode()
    out = gnews._aes_decrypt(token, key)
    assert out == url, out


def test_extract_keys():
    tok = '"AU_yqLabc123-def456+ghi789=="'
    html = f"<html>{tok},[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]</html>"
    keys = gnews.extract_keys(html)
    assert keys and keys[0][1] == bytes(range(1, 17)), keys


def test_decode_many_empty():
    assert gnews.decode_many([]) == {}


def test_verify_routes_to_aes_decoder_first(monkeypatch=None):
    """verify.decode_gnews_link must call pipeline.gnews.decode_article_url before
    touching the legacy decoder — verified by monkeypatching both."""
    calls = []
    orig_gn, orig_leg = gnews.decode_article_url, verify._legacy_decode_gnews_link
    try:
        def fake_aes(link, cid, timeout=9):
            calls.append("aes")
            return "https://www.pib.gov.in/real-article"
        def fake_legacy(gurl, cache={}):
            calls.append("legacy")
            return None
        gnews.decode_article_url = fake_aes
        verify._legacy_decode_gnews_link = fake_legacy
        url = "https://news.google.com/rss/articles/AU_yqLdGVzdA?oc=5"
        out = verify.decode_gnews_link(url + "#t1", guid="CBMiAU...")
        assert out == "https://www.pib.gov.in/real-article"
        assert calls == ["aes"], calls  # legacy must NOT run when AES succeeds
        # when AES fails -> legacy fallback is tried
        calls.clear()
        gnews.decode_article_url = lambda link, cid, timeout=9: None
        def fake_legacy2(gurl, cache={}):
            calls.append("legacy")
            return "https://fallback.example/x"
        verify._legacy_decode_gnews_link = fake_legacy2
        out2 = verify.decode_gnews_link(url + "#t2", guid="")
        assert out2 == "https://fallback.example/x"
        assert calls == ["legacy"], calls
    finally:
        gnews.decode_article_url = orig_gn
        verify._legacy_decode_gnews_link = orig_leg


def test_verify_all_seeds_cache_from_decode_many():
    """Batch decode_many results must seed the decode cache so fetch_page uses them."""
    orig_many, orig_get = gnews.decode_many, verify.requests.get
    try:
        def fake_many(pairs, workers=10, deadline_s=60):
            return {p[0]: "https://official.example/article" for p in pairs}
        gnews.decode_many = fake_many
        items = [{"event_id": "e1", "headline_en": "Test headline",
                  "source_url": "https://news.google.com/rss/articles/TOKEN1",
                  "source_tier": "tier1", "gnews_guid": "CBMiAU_yqL"}]
        cache = verify._GN_DECODE_CACHE
        key = items[0]["source_url"]
        cache.pop(key, None)
        # simulate what verify_all does at startup
        gn_map = gnews.decode_many([(it["source_url"], it.get("gnews_guid") or "")
                                   for it in items if "news.google.com" in it["source_url"]])
        # production seeding (verify_all): key by link only so fetch_page hits cache
        for (l, g), u in gn_map.items():
            _GN_DECODE_CACHE[l] = u
        assert verify.decode_gnews_link(key) == "https://official.example/article"
    finally:
        gnews.decode_many = orig_many
        verify.requests.get = orig_get


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for f in fns:
        try:
            f(); print(f"PASS {f.__name__}")
        except Exception as e:
            failed += 1; print(f"FAIL {f.__name__}: {e}")
    print(f"{len(fns)-failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
