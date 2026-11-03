# -*- coding: utf-8 -*-
"""
DISCOVERY APIs — Serper.dev (Google Search) + GNews.io v4
==========================================================
Standalone, env-gated helpers for primary-source discovery and news top-up.
Keys: SERPER_API_KEY (2500 free credits), GNEWS_API_KEY (100 req/day free).
Design rules:
  - No key => graceful empty result (never raises for missing config).
  - Network errors => logged + empty result (callers decide fallbacks).
  - Never invents URLs; returns exactly what the APIs return.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = int(os.getenv("ALP_DISCOVERY_TIMEOUT", "15"))


def serper_search(query: str, num: int = 5, gl: str = "in") -> List[Dict[str, Any]]:
    """Google Search via Serper.dev. Returns [{title, link, snippet, date?}, ...]."""
    key = os.environ.get("SERPER_API_KEY", "").strip()
    if not key:
        return []
    try:
        r = requests.post("https://google.serper.dev/search",
                          headers={"X-API-KEY": key, "Content-Type": "application/json"},
                          json={"q": query, "gl": gl, "num": min(num, 10)},
                          timeout=_TIMEOUT)
        if r.status_code != 200:
            logger.warning(f"[discovery] serper {r.status_code}: {r.text[:120]}")
            return []
        return r.json().get("organic", []) or []
    except Exception as exc:
        logger.warning(f"[discovery] serper fail: {exc}")
        return []


def fetch_gnews_api(query: str, lang: str = "en", country: str = "in",
                    max_articles: int = 10) -> List[Dict[str, Any]]:
    """GNews.io v4 search. Returns [{title, description, url, source{name}, publishedAt, image}, ...]."""
    key = os.environ.get("GNEWS_API_KEY", "").strip()
    if not key:
        return []
    try:
        r = requests.get("https://gnews.io/api/v4/search",
                         params={"q": query, "lang": lang, "country": country,
                                 "max": min(max_articles, 10), "apikey": key},
                         timeout=_TIMEOUT)
        if r.status_code != 200:
            logger.warning(f"[discovery] gnews {r.status_code}: {r.text[:120]}")
            return []
        return r.json().get("articles", []) or []
    except Exception as exc:
        logger.warning(f"[discovery] gnews fail: {exc}")
        return []


# Official/primary domains used for mirror discovery (tier-2 -> primary upgrade)
OFFICIAL_HOSTS = (
    "pib.gov.in", "agricoop.nic.in", "icar.org.in", "rbi.org.in", "nabard.org",
    "sebi.gov.in", "mospi.gov.in", "niti.gov.in", "mea.gov.in", "mausam.imd.gov.in",
    "isro.gov.in", "drdo.gov.in", "india.gov.in", "pmindia.gov.in", "mof.gov.in",
    "fssai.gov.in", "apeda.gov.in", "nhb.gov.in", "dahd.gov.in", "fao.org",
    "worldbank.org", "imf.org", "wto.org", "who.int",
)


def find_official_mirror(title: str, extra_hosts: tuple = ()) -> str | None:
    """Serper site-restricted search for the official page of a news title.
    Returns an official-domain URL whose page title closely matches, else None.
    Never invents URLs — only returns links Google actually indexed."""
    if not title or not os.environ.get("SERPER_API_KEY"):
        return None
    norm = re.sub(r"[^a-z0-9 ]", "", title.lower())
    words = [w for w in norm.split() if len(w) > 3][:8]
    if len(words) < 3:
        return None
    phrase = " ".join(words)
    hosts = tuple(dict.fromkeys(OFFICIAL_HOSTS + tuple(extra_hosts)))
    # one combined query: site:a OR site:b ... "key phrase"
    site_q = " OR ".join(f"site:{h}" for h in hosts[:12])
    for res in serper_search(f"({site_q}) {phrase}", num=6):
        link = res.get("link", "")
        rtitle = re.sub(r"[^a-z0-9 ]", "", (res.get("title") or "").lower())
        overlap = sum(1 for w in words if w in rtitle)
        if overlap >= max(3, len(words) // 2) and any(h in link for h in hosts):
            logger.info(f"[discovery] official mirror: {link[:90]}")
            return link
    return None
