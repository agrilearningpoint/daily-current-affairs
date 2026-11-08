# -*- coding: utf-8 -*-
"""
TEXT NORMALISATION shared by the period builder, the Hindi post-fix and the
PDF display cleaners.  Pure functions, no I/O, never raise on odd input.

* ``tidy``            punctuation/typography: "?." -> "?", no space before , . ; : ? ! ।,
                      collapsed spaces, unbalanced quotes stripped (hyphens kept).
* ``normalise_money`` "Rs 1,500 crore" / "Rs.2,814 Crore" / "INR 50" -> "₹…" (EN and HI);
                      in a Hindi line the units become करोड़ / लाख करोड़ / लाख.
* ``exact_money``     a rounded or abbreviated money figure ("₹4K cr", "₹4,000 करोड़") is
                      replaced by the exact figure of the story's own text ("₹4,371.10 crore").
* ``strip_source_tags`` trailing outlet names in EN and HI ("- PM India", "- पीएम इंडिया",
                      "- एयर पर समाचार").
* ``caption_residue`` photo-caption remnants glued into a sentence ("CM K. Photo Jana Sena").
* ``hi_truncated_start`` a Hindi line that starts mid-word ("क्कल के किसानों ने").
* ``garbled_hi``      a Hindi line whose structure is broken (a doubled "के तहत", a dangling
                      postposition at the end).
* ``resolve_weekdays`` "on Thursday" / "गुरुवार को" -> the actual date relative to the
                      article's publish date ("on 5 November" / "5 नवंबर को").
* ``clip_words``      shorten text on a word boundary with "…" (never mid-word).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional, Tuple

DEVA_RE = re.compile(r"[\u0900-\u097F]")
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
             "October", "November", "December"]
MONTHS_HI = ["जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर",
             "नवंबर", "दिसंबर"]


# --------------------------------------------------------------------------- #
# Punctuation / typography
# --------------------------------------------------------------------------- #
_QUOTE_PAIRS = (("“", "”"), ("‘", "’"))


def _balance_quotes(s: str) -> str:
    # Straight double quotes: an odd count means one is unclosed -> drop the last one.
    if s.count('"') % 2:
        i = s.rfind('"')
        s = s[:i] + s[i + 1:]
    for o, c in _QUOTE_PAIRS:
        no, nc = s.count(o), s.count(c)
        if o == "‘":
            # ’ is also the apostrophe (India’s): only strip an orphan opening quote.
            if no > nc:
                for _ in range(no - nc):
                    i = s.rfind(o)
                    s = s[:i] + s[i + 1:]
            continue
        while no > nc:
            i = s.rfind(o)
            s = s[:i] + s[i + 1:]
            no -= 1
        while nc > no:
            i = s.find(c)
            s = s[:i] + s[i + 1:]
            nc -= 1
    return s


def tidy(text: Any) -> str:
    """Typographic cleanup of one display line (EN or HI). Hyphens are kept."""
    s = str(text or "")
    if not s:
        return ""
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"([?!])\s*\.(?!\.)", r"\1", s)            # "?." -> "?"
    s = re.sub(r"\.\s*([?!])", r"\1", s)                   # ".?" -> "?"
    s = re.sub(r"।\s*\.", "।", s)                            # "।." -> "।"
    s = re.sub(r"\.\s*।", "।", s)
    s = re.sub(r"\s+([,;:!?।])", r"\1", s)                  # no space before , ; : ! ? ।
    s = re.sub(r"(?<=\S)\s+\.(?!\d|\.)", ".", s)            # "word ." -> "word." (not " .5")
    s = re.sub(r",{2,}", ",", s)
    s = re.sub(r"([,;:])(?=[A-Za-z\u0900-\u097F])", r"\1 ", s)  # missing space after , ; :
    s = _balance_quotes(s)
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s+\)", ")", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


# --------------------------------------------------------------------------- #
# Money
# --------------------------------------------------------------------------- #
_RS_RE = re.compile(r"(?<![A-Za-z])(?:Rs\.?|INR|₹)\s?(?=\d)")
_CRORE_CAP_RE = re.compile(r"(₹\d[\d,]*(?:\.\d+)?)\s?(Lakh\s+Crore|Crores?|Lakhs?|cr\.?|Cr\.?)(?![A-Za-z])")
_HI_UNITS = (("lakh crore", "लाख करोड़"), ("lakh crores", "लाख करोड़"), ("crores", "करोड़"), ("crore", "करोड़"),
             ("cr", "करोड़"), ("lakhs", "लाख"), ("lakh", "लाख"))


def normalise_money(text: Any, hindi: Optional[bool] = None) -> str:
    """Rs / INR -> ₹ and consistent units. ``hindi`` defaults to "line has Devanagari"."""
    s = str(text or "")
    if not s:
        return ""
    hi = bool(DEVA_RE.search(s)) if hindi is None else hindi
    s = _RS_RE.sub("₹", s)
    if hi:
        def _u(m: re.Match) -> str:
            unit = m.group(2).lower().rstrip(".")
            unit = re.sub(r"\s+", " ", unit)
            rep = next((h for e, h in _HI_UNITS if unit == e), m.group(2))
            return f"{m.group(1)} {rep}"
        s = re.sub(r"(₹\d[\d,]*(?:\.\d+)?)\s?(lakh\s+crores?|crores?|cr\.?|lakhs?)(?![A-Za-z])", _u, s, flags=re.I)
    else:
        def _e(m: re.Match) -> str:
            unit = re.sub(r"\s+", " ", m.group(2).lower().rstrip("."))
            unit = {"crores": "crore", "cr": "crore", "lakhs": "lakh"}.get(unit, unit)
            return f"{m.group(1)} {unit}"
        s = _CRORE_CAP_RE.sub(_e, s)
    return s


_MONEY_RE = re.compile(
    r"₹\s?(?P<num>\d[\d,]*(?:\.\d+)?)\s?(?P<k>[Kk](?![A-Za-z])|thousand\b|हज़ार|हजार)?\s?"
    r"(?P<unit>lakh\s+crores?|लाख\s+करोड़|crores?|cr\b\.?|करोड़|lakhs?\b|लाख|trn\b|trillion\b|ट्रिलियन|"
    r"bn\b|billion\b|बिलियन|अरब|million\b|मिलियन)?")
_UNIT_CRORE = {"lakh crore": 1e5, "लाख करोड़": 1e5, "crore": 1.0, "cr": 1.0, "करोड़": 1.0, "lakh": 0.01,
               "लाख": 0.01, "trn": 1e5, "trillion": 1e5, "ट्रिलियन": 1e5, "bn": 100.0, "billion": 100.0,
               "बिलियन": 100.0, "अरब": 100.0, "million": 0.1, "मिलियन": 0.1}


def _unit_key(u: str) -> str:
    u = re.sub(r"\s+", " ", (u or "").lower().rstrip("."))
    return {"crores": "crore", "lakhs": "lakh", "lakh crores": "lakh crore"}.get(u, u)


def money_mentions(text: str) -> List[Tuple[re.Match, float, bool]]:
    """(match, value in crore, abbreviated?) for every ₹ figure in *text* (normalise first)."""
    out = []
    for m in _MONEY_RE.finditer(text or ""):
        try:
            num = float(m.group("num").replace(",", ""))
        except ValueError:
            continue
        unit = _unit_key(m.group("unit") or "")
        factor = _UNIT_CRORE.get(unit, 1e-7 if not unit else 1.0)
        if m.group("k"):
            num *= 1000
        abbreviated = bool(m.group("k")) or unit in ("cr", "trn", "bn")
        out.append((m, num * factor, abbreviated))
    return out


def _sig(num_text: str) -> int:
    digits = re.sub(r"\D", "", num_text.split(".")[0]) + (num_text.split(".")[1] if "." in num_text else "")
    return len(digits.rstrip("0").lstrip("0"))


def exact_money(line: Any, source: Any, hindi: Optional[bool] = None) -> str:
    """Replace a rounded/abbreviated ₹ figure in *line* with the exact figure the
    story's own *source* text gives (within 12%, more significant digits, unique)."""
    s = normalise_money(line, hindi)
    src = normalise_money(source, False)
    if not s or "₹" not in s or "₹" not in src:
        return s
    hi = bool(DEVA_RE.search(s)) if hindi is None else hindi
    srcs = money_mentions(src)
    out, pos = [], 0
    for m, val, abbr in money_mentions(s):
        best = None
        for sm, sval, sab in srcs:
            if sab or sval <= 0 or abs(sval - val) / sval > 0.12 or abs(sval - val) < 1e-9:
                continue
            if not abbr and _sig(sm.group("num")) <= _sig(m.group("num")):
                continue
            if best is not None and abs(best[1] - sval) > 1e-9:
                best = ("ambiguous", 0)
                break
            best = (sm, sval)
        if not best or best[0] == "ambiguous":
            continue
        sm = best[0]
        unit = _unit_key(sm.group("unit") or "")
        if hi:
            unit = {"crore": "करोड़", "lakh crore": "लाख करोड़", "lakh": "लाख", "billion": "बिलियन",
                    "million": "मिलियन", "trillion": "ट्रिलियन"}.get(unit, unit)
        rep = f"₹{sm.group('num')}" + (f" {unit}" if unit else "")
        end = m.end()
        while end > m.start() and s[end - 1] == " ":
            end -= 1
        out.append(s[pos:m.start()] + rep)
        pos = end
    out.append(s[pos:])
    return "".join(out)


# --------------------------------------------------------------------------- #
# Source tags, caption residue
# --------------------------------------------------------------------------- #
_SRC_EN = (r"PM India|PIB(?: Delhi| India)?|DD News|AIR News|All India Radio|Akashvani(?: News)?|News On AIR|"
           r"Mint|Livemint|The Hindu(?: BusinessLine)?|BusinessLine|Business Standard|The Economic Times|"
           r"Economic Times|Hindustan Times|Times of India|Indian Express|The Indian Express|NDTV|ANI|PTI|IANS|"
           r"Reuters|Moneycontrol|Financial Express|Report")
_SRC_HI = (r"पीएम इंडिया|पीएमइंडिया|प्रधानमंत्री इंडिया|पीआईबी(?: दिल्ली)?|पत्र सूचना कार्यालय|डीडी न्यूज़?|डीडी समाचार|"
           r"एयर पर समाचार|न्यूज़? ऑन एयर|ऑल इंडिया रेडियो|आकाशवाणी(?: समाचार)?|एआईआर समाचार|एआईआर न्यूज़?|"
           r"मिंट|लाइवमिंट|द हिंदू(?: बिजनेसलाइन)?|बिज़?नेस स्टैंडर्ड|द इकोनॉमिक टाइम्स|इकोनॉमिक टाइम्स|"
           r"हिंदुस्तान टाइम्स|टाइम्स ऑफ इंडिया|इंडियन एक्सप्रेस|एनडीटीवी|रिपोर्ट")
_SRC_TAIL_RE = re.compile(rf"\s+[-–—|]\s*(?:{_SRC_EN}|{_SRC_HI})\s*[.।]?\s*$", re.I)


def strip_source_tags(text: Any) -> str:
    s = str(text or "").strip()
    for _ in range(2):
        s = _SRC_TAIL_RE.sub("", s).strip()
    return s


_CAPTION_RE = re.compile(
    r"\b[A-Z]\.\s+Photo\s+[A-Z]"                        # "CM K. Photo Jana Sena" (name eaten by a credit)
    r"|\b(?:File|PTI|ANI|IANS|Reuters|Special\s+Arrangement)\s+Photo\b"
    r"|\bPhoto\s*(?:Credit)?\s*:\s*"
    r"|\bPhoto\s+(?:by|courtesy)\b")


def caption_residue(text: Any) -> bool:
    return bool(_CAPTION_RE.search(str(text or "")))


# --------------------------------------------------------------------------- #
# Hindi integrity
# --------------------------------------------------------------------------- #
_DEP_SIGN = "\u0900-\u0903\u093A-\u094F\u0951-\u0957\u0962\u0963\u093C"
_GEMINATE_START_RE = re.compile(r"^([\u0915-\u0939\u0958-\u095F])\u094D\1")


def hi_truncated_start(hi: Any) -> bool:
    """Starts with a dependent sign / virama, or a geminate cluster no Hindi word starts with."""
    s = re.sub(r"^[\s\"'“‘(\-–•\d.)]+", "", str(hi or ""))
    if not s or not DEVA_RE.match(s):
        return False
    return bool(re.match(rf"[{_DEP_SIGN}]", s) or _GEMINATE_START_RE.match(s))


_DOUBLE_POST = ("के तहत", "के अंतर्गत")
_DANGLING_END_RE = re.compile(r"(?:के\s+(?:लिए|तहत|अंतर्गत|साथ|द्वारा)|द्वारा|में\s+से)\s*[,]?\s*$")


def garbled_hi(hi: Any) -> bool:
    s = str(hi or "").strip()
    if not DEVA_RE.search(s):
        return False
    for sent in re.split(r"[।!?]", s):
        for p in _DOUBLE_POST:
            if sent.count(p) >= 2:
                return True
        if _DANGLING_END_RE.search(sent.strip().rstrip(".")) and len(sent.split()) >= 8:
            return True
    return False


# --------------------------------------------------------------------------- #
# Dates: "on Thursday" -> the event date
# --------------------------------------------------------------------------- #
_WD_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_WD_HI = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]
_IST = timezone(timedelta(hours=5, minutes=30))


def publish_date(value: Any, fallback: Any = None) -> Optional[date]:
    """Article publish date (IST) from an ISO / RFC-2822 string, else *fallback*."""
    for v in (value, fallback):
        if not v:
            continue
        if isinstance(v, datetime):
            return (v.astimezone(_IST) if v.tzinfo else v).date()
        if isinstance(v, date):
            return v
        t = str(v).strip()
        try:
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            return (dt.astimezone(_IST) if dt.tzinfo else dt).date()
        except ValueError:
            pass
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(t)
            return (dt.astimezone(_IST) if dt.tzinfo else dt).date()
        except (TypeError, ValueError, IndexError):
            pass
        m = re.match(r"(\d{4}-\d{2}-\d{2})", t)
        if m:
            try:
                return date.fromisoformat(m.group(1))
            except ValueError:
                pass
    return None


def weekday_date(weekday: int, pub: date, forward: bool = False) -> date:
    """The *weekday* on/before *pub* (or the next one after it when *forward*)."""
    if forward:
        return pub + timedelta(days=((weekday - pub.weekday()) % 7) or 7)
    return pub - timedelta(days=(pub.weekday() - weekday) % 7)


def _fmt(d: date, pub: date, hindi: bool) -> str:
    month = (MONTHS_HI if hindi else MONTHS_EN)[d.month - 1]
    return f"{d.day} {month}" + (f" {d.year}" if d.year != pub.year else "")


_EN_WD_RE = re.compile(r"\b(?:(on|last|this past|next|earlier on|late on)\s+)(" + "|".join(_WD_EN) + r")\b"
                       r"(?:\s+(morning|afternoon|evening|night))?(?![’']s)")
_HI_WD_RE = re.compile(r"(?:(पिछले|बीते|अगले|आगामी)\s+)?(" + "|".join(_WD_HI) + r")(?![\u0900-\u097F])"
                       r"(\s+को(?![\u0900-\u097F])|\s+(?:सुबह|शाम|रात|दोपहर)\s+को(?![\u0900-\u097F]))?")
_HI_KEEP_RE = re.compile(r"\s+(?:की|के|का|से|तक)(?![\u0900-\u097F])")


def resolve_weekdays(text: Any, pub: Optional[date]) -> str:
    """Replace a relative weekday with the actual date, counted from the publish date."""
    s = str(text or "")
    if not s or pub is None:
        return s
    if DEVA_RE.search(s):
        def hi(m: re.Match) -> str:
            fwd = m.group(1) in ("अगले", "आगामी")
            d = _fmt(weekday_date(_WD_HI.index(m.group(2)), pub, fwd), pub, True)
            tail = (m.group(3) or "").strip()
            if tail:
                return f"{d} {tail}"                    # "गुरुवार (शाम) को" -> "5 नवंबर (शाम) को"
            if _HI_KEEP_RE.match(m.string, m.end()):
                return d                                # "गुरुवार की बैठक" -> "5 नवंबर की बैठक"
            return f"{d} को"                            # "गुरुवार प्रस्ताव रखा" -> "5 नवंबर को प्रस्ताव रखा"
        s = _HI_WD_RE.sub(hi, s)
        s = re.sub(r"को\s+को", "को", s)
        return re.sub(r"\s{2,}", " ", s)

    def en(m: re.Match) -> str:
        fwd = m.group(1) == "next"
        d = _fmt(weekday_date(_WD_EN.index(m.group(2)), pub, fwd), pub, False)
        if m.group(3):
            return f"on the {m.group(3)} of {d}"
        return f"on {d}"
    return _EN_WD_RE.sub(en, s)


# --------------------------------------------------------------------------- #
# Word-boundary clipping
# --------------------------------------------------------------------------- #
def clip_words(text: Any, n: int) -> str:
    t = str(text or "").strip()
    if len(t) <= n:
        return t
    cut = t[:n]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(",;:-–— ") + "…"
