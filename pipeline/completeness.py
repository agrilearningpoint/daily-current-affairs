# -*- coding: utf-8 -*-
"""Content Completeness Validator for Agri Learning Point Current Affairs.

Verifies the educational depth, field presence, bilingual consistency, and
factual completeness of selected news items before PDF rendering.
Enforces Master Rule: Never publish empty, half-translated, or ungrounded stories.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
NUMBER_RE = re.compile(r"\b\d+(?:,\d+)*(?:\.\d+)?\b")


@dataclass
class CompletenessIssue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str
    item_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompletenessReport:
    total_items: int = 0
    complete_items: int = 0
    items_with_detailed_explanation: int = 0
    items_with_static_gk: int = 0
    items_with_sources: int = 0
    average_words_en: float = 0.0
    average_words_hi: float = 0.0
    issues: List[CompletenessIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    def add(self, severity: str, code: str, message: str, item_id: str = "", **details: Any) -> None:
        self.issues.append(CompletenessIssue(severity, code, message, item_id, details))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_items": self.total_items,
            "complete_items": self.complete_items,
            "items_with_detailed_explanation": self.items_with_detailed_explanation,
            "items_with_static_gk": self.items_with_static_gk,
            "items_with_sources": self.items_with_sources,
            "average_words_en": round(self.average_words_en, 1),
            "average_words_hi": round(self.average_words_hi, 1),
            "passed": self.passed,
            "issues": [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "message": i.message,
                    "item_id": i.item_id,
                    "details": i.details,
                }
                for i in self.issues
            ],
        }


def extract_numbers_from_text(text: str) -> Set[str]:
    """Find all numeric strings in text for cross-lingual validation."""
    return set(NUMBER_RE.findall(text or ""))


def validate_item_completeness(item: Dict[str, Any], report: CompletenessReport) -> bool:
    """Validate a single story against educational completeness standards."""
    event_id = str(item.get("event_id") or "unknown")
    headline_en = (item.get("headline_en") or "").lstrip("> ").strip()
    headline_hi = (item.get("headline_hi") or "").lstrip("> ").strip()

    # 1. Headline validation
    if not headline_en or len(headline_en) < 15 or len(headline_en.split()) < 3:
        report.add("error", "invalid_headline_en", f"English headline is empty or too short: {headline_en!r}", event_id)
        return False
    if not headline_hi or not DEVANAGARI_RE.search(headline_hi):
        report.add("error", "missing_headline_hi", "Hindi headline is missing or lacks Devanagari script", event_id)
        return False

    # 2. Key Points / Detailed Analysis
    kps_en = item.get("key_points_en") or []
    kps_hi = item.get("key_points_hi") or []
    det_en = item.get("detailed_explanation_en") or ""
    det_hi = item.get("detailed_explanation_hi") or ""

    if not kps_en and not det_en:
        report.add("error", "missing_content_en", "Item has neither key points nor detailed explanation in English", event_id)
        return False
    if not kps_hi and not det_hi:
        report.add("error", "missing_content_hi", "Item has neither key points nor detailed explanation in Hindi", event_id)
        return False

    # Word count estimation
    full_en = (headline_en + " " + " ".join(kps_en) + " " + det_en).strip()
    full_hi = (headline_hi + " " + " ".join(kps_hi) + " " + det_hi).strip()
    words_en = len(full_en.split())
    words_hi = len(full_hi.split())

    if words_en < 25:
        report.add("warning", "shallow_story_en", f"English text is very brief ({words_en} words)", event_id, words=words_en)
    if words_hi < 20:
        report.add("warning", "shallow_story_hi", f"Hindi text is very brief ({words_hi} words)", event_id, words=words_hi)

    # 3. Numeric consistency between English and Hindi
    nums_en = extract_numbers_from_text(full_en)
    nums_hi = extract_numbers_from_text(full_hi)
    # Any two-or-more-digit figure present in English but absent from Hindi is a
    # likely translation drift (exam figures must survive translation unchanged).
    missing_nums = {
        n for n in nums_en
        if n not in nums_hi
        and n.replace(",", "") not in full_hi
        and len(n.replace(",", "").replace(".", "")) >= 2
    }
    if missing_nums:
        report.add("info", "numeric_divergence",
                   f"Numbers {sorted(missing_nums)[:3]} in EN not found in HI text", event_id)

    # 4. Static GK & Background
    static_facts = item.get("static_facts") or {}
    if static_facts:
        report.items_with_static_gk += 1

    # 5. Source attribution
    src = item.get("source") or {}
    src_url = src.get("url") or item.get("source_url") or ""
    if src_url or src.get("name") or item.get("source_name"):
        report.items_with_sources += 1
    else:
        report.add("warning", "missing_source_attribution", "Item has no verified source name or URL", event_id)

    if bool(det_en):
        report.items_with_detailed_explanation += 1

    return True


def validate_content_completeness(content: Dict[str, Any]) -> CompletenessReport:
    """Validate all stories in a content payload before passing to PDF renderer."""
    report = CompletenessReport()
    items = content.get("items") or []
    report.total_items = len(items)

    if not items:
        report.add("error", "zero_items", "Content payload contains 0 news items; refusing to render empty edition")
        return report

    total_words_en = 0
    total_words_hi = 0
    valid_count = 0

    for it in items:
        en_text = (it.get("headline_en", "") + " " + " ".join(it.get("key_points_en", [])) + " " + (it.get("detailed_explanation_en") or "")).strip()
        hi_text = (it.get("headline_hi", "") + " " + " ".join(it.get("key_points_hi", [])) + " " + (it.get("detailed_explanation_hi") or "")).strip()
        total_words_en += len(en_text.split())
        total_words_hi += len(hi_text.split())

        if validate_item_completeness(it, report):
            valid_count += 1

    report.complete_items = valid_count
    report.average_words_en = total_words_en / len(items) if items else 0.0
    report.average_words_hi = total_words_hi / len(items) if items else 0.0

    return report
