#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agri Learning Point - Branding, Social Channels & Template Configuration
========================================================================
Centralized configuration for the Exam-Genius-style Bilingual PDF layout,
cover page badges, curved top header banner, watermark, and 3 social handles:
  1. YouTube Channel: Agri Learning Point
  2. Telegram Channel 1: Agri Learning Point
  3. Telegram Channel 2: Agri Quiz World
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent

BRANDING_CONFIG: Dict[str, Any] = {
    # Cover Page Top & Hero Text
    "brand_title_upper": "AGRI LEARNING POINT",
    "presents_text": "Presents",
    "cover_hero_lines": ["AGRI", "CURRENT", "AFFAIRS"],
    "bilingual_tag": "In Bilingual",
    "bottom_tagline": "Achieve Success with Agri Learning Point - Your Ultimate Guide to Agriculture & Govt. Exams !",

    # Cover Page 5 Exam Pill Badges (Matching Demo PDF style)
    "cover_exam_badges": [
        {"label": "UPSC / PCS", "icon": "pillar"},
        {"label": "IBPS AFO", "icon": "bank"},
        {"label": "NABARD", "icon": "leaf"},
        {"label": "ICAR / JRF", "icon": "user"},
        {"label": "STATE AGRI", "icon": "state"},
    ],

    # Content Page Curved Top Header Banner
    "header_line_1": "No. 1 PLATFORM FOR AGRI & GOVT. EXAMS",
    "header_line_2": "IBPS AFO | NABARD | ICAR | AGTA | BANKING | SSC",
    "header_link_text": "t.me/agrilearningpoint",
    "header_link_url": "https://t.me/agrilearningpoint",

    # Content Page Bottom Social Bar (Strictly the 3 channels owned by user)
    "social_handles": [
        {
            "platform": "youtube",
            "label": "Agri Learning Point",
            "url": "https://www.youtube.com/@agrilearningpoint",
        },
        {
            "platform": "telegram",
            "label": "Agri Learning Point",
            "url": "https://t.me/agrilearningpoint",
        },
        {
            "platform": "telegram",
            "label": "Agri Quiz World",
            "url": "https://t.me/agriquizworld",
        },
    ],

    # Asset Paths
    "logo_path": str(ROOT_DIR / "assets" / "logo.png"),
    "watermark_path": str(ROOT_DIR / "assets" / "watermark_logo.png"),
}
