# -*- coding: utf-8 -*-
"""
Agent 04: Zero-Hallucination Fact Verification Engine & Fact Ledger (Section 7)
===============================================================================
Extracts structured 5W1H + numerical/institutional facts for each candidate news item:
- Who, What, When, Where, Why, How
- Organization, Ministry, Location, Scheme, Amount, Percentage, Ranking,
  Statistical figure, Official designation, Effective date, Reference source.

Verification Rules Enforced:
1. Every numerical figure (Rs/crore, %, LMT/MT, rank, year) in a generated summary
   or bullet MUST appear in the source evidence text. Invented numbers are blocked.
2. When two sources report conflicting numerical figures for the same event+metric
   (e.g. "₹1,500 crore" vs "₹2,500 crore"), the disputed fact is quarantined
   instead of silently picking one number.
3. Persists a permanent verifiable Fact Ledger in `state/fact_ledger.json`.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pipeline.store import STATE_DIR, atomic_write_json, safe_read_json

FACT_LEDGER_PATH = STATE_DIR / "fact_ledger.json"

MINISTRY_RE = re.compile(
    r"\b(Ministry\s+of\s+[A-Z][A-Za-z\s,&\-]{3,55}?)(?=[.,;\)]|\s+(?:has|launched|announced|approved|released|in|on|under)\b|$)"
)
SCHEME_RE = re.compile(
    r"\b((?:Pradhan\s+Mantri|PM|National\s+Mission|Atmanirbhar|Mukhyamantri|Kisan|Agri)[A-Za-z0-9\s\-()]{4,60}?\s*(?:Yojana|Scheme|Mission|Abhiyan|Kosh|Fund))\b"
)
AMOUNT_RE = re.compile(
    r"(?:₹|Rs\.?|INR|USD|\$)\s*\d[\d,]*(?:\.\d+)?\s*(?:lakh\s+crore|crore|lakh|billion|million)?"
    r"|\d[\d,]*(?:\.\d+)?\s*(?:lakh\s+crore|crore|lakh\s+metric\s+tonnes|LMT|MT|million\s+tonnes|GW|MW|hectares|Mha)",
    re.IGNORECASE,
)
PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%")
RANK_RE = re.compile(r"\b(?:rank(?:ed)?\s+\d+|\d+(?:st|nd|rd|th)\s+(?:rank|place|position))\b", re.IGNORECASE)
ORG_ACRONYMS = (
    "ICAR", "NABARD", "RBI", "SEBI", "ISRO", "DRDO", "NITI Aayog", "APEDA",
    "FSSAI", "FAO", "World Bank", "IMF", "WHO", "WTO", "UNFCCC", "CACP", "FCI", "DAHD", "IARI",
)
STATES_UT = (
    "Uttar Pradesh", "Maharashtra", "Madhya Pradesh", "Punjab", "Haryana", "Rajasthan",
    "Bihar", "Gujarat", "Karnataka", "Tamil Nadu", "Telangana", "Andhra Pradesh",
    "Odisha", "West Bengal", "Assam", "Kerala", "Chhattisgarh", "Jharkhand",
    "Uttarakhand", "Himachal Pradesh", "Goa", "Tripura", "Manipur", "Meghalaya",
    "Nagaland", "Mizoram", "Arunachal Pradesh", "Sikkim", "New Delhi", "Jammu and Kashmir", "Ladakh",
)


def extract_numbers_normalized(text: str) -> List[str]:
    """Extract normalized numerical tokens from text for strict source-support verification."""
    s = str(text or "").replace(",", "")
    return re.findall(r"\b\d+(?:\.\d+)?\b", s)


def extract_structured_facts(item: Dict[str, Any]) -> Dict[str, Any]:
    """Extract 5W1H and high-risk exam facts directly from source text."""
    headline = str(item.get("headline_en") or item.get("title") or "").strip()
    summary = str(item.get("summary_en") or item.get("summary") or "").strip()
    source_text = f"{headline}. {summary}"

    ministries = [m.strip() for m in MINISTRY_RE.findall(source_text)]
    schemes = [s.strip() for s in SCHEME_RE.findall(source_text)]
    amounts = [a.strip() for a in AMOUNT_RE.findall(source_text)]
    percentages = [p.strip() for p in PERCENT_RE.findall(source_text)]
    rankings = [r.strip() for r in RANK_RE.findall(source_text)]
    orgs = [org for org in ORG_ACRONYMS if re.search(rf"\b{re.escape(org)}\b", source_text)]
    locations = [st for st in STATES_UT if re.search(rf"\b{re.escape(st)}\b", source_text, re.IGNORECASE)]

    status_tag = "final"
    if re.search(r"\bprovisional\b", source_text, re.I):
        status_tag = "provisional"
    elif re.search(r"\b(?:advance\s+estimate|estimated)\b", source_text, re.I):
        status_tag = "estimated"
    elif re.search(r"\brevised\b", source_text, re.I):
        status_tag = "revised"

    who_val = ministries[0] if ministries else (orgs[0] if orgs else item.get("source_name", "Government of India"))
    where_val = locations[0] if locations else "India"
    when_val = item.get("published_at_ist") or item.get("published_at") or ""

    return {
        "who": who_val,
        "what": headline,
        "when": when_val,
        "where": where_val,
        "why": summary[:220] if summary else headline,
        "how": schemes[0] if schemes else (ministries[0] if ministries else "Official policy/programme implementation"),
        "organizations": orgs,
        "ministries": ministries,
        "locations": locations,
        "schemes": schemes,
        "amounts": amounts,
        "percentages": percentages,
        "rankings": rankings,
        "figure_status": status_tag,
        "source_url": item.get("link") or item.get("canonical_url") or "",
        "source_name": item.get("source_name") or "",
    }


def verify_claim_against_source(claim_text: str, source_evidence: str) -> Tuple[bool, List[str]]:
    """
    Rule 3 & 4: Every numerical figure in `claim_text` MUST be present in `source_evidence`.
    Returns (is_valid, unsupported_numbers).
    """
    source_nums = set(extract_numbers_normalized(source_evidence))
    claim_nums = extract_numbers_normalized(claim_text)
    unsupported = [n for n in claim_nums if n not in source_nums]
    return len(unsupported) == 0, unsupported


def detect_source_contradictions(reports_for_same_event: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Rule 10: If two sources report conflicting monetary amounts or percentages for
    the same event, flag and quarantine the disputed fact.
    """
    if len(reports_for_same_event) < 2:
        return False, ""
    amount_sets = []
    pct_sets = []
    for rep in reports_for_same_event:
        txt = f"{rep.get('headline_en') or rep.get('title') or ''} {rep.get('summary_en') or rep.get('summary') or ''}"
        amts = {re.sub(r"\s+", " ", a.strip().lower()) for a in AMOUNT_RE.findall(txt)}
        pcts = {p.strip() for p in PERCENT_RE.findall(txt)}
        if amts:
            amount_sets.append((rep.get("source_name", "source"), amts))
        if pcts:
            pct_sets.append((rep.get("source_name", "source"), pcts))

    if len(amount_sets) >= 2:
        base_src, base_amts = amount_sets[0]
        for other_src, other_amts in amount_sets[1:]:
            if base_amts and other_amts and not (base_amts & other_amts):
                return True, f"Conflicting amounts between {base_src} ({sorted(base_amts)}) and {other_src} ({sorted(other_amts)})"

    if len(pct_sets) >= 2:
        base_src, base_pcts = pct_sets[0]
        for other_src, other_pcts in pct_sets[1:]:
            if base_pcts and other_pcts and not (base_pcts & other_pcts):
                return True, f"Conflicting percentages between {base_src} ({sorted(base_pcts)}) and {other_src} ({sorted(other_pcts)})"

    return False, ""


def verify_and_record_facts(
    items: List[Dict[str, Any]],
    ledger_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Verify candidate news items, build structured facts, check for numerical hallucinations
    or inter-source contradictions, and persist the Fact Ledger.
    Returns (verified_items, quarantined_items).
    """
    l_path = ledger_path or FACT_LEDGER_PATH
    ledger = safe_read_json(l_path, {"facts": {}})
    facts_map: Dict[str, Any] = ledger.get("facts", {})

    verified: List[Dict[str, Any]] = []
    quarantined: List[Dict[str, Any]] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for item in items:
        working = dict(item)
        source_url = str(working.get("link") or working.get("canonical_url") or "").strip()
        headline = str(working.get("headline_en") or working.get("title") or "").strip()
        summary = str(working.get("summary_en") or working.get("summary") or "").strip()
        evidence = str(working.get("raw_evidence") or f"{headline}. {summary}").strip()

        if not source_url.startswith(("http://", "https://")) or len(headline) < 12:
            working["quarantine_reason"] = "missing_verifiable_source_url_or_headline"
            quarantined.append(working)
            continue

        # Check if multiple reports attached to this item disagree on figures
        corroborating = working.get("corroborating_reports") or []
        if corroborating:
            has_conflict, conflict_msg = detect_source_contradictions([working] + list(corroborating))
            if has_conflict:
                working["quarantine_reason"] = f"source_contradiction:{conflict_msg}"
                quarantined.append(working)
                continue

        # Check that edited summary/key_points do not contain numbers absent from raw evidence
        candidate_claims = " ".join(list(working.get("key_points_en") or []) + [summary])
        ok_nums, bad_nums = verify_claim_against_source(candidate_claims, evidence)
        if not ok_nums:
            working["quarantine_reason"] = f"unsupported_numerical_figures:{bad_nums}"
            quarantined.append(working)
            continue

        structured = extract_structured_facts(working)
        working["structured_facts"] = structured
        working["verification_status"] = "verified"
        working["verified_at"] = now_iso

        # Record every extracted numerical/scheme/institutional fact in the permanent Fact Ledger
        fact_entries = (
            [("amount", v) for v in structured["amounts"]]
            + [("percentage", v) for v in structured["percentages"]]
            + [("ranking", v) for v in structured["rankings"]]
            + [("scheme", v) for v in structured["schemes"]]
            + [("ministry", v) for v in structured["ministries"]]
        )
        if not fact_entries:
            fact_entries = [("headline_claim", headline)]

        item_fact_ids = []
        for f_type, f_val in fact_entries:
            fid = "fact_" + hashlib.sha1(f"{source_url}|{f_type}|{f_val}".encode("utf-8")).hexdigest()[:14]
            facts_map[fid] = {
                "fact_id": fid,
                "fact_type": f_type,
                "fact_value": f_val,
                "figure_status": structured["figure_status"],
                "source_url": source_url,
                "source_name": structured["source_name"],
                "source_publication_date": structured["when"],
                "supporting_evidence": evidence[:300],
                "verification_status": "verified",
                "confidence_level": "primary_official" if "tier1" in str(working.get("reliability_level", "")) else "corroborated_editorial",
                "verification_timestamp": now_iso,
            }
            item_fact_ids.append(fid)

        working["fact_ids"] = item_fact_ids
        verified.append(working)

    ledger["facts"] = facts_map
    ledger["updated_at"] = now_iso
    atomic_write_json(l_path, ledger)
    return verified, quarantined
