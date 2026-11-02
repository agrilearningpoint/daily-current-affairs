# -*- coding: utf-8 -*-
"""Shared news/non-news filters used by selection (stage 10) and the auto sections (stage 17b)."""
import re

# Feed entries that are not exam news: tenders/bid notices, recruitment-rule PDFs,
# opinion/editorial/review pieces, videos/quizzes/live blogs.  Run 41425513692
# printed "Bid opening meeting link for Procurement of ..." and a film review.
#
# Kept deliberately narrow: "procurement of paddy", "tender" in a defence-contract
# story, or an "Explained" analysis of a Cabinet decision are real news, so only
# notice-board phrasing is matched (see tests/test_selection_quality.py).
NON_NEWS_RE = re.compile(
    r"\b(?:bid\s+opening|corrigendum|e-?procurement\s+portal|tender\s+(?:notice|document|enquiry)|"
    r"notice\s+inviting\s+tender|NIT\s+for|procurement\s+of\s+(?:services|goods|items|equipment|hardware|"
    r"software|vehicles?|furniture|stationery|consumables|manpower)|expression\s+of\s+interest|"
    r"request\s+for\s+proposal|\bRFP\b|walk[-\s]?in\s+interview|recruitment\s+rules|vacancy\s+circular|"
    r"admit\s+card|answer\s+key|movie\s+review|film\s+review|book\s+review|"
    r"editorial|op-ed|podcast|live\s+updates?|live\s+blog|crossword|horoscope|quiz\s+(?:of\s+the\s+day|time)|"
    r"wordle|spangram|hints?\s+and\s+answers|net\s+worth|stocks?\s+to\s+buy|share\s+price\s+today|"
    r"national\s+portal\s+of\s+india|photo\s+gallery|press\s+note\s+details|candidate\s+affidavit|weekly\s+policy\s+watch|week\s+ahead)\b"
    r"|^\s*(?:watch|video|photos?|in\s+pictures|letters?|opinion)\s*[:|]"
    r"|\|\s*the\s+hindu\s+editorial",
    re.IGNORECASE,
)


def topic_key(x: dict) -> str:
    """Running-story key: the 'Cyclone Murasu' of 'Cyclone Murasu: red alert in ...'."""
    h = (x.get("headline_en") or x.get("title") or "").strip()
    m = re.match(r"^([A-Z][\w'’.-]*(?:\s+[A-Z][\w'’.-]*){0,3})\s*[:|]", h)
    if m:
        return m.group(1).lower()
    m = re.search(r"\b(?:Cyclone|Operation|Mission|Storm|Typhoon|Hurricane)\s+[A-Z][a-z]+", h)
    return m.group(0).lower() if m else ""


def is_non_news(headline: str) -> bool:
    return bool(NON_NEWS_RE.search(headline or ""))
