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
    r"national\s+portal\s+of\s+india|photo\s+gallery|press\s+note\s+details|candidate\s+affidavit|weekly\s+policy\s+watch|week\s+ahead|"
    r"(?:morning|evening|news|daily)\s+digest|news\s+wrap)\b"
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


def story_key(headline: str) -> str:
    """Normalised headline used to recognise the same story across editions
    (feeds re-stamp event ids, so ids alone miss repeats)."""
    h = re.sub(r"^\W+", "", (headline or "").lower())
    h = re.sub(r"\s+-\s+[^-]{2,60}$", "", h)          # " - PM India" publisher suffix
    return re.sub(r"[^a-z0-9\u0900-\u097f]+", " ", h).strip()[:90]


# --------------------------------------------------------------------------- #
# Opinion / column pieces (audit 2026-11-04: The Hindu editorials and lead
# articles printed as Quick Bites: "Coming of age: On the Binance hack. ...",
# "On the Arunachal frontier, silence is not a strategy").
# --------------------------------------------------------------------------- #
OPINION_URL_RE = re.compile(
    r"/(?:opinion|opinions|editorials?|columns?|columnists?|op-?eds?|blogs?|views?|comment|commentary|"
    r"letters?(?:-to-the-editor)?|readers?-?mail|guest-?column|perspective)(?:/|$|-)"
    r"|[?&](?:section|category)=(?:opinion|editorial|columns?)", re.I)
OPINION_HEAD_RE = re.compile(
    r"^[^:]{2,60}:\s+On\s+(?:the\s+|a\s+|an\s+)?[A-Z\w]"          # Hindu editorial "X: On the Y"
    r"|^\s*(?:opinion|editorial|column|analysis|view|comment|op-?ed)\s*[:|-]"
    r"|\|\s*(?:opinion|editorial|column)\b", re.I)
_OPINION_SECTIONS = {"opinion", "editorial", "editorials", "column", "columns", "op-ed", "oped", "blog",
                     "blogs", "views", "comment", "lead"}


def is_opinion(item: dict) -> bool:
    """Opinion / editorial / column piece, judged by URL, section and headline shape."""
    if not isinstance(item, dict):
        return False
    for k in ("link", "source_url", "url", "source_feed"):
        if OPINION_URL_RE.search(str(item.get(k) or "")):
            return True
    for k in ("section", "source_section", "category"):
        if str(item.get(k) or "").strip().lower() in _OPINION_SECTIONS:
            return True
    head = str(item.get("headline_en") or item.get("title") or "")
    return bool(OPINION_HEAD_RE.search(head))


# --------------------------------------------------------------------------- #
# Headline repair: leftover tags and truncation ("... - PM India",
# "(Key: DD News)", "...The Division of Soil").
# --------------------------------------------------------------------------- #
_TAG_RES = (
    re.compile(r"\s*[\(\[]\s*(?:key|source|via|courtesy|credit)\s*:\s*[^\)\]]{1,60}[\)\]]\s*$", re.I),
    re.compile(r"\s+[-–—|]\s+(?:PM\s+India|News\s+On\s+AIR|DD\s+News|PIB(?:\s+\w+)?|Press\s+Information\s+Bureau|"
               r"All\s+India\s+Radio|AIR\s+News|The\s+Hindu(?:\s+BusinessLine)?|Business\s+Standard|"
               r"Indian\s+Express|The\s+Indian\s+Express|Hindustan\s+Times|Times\s+of\s+India|"
               r"Economic\s+Times|ET\s+\w+|Mint|Livemint|NDTV|India\s+Today|Firstpost|Moneycontrol|"
               r"Deccan\s+Herald|The\s+Tribune|WION|ANI|PTI|Reuters|Bloomberg|BBC(?:\s+News)?|"
               r"[\w.-]+\.(?:com|in|org|net|gov\.in|co\.in|nic\.in)|www\.[\w.]+|[A-Z][\w&.' ]{1,40}"
               r"\s+(?:Media|News|Times|Post|Radio|Network|Online))\s*$", re.I),
)
TRUNCATED_RE = re.compile(r"(?:…|\.\.\.|\u2026)\s*$|^\s*(?:…|\.\.\.)")


def strip_tags(headline: str) -> str:
    h = re.sub(r"\s+", " ", str(headline or "")).strip()
    for _ in range(3):
        before = h
        for rx in _TAG_RES:
            h = rx.sub("", h).strip()
        if h == before:
            break
    return h.strip(" -|:")


def is_truncated(headline: str) -> bool:
    return bool(TRUNCATED_RE.search(str(headline or "")))


def repair_headline(item: dict) -> str:
    """A clean, complete headline for *item*, or "" when it cannot be repaired.

    Tags/publisher tails are stripped; a truncated headline ("...The Division of
    Soil") is replaced by the item's full title, or by the summary sentence it was
    cut from; otherwise "" (the caller drops the item)."""
    head = strip_tags(item.get("headline_en") or item.get("title") or "")
    if head and not is_truncated(head):
        return head
    stem = re.sub(r"(?:…|\.\.\.|\u2026)\s*$", "", head).strip()
    stem = re.sub(r"^\s*(?:…|\.\.\.)\s*", "", stem)
    for alt in (item.get("title"), item.get("headline_en"), item.get("og_title"), item.get("page_title")):
        alt = strip_tags(alt or "")
        if alt and not is_truncated(alt) and len(alt) >= len(stem) and (
                not stem or alt.lower().startswith(stem[:25].lower()) or stem.lower() in alt.lower()):
            return alt
    body = re.sub(r"\s+", " ", str(item.get("summary") or item.get("raw_facts") or "")).strip()
    if stem and len(stem) >= 20 and body:
        i = body.lower().find(stem.lower())
        if i >= 0:
            m = re.match(r"[^.!?]{0,240}[.!?]", body[i:])
            if m and len(m.group(0)) > len(stem):
                return m.group(0).rstrip(".").strip()
    return ""


# --------------------------------------------------------------------------- #
# Same-event detection by shared rare entity ("Binance hack" x3, "EC Form 6" x2)
# --------------------------------------------------------------------------- #
_STOP = {"the", "and", "for", "with", "from", "that", "this", "into", "over", "after", "amid", "says", "said",
         "will", "about", "under", "india", "indian", "govt", "government", "minister", "ministry", "union",
         "state", "national", "new", "today", "year", "news", "report", "says", "more", "than", "also",
         "first", "over", "what", "when", "why", "how", "its", "has", "have", "been", "were", "was", "are",
         "per", "cent", "crore", "lakh", "day", "days", "week", "month", "official", "officials"}
_GENERIC_ENT = {"union", "minister", "ministry", "government", "india", "indian", "national", "shri", "president",
                "prime", "chief", "state", "states", "central", "centre", "department", "scheme", "mission",
                "report", "board", "commission", "award", "awards", "court", "supreme", "high", "delhi", "new",
                "january", "february", "march", "april", "may", "june", "july", "august", "september",
                "october", "november", "december", "monday", "tuesday", "wednesday", "thursday", "friday",
                "saturday", "sunday", "the", "on", "in", "pm", "cm", "us", "un", "pib", "govt", "day"}


def _content_tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]{3,}", (text or "").lower()) if w not in _STOP}


def entity_tokens(text: str) -> set:
    """Distinctive names in a headline: capitalised words, acronyms, 'Form 6'-style ids."""
    t = re.sub(r"[‐-―−]", " ", text or "")
    ents = set()
    for m in re.finditer(r"\b[A-Z][A-Za-z0-9]{2,}\b", t):
        w = m.group(0)
        start = not t[:m.start()].strip() or re.search(r"[.:!?|]\s*$", t[:m.start()])
        if start and not w.isupper():
            continue  # sentence-initial capital is not a name
        ents.add(w.lower())
    ents |= {f"{a.lower()} {b}" for a, b in re.findall(r"\b([A-Z][a-z]+)\s+(\d{1,3}[A-Z]?)\b", t)}
    return {e for e in ents if e not in _GENERIC_ENT}


def rare_entities(headlines, max_df: int = 3) -> set:
    """Entities appearing in at most *max_df* of *headlines* (pool document frequency)."""
    df: dict = {}
    for h in headlines:
        for e in entity_tokens(h):
            df[e] = df.get(e, 0) + 1
    return {e for e, n in df.items() if n <= max_df}


def same_event_entity(a: str, b: str, rare: set) -> bool:
    """Two headlines name the same rare entity and share another content word."""
    shared = entity_tokens(a) & entity_tokens(b) & set(rare or ())
    if not shared:
        return False
    common = _content_tokens(a) & _content_tokens(b)
    others = common - {w for e in shared for w in e.split()}
    return bool(others) or len(shared) >= 2
