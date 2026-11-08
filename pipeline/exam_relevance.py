# -*- coding: utf-8 -*-
"""Exam relevance for agri / banking aspirants (AGTA, AFO, NABARD, IBPS, RBI, FCI).

Shared by the daily relevance stage (agents/07_student_domain_relevance.py) and
the weekly/monthly period builder (pipeline/period_builder.py).

Audit of weekly_2026-11-08: state party sound-bites (Stalin / Palaniswami on TN
GST, DVAC vs E.V. Velu), a "US stocks: 5 platforms" listicle, a BRICS opinion
piece and local poll results made the paid edition (four of them on the cover),
while Cabinet decisions, the Khet Bachaao Abhiyaan and the International Maize
Conference were buried or missing.

``drop_reason(item)``  -> why an item is not exam news at all ("" = keep);
``boost(item)``        -> extra points for the exam's core (Cabinet, agriculture
                          ministry, ICAR, RBI agri credit, schemes), capped;
``is_boosted(item)``   -> part of the boosted set (cover / top-story pool);
``exam_score(item)``   -> importance + boost (- soft penalty).
"""
from __future__ import annotations

import re
from typing import Any, Dict, Tuple

# --------------------------------------------------------------------------- #
# Not exam news
# --------------------------------------------------------------------------- #
# State party politics: named state leaders / parties + a statement verb, local
# poll results, vigilance raids on politicians.
_STATE_LEADERS = (r"stalin|palaniswami|edappadi|\beps\b|udhayanidhi|annamalai|e\.?\s?v\.?\s?velu|\bvelu\b|"
                  r"kanimozhi|vijay['’]?s?\s+tvk|seeman|ops\b|panneerselvam|siddaramaiah|shivakumar|revanth|"
                  r"\bkcr\b|ktr\b|jagan|chandrababu|naidu['’]s\s+tdp|pawan(?:\s+kalyan)?|mamata|abhishek\s+banerjee|"
                  r"akhilesh|mayawati|tejashwi|nitish|kejriwal|bhagwant\s+mann|fadnavis|uddhav|sharad\s+pawar|"
                  r"ajit\s+pawar|hemant\s+soren|vijayan|pinarayi|satheesan")
_PARTIES = (r"dmk|aiadmk|tvk|tamilaga\s+vettri\s+kazhagam|ysrcp|tdp|jana\s+sena|jsp|brs|tmc|trinamool|aap|bjd|"
            r"jd\(u\)|jdu|rjd|bsp|samajwadi|shiv\s+sena|ncp|(?<!us\s)(?<!u\.s\.\s)congress|bjp|cpi\(m\)|cpm|pmk|vck|mnm|naam\s+tamilar")
_STATEMENT = (r"says|said|slams?|alleges?|accus\w+|attacks?|claims?|criticis\w+|criticiz\w+|hails?|urges?|"
              r"demands?|expresses|blames?|questions|mocks?|taunts?|warns|vows|attributes?|hits\s+out|"
              r"lashes\s+out|concern|doomed|backs|rally|rallies|roadshow|campaign\w*|manifesto|joins|quits")
STATE_POLITICS_RE = re.compile(
    rf"(?:\b(?:{_STATE_LEADERS})\b.{{0,120}}\b(?:{_STATEMENT})\b"
    rf"|\b(?:{_STATEMENT})\b.{{0,80}}\b(?:{_STATE_LEADERS})\b"
    rf"|\b(?:{_PARTIES})\b.{{0,60}}\b(?:{_STATEMENT})\b"
    r"|\bdvac\b|\bvigilance\s+and\s+anti-?corruption\b"
    r"|\b(?:zptc|mptc|bypoll|by-election|local\s+body\s+(?:polls?|elections?)|poll\s+victor(?:y|ies)|"
    r"assembly\s+(?:polls?|elections?)\s+(?:campaign|rally|result))\b"
    r"|\b(?:party\s+workers|youth\s+wing|party['’]s\s+\w+\s+(?:zone|wing)|general\s+secretary\s+of\s+the\s+party)\b)",
    re.I)
# Market listicles / personal-finance explainers.
LISTICLE_RE = re.compile(
    r"\b(?:stocks?\s+to\s+(?:buy|watch|invest)|(?:investing|invest)\s+in\s+us\s+stocks|"
    r"\d+\s+(?:platforms|stocks|apps|ways|things|tips|mutual\s+funds|funds|reasons)\b|"
    r"check\s+(?:how|which|these|list|out)|here['’]?s\s+(?:how|what|why|where|the\s+list)|"
    r"best\s+\w+(?:\s+\w+)?\s+to\s+(?:buy|invest)|multibagger|top\s+picks|target\s+price|"
    r"should\s+you\s+(?:buy|invest|sell)|stack\s+up)\b", re.I)
# Opinion / analysis framing that the daily opinion filter (URL/section) can miss.
OPINION_HEAD_RE = re.compile(
    r"^(?:what|why|how)\b[^.?!]{3,90}\b(?:needs?|must|should|means?|matters?|got\s+wrong)\b"
    r"|\b(?:opinion|op-?ed|editorial|column|viewpoint|guest\s+column)\b|^the\s+case\s+(?:for|against)\b", re.I)
CRIME_RE = re.compile(
    r"\b(?:murder\w*|killed\s+by|shot\s+dead|stabb\w+|robbery|loot\w*|kidnap\w*|abduct\w*|"
    r"arrested|nabbed|smuggl\w+|drug\s+peddl\w+|extortion|chain\s+snatch\w*|"
    r"sexual\s+assault|molest\w*|gang-?rape|dowry\s+death|police\s+(?:arrest|seize|raid)\w*|"
    r"illegal\s+sand\s+mining|sand\s+mining\s+(?:case|charge))\b", re.I)
# Foreign conflict / commodity spot news with no India angle (one-liners #1, #10).
FOREIGN_CONFLICT_RE = re.compile(
    r"\b(?:russian?|ukrain\w*|israel\w*|gaza|hamas|hezbollah|houthi|pakistan\w*|iran\w*|zaporizhzhia|kyiv|kharkiv)\b"
    r".{0,80}\b(?:strikes?|attacks?|shell\w*|drones?|missiles?|killed|lng|cargo|blasts?|offensive|troops)\b"
    r"|\b(?:lng|cargo)\b.{0,40}\b(?:in|from|to)\s+(?:pakistan|iran|russia)\b",
    re.I)
_INDIA_RE = re.compile(r"\b(?:india|indian|new\s+delhi|union\s+cabinet)\b|(?:^|\bthe\s+)centre\b|\bcentre['’]s\b", re.I)
# Official exceptions: the Cabinet / courts / commissions acting on crime or polls are exam news.
_OFFICIAL_EXCEPTION_RE = re.compile(
    r"\b(?:cabinet|ccea|election\s+commission|supreme\s+court|high\s+court|fast[-\s]track\s+courts?|"
    r"pocso|ministry|nhrc|ncsc|ncw|cbi\s+court)\b", re.I)

# --------------------------------------------------------------------------- #
# Boosted set
# --------------------------------------------------------------------------- #
CABINET_RE = re.compile(r"\b(?:cabinet\s+(?:approves?|approved|decisions?|nod|clears?)|union\s+cabinet|ccea|"
                        r"cabinet\s+committee\s+on\s+economic\s+affairs)\b", re.I)
AGRI_MINISTRY_RE = re.compile(
    r"\b(?:ministry\s+of\s+agriculture|agriculture\s+(?:and|&)\s+farmers['’]?\s+welfare|agriculture\s+minist\w+|"
    r"shivraj\s+singh\s+chouhan|chouhan|icar\b|indian\s+council\s+of\s+agricultural\s+research|krishi\s+vigyan|"
    r"kvks?\b|dare\b|iari\b|cacp\b|fisheries\s+(?:department|ministry)|animal\s+husbandry|dairying|"
    r"department\s+of\s+(?:agriculture|fisheries|food\s+and\s+public\s+distribution))\b", re.I)
AGRI_TERMS_RE = re.compile(
    r"\b(?:farmers?|farming|agricultur\w*|agri[-\s]?(?:infra\w*|business|credit|export\w*|startups?|tech)|"
    r"agri\b|agro\w*|crops?|kharif|rabi|msp|paddy|wheat|rice|pulses|millets?|maize|sugarcane|cotton|oilseeds?|"
    r"horticultur\w*|fisher(?:y|ies|men|man)|fish|aquaculture|dairy|milk|livestock|poultry|cattle|"
    r"animal\s+husbandry|icar|kvks?|krishi|kisan|nabard|fertili[sz]ers?|urea|dap|irrigation|seeds?|soil|"
    r"mandis?|procurement|food\s*grains?|omss|fci|organic|natural\s+farming|apeda|fpos?|"
    r"farmer\s+producer|crop\s+loans?|kcc|pm-?kisan|pmfby|pmmsy|e-?nam|warehous\w*|cold\s+chain|"
    r"food\s+processing|plantation|tea\s+board|coffee\s+board|spices\s+board|jute|sericulture|bee-?keeping|honey)\b",
    re.I)
BANK_AGRI_RE = re.compile(r"\b(?:rbi|reserve\s+bank|nabard|banks?|lending|loans?|credit|priority\s+sector|psl)\b", re.I)
SCHEME_RE = re.compile(r"\b(?:scheme|yojana|abhiyaa?n|mission|programme|pm-[a-z]+)\b", re.I)
BIG_TICKET_RE = re.compile(
    r"\b(?:cabinet\s+approves?|khet\s+bachaa?o|international\s+maize\s+conference|omss|open\s+market\s+sale|"
    r"semicon(?:ductor)?\s+(?:2\.0|mission|india)|india\s+semiconductor\s+mission|msp\s+for|kharif\s+msp|rabi\s+msp|"
    r"repo\s+rate|monetary\s+policy|union\s+budget|economic\s+survey|gdp\s+(?:growth|data|estimate))\b", re.I)
_OFFICIAL_HOSTS_RE = re.compile(r"(?:pib\.gov\.in|rbi\.org\.in|agricoop|icar\.(?:gov|org)\.in|nabard\.org|"
                                r"pmindia\.gov\.in|cabsec|ddnews\.gov\.in|newsonair)", re.I)
BOOST_CAP = 40


def _text(item: Dict[str, Any], body_chars: int = 400) -> Tuple[str, str]:
    head = str(item.get("headline_en") or item.get("title") or item.get("text_en") or item.get("en") or "")
    body = " ".join(str(item.get(k) or "") for k in ("summary_en", "raw_facts", "summary"))[:body_chars]
    return head, body


def _url(item: Dict[str, Any]) -> str:
    src = item.get("source")
    parts = [str(item.get(k) or "") for k in ("source_url", "link", "url", "canonical_url")]
    if isinstance(src, dict):
        parts.append(str(src.get("url") or ""))
        parts.append(str(src.get("name") or ""))
    parts.append(str(item.get("source_name") or ""))
    return " ".join(parts)


def drop_reason(item: Dict[str, Any]) -> str:
    """Why *item* is not exam news ("" = keep). Judged on the headline (+ first body chars
    for state politics, where the headline names only the leader)."""
    if not isinstance(item, dict):
        return ""
    head, body = _text(item, 300)
    official = bool(_OFFICIAL_EXCEPTION_RE.search(head))
    if not official and STATE_POLITICS_RE.search(head):
        return "state party politics"
    if not official and STATE_POLITICS_RE.search(body) and not AGRI_MINISTRY_RE.search(head) \
            and not CABINET_RE.search(head) and re.search(rf"\b(?:{_PARTIES})\b", f"{head} {body}", re.I):
        return "state party politics"
    if LISTICLE_RE.search(head):
        return "market listicle"
    try:
        from pipeline.news_filters import is_opinion
        if is_opinion(item):
            return "opinion piece"
    except Exception:  # pragma: no cover - helper missing
        pass
    if OPINION_HEAD_RE.search(head):
        return "opinion piece"
    if not official and CRIME_RE.search(head):
        return "crime"
    if FOREIGN_CONFLICT_RE.search(head) and not _INDIA_RE.search(head):
        return "foreign conflict without India angle"
    return ""


def agri_terms(text: str) -> int:
    """Distinct real agriculture terms in *text* ("farm" / "trade" alone do not count)."""
    return len({m.group(0).lower() for m in AGRI_TERMS_RE.finditer(text or "")})


def boost(item: Dict[str, Any]) -> int:
    head, body = _text(item, 400)
    both = f"{head} {body}"
    pts = 0
    if CABINET_RE.search(both):
        pts += 25
    if AGRI_MINISTRY_RE.search(both):
        pts += 20
    if BANK_AGRI_RE.search(head) and (agri_terms(head) or agri_terms(body) >= 2):
        pts += 20   # RBI / NABARD agri credit, priority-sector agri lending
    elif re.search(r"\b(?:rbi|reserve\s+bank|nabard)\b", head, re.I):
        pts += 8
    if SCHEME_RE.search(head):
        pts += 10
    if BIG_TICKET_RE.search(both):
        pts += 15
    if agri_terms(head):
        pts += 10
    if _OFFICIAL_HOSTS_RE.search(_url(item)):
        pts += 5
    return min(BOOST_CAP, pts)


def is_boosted(item: Dict[str, Any]) -> bool:
    """The exam's core: Cabinet, agriculture ministry / ICAR, RBI agri credit, schemes."""
    head, body = _text(item, 400)
    both = f"{head} {body}"
    if drop_reason(item):
        return False
    return bool(CABINET_RE.search(both) or AGRI_MINISTRY_RE.search(both) or BIG_TICKET_RE.search(both)
                or (BANK_AGRI_RE.search(head) and agri_terms(both))
                or SCHEME_RE.search(head) or agri_terms(head))


def exam_score(item: Dict[str, Any]) -> float:
    try:
        base = float(item.get("importance_score") or 0)
    except (TypeError, ValueError):
        base = 0.0
    return base + boost(item)
