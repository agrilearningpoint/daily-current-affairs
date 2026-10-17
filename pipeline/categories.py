# -*- coding: utf-8 -*-
"""Canonical news-category vocabulary.

Single source of truth for the mapping between *source-registry category keys*
(config/sources.py, e.g. ``economy_data``, ``agriculture_core``) and the
canonical category names every downstream stage compares against
(scoring boosts, student relevance, selection priority, PDF sections).

This module is deliberately dependency-free: importing it must never pull in a
collector, a network client, or the source registry, so that artifact
normalisation stays available in every stage (and in tests) even when the
registry is not importable.
"""

from __future__ import annotations

# Canonical category names used by downstream priority/boost logic.
CANONICAL_CATEGORIES = (
    "Agriculture",
    "Banking & Finance",
    "Economy",
    "Government Schemes",
    "National",
    "International",
    "Science & Technology",
    "Environment",
    "Sports",
    "Health",
)

# Legacy/short names already canonical in the artifact contract.
CATEGORY_NAMES = {
    "agriculture": "Agriculture", "agri": "Agriculture",
    "banking": "Banking & Finance", "finance": "Banking & Finance",
    "banking & finance": "Banking & Finance", "economy": "Economy",
    "government": "Government Schemes", "government schemes": "Government Schemes",
    "national": "National", "general": "National", "international": "International",
    "science": "Science & Technology", "science & technology": "Science & Technology",
    "environment": "Environment", "sports": "Sports", "health": "Health",
}

# Source-registry category keys -> canonical names.
CATEGORY_ALIASES = {
    # agriculture
    "agriculture_core": "Agriculture", "agriculture_economy": "Agriculture",
    "agriculture_specialists": "Agriculture", "horticulture": "Agriculture",
    "food_processing": "Agriculture", "rural_development": "Agriculture",
    "rural": "Agriculture", "cooperation": "Agriculture",
    # banking / economy
    "banking_finance": "Banking & Finance",
    "economy_data": "Economy", "economy": "Economy", "finance_economy": "Economy",
    # government / national
    "govt_national": "National", "govt": "National", "government": "Government Schemes",
    "discovery": "National", "aggregator": "National", "education": "National",
    "defence": "National",
    # science / environment / health
    "defence_science": "Science & Technology", "science": "Science & Technology",
    "food_safety": "Science & Technology", "health": "Science & Technology",
    "environment": "Environment", "forestry_environment": "Environment",
    "energy": "Environment",
    # explicit passthroughs
    "agriculture": "Agriculture", "international": "International", "general": "National",
}

DEFAULT_CATEGORY = "National"


def normalize_category(category) -> str:
    """Map a source/legacy category key to its canonical category name.

    Unknown values are preserved verbatim (never dropped and never guessed),
    so an unmapped source key stays visible in the artifact instead of being
    silently merged into another section.
    """
    if category is None:
        return DEFAULT_CATEGORY
    raw = str(category).strip()
    if not raw:
        return DEFAULT_CATEGORY
    key = raw.lower()
    if key in CATEGORY_NAMES:
        return CATEGORY_NAMES[key]
    if key in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[key]
    if raw in CANONICAL_CATEGORIES:
        return raw
    return raw
