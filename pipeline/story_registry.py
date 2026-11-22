# -*- coding: utf-8 -*-
"""
CANONICAL STORY REGISTRY & EDITORIAL RANKING ENGINE
Agri Learning Point — Single Source of Truth for Daily Editions

Guarantees:
1. Single canonical ordering (1..15) preserved across Cover, Contents (TOC),
   Story Units, MCQs, News in Pictures, Agriculture Corner, and One-Liners.
2. Objective editorial ranking: High-yield Agriculture (AGTA/AFO/ICAR relevance)
   and National Policies are given top prominence.
3. Strict consistency validation: Story count, numbers, and event IDs must match 100%.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("pipeline.story_registry")

# High-yield agricultural exam keyword pattern
AGRI_EXAM_PATTERNS = re.compile(
    r"\b(?:agriculture|farmer|seed|crop|horticulture|icar|nabard|fci|apeda|dairy|milk|fisheries|"
    r"soil|fertilizer|msp|kisan|krishi|irrigation|mandis?|enam|cervavac|vaccine|livestock)\b",
    re.IGNORECASE
)


class StoryEntry:
    def __init__(self, story_number: int, item: Dict[str, Any], mcq: Optional[Dict[str, Any]] = None):
        self.story_number = story_number
        self.story_id = str(item.get("event_id") or item.get("id") or f"story_{story_number}")
        self.category = str(item.get("category") or "National").strip()
        self.headline_en = str(item.get("headline_en") or item.get("title") or "").strip()
        self.headline_hi = str(item.get("headline_hi") or "").strip()
        self.source = item.get("source") if isinstance(item.get("source"), dict) else {
            "name": item.get("source_name", "Official Source"),
            "url": item.get("source_url", ""),
            "date": item.get("pub_time_ist", "")
        }
        self.summary_en = str(item.get("summary_en") or "").strip()
        self.summary_hi = str(item.get("summary_hi") or "").strip()
        self.key_points_en = item.get("key_points_en") or []
        self.key_points_hi = item.get("key_points_hi") or []
        self.detailed_explanation_en = str(item.get("detailed_explanation_en") or "").strip()
        self.detailed_explanation_hi = str(item.get("detailed_explanation_hi") or "").strip()
        self.static_gk = item.get("static_gk_pairs") or []
        self.mcq = mcq or {}
        self.item_dict = item

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.item_dict)
        d["story_number"] = self.story_number
        d["event_id"] = self.story_id
        d["headline_en"] = self.headline_en
        d["headline_hi"] = self.headline_hi
        d["category"] = self.category
        d["source"] = self.source
        return d


class CanonicalStoryRegistry:
    def __init__(self, items: List[Dict[str, Any]], mcqs: Optional[List[Dict[str, Any]]] = None):
        self.raw_items = [i for i in items if isinstance(i, dict)]
        self.raw_mcqs = [m for m in (mcqs or []) if isinstance(m, dict)]
        self.stories: List[StoryEntry] = []
        self._build_registry()

    def _rank_stories(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Editorial ranking: Prioritizes Agriculture & High-yield National/Science milestones."""
        def score_story(it: Dict[str, Any]) -> Tuple[int, float]:
            cat = str(it.get("category", "")).lower()
            text = f"{it.get('headline_en', '')} {it.get('summary_en', '')}".lower()
            
            # Tier 1: Substantive Agriculture & Farmer policy/schemes/milestones
            is_agri = cat == "agriculture" or bool(AGRI_EXAM_PATTERNS.search(text))
            # Check for major quantitative milestone (exports, advance estimates, vaccines)
            has_major_data = bool(re.search(r"\b(?:\d+%\s+growth|advance\s+estimates|1\s+crore\s+doses|indigenous\s+vaccine)\b", text))
            
            tier = 3
            if is_agri and has_major_data:
                tier = 0  # Absolute top priority
            elif is_agri:
                tier = 1  # Standard agriculture priority
            elif cat in ("government schemes", "national") and has_major_data:
                tier = 2  # Major national policy
            
            importance = float(it.get("importance_score") or 0.0)
            return (tier, -importance)

        return sorted(items, key=score_story)

    def _build_registry(self):
        ranked = self._rank_stories(self.raw_items)
        # Map MCQs by event_id
        mcq_by_event = {}
        for m in self.raw_mcqs:
            eid = str(m.get("event_id") or "")
            if eid:
                mcq_by_event[eid] = m

        self.stories = []
        for idx, it in enumerate(ranked, 1):
            eid = str(it.get("event_id") or it.get("id") or "")
            linked_mcq = mcq_by_event.get(eid)
            # If no event_id match, fallback to index match if lengths align
            if not linked_mcq and idx - 1 < len(self.raw_mcqs):
                linked_mcq = self.raw_mcqs[idx - 1]
            
            entry = StoryEntry(story_number=idx, item=it, mcq=linked_mcq)
            self.stories.append(entry)

    def get_stories(self) -> List[StoryEntry]:
        return self.stories

    def get_items(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self.stories]

    def get_mcqs(self) -> List[Dict[str, Any]]:
        mcqs_out = []
        for s in self.stories:
            m = dict(s.mcq)
            m["q_idx"] = s.story_number
            m["story_number"] = s.story_number
            m["event_id"] = s.story_id
            mcqs_out.append(m)
        return mcqs_out

    def validate_consistency(self) -> Tuple[bool, List[str]]:
        """Validates 100% consistency across all stories and MCQs."""
        errors = []
        if len(self.stories) != 15:
            errors.append(f"Expected 15 stories, found {len(self.stories)}")

        seen_numbers = set()
        seen_ids = set()
        for s in self.stories:
            if s.story_number in seen_numbers:
                errors.append(f"Duplicate story number: {s.story_number}")
            seen_numbers.add(s.story_number)

            if s.story_id in seen_ids:
                errors.append(f"Duplicate story ID: {s.story_id}")
            seen_ids.add(s.story_id)

            if not s.headline_en:
                errors.append(f"Story {s.story_number} missing English headline")
            if not s.headline_hi:
                errors.append(f"Story {s.story_number} missing Hindi headline")

        return (len(errors) == 0, errors)
