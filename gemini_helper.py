#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini LLM Helper & Prompt Templates for Agri Learning Point Bilingual Pipeline
==============================================================================
Provides structured JSON prompt templates to convert daily current affairs news
into the exact Exam Genius / Agri Learning Point Bilingual MCQ-First schema:
  - `question_en` & `question_hi`
  - 5 options (`A)` to `E)`) with `English / हिंदी` formatting
  - `answer` (`Option A` .. `Option E`)
  - 5 to 6 `explanation_pairs` (`[{"en": "...", "hi": "..."}]`)
  - 5 to 7 `static_gk` bilingual pairs (`[{"en": "...", "hi": "..."}]`)
"""

from __future__ import annotations
import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger("pipeline.gemini_helper")

EXAM_GENIUS_BILINGUAL_PROMPT = """You are an expert editor for 'Agri Learning Point' (Competitive Exams: IBPS AFO, NABARD, ICAR, UPSC, SSC, Banking, State Agri Exams).
Given the following news article, produce a JSON object strictly matching this structure:
{
  "question_en": "Clear exam-oriented question in English?",
  "question_hi": "उसी प्रश्न का सटीक और स्वाभाविक हिंदी अनुवाद?",
  "options": [
    "Option A in English / हिंदी में विकल्प A",
    "Option B in English / हिंदी में विकल्प B",
    "Option C in English / हिंदी में विकल्प C",
    "Option D in English / हिंदी में विकल्प D",
    "Option E in English / हिंदी में विकल्प E"
  ],
  "answer": "Option B",
  "explanation_pairs": [
    {
      "en": "First detailed factual sentence in English with exact dates, figures, and ministries.",
      "hi": "उसी पहले वाक्य का सटीक हिंदी अनुवाद (देवनागरी में)।"
    },
    {
      "en": "Second detailed factual sentence in English.",
      "hi": "दूसरे वाक्य का सटीक हिंदी अनुवाद।"
    },
    {
      "en": "Third detailed factual sentence in English.",
      "hi": "तीसरे वाक्य का सटीक हिंदी अनुवाद।"
    },
    {
      "en": "Fourth detailed factual sentence in English.",
      "hi": "चौथे वाक्य का सटीक हिंदी अनुवाद।"
    },
    {
      "en": "Fifth detailed factual sentence in English.",
      "hi": "पाँचवें वाक्य का सटीक हिंदी अनुवाद।"
    }
  ],
  "static_gk": [
    {
      "en": "Organisation establishment: Year/Date.",
      "hi": "संगठन की स्थापना: वर्ष/तारीख।"
    },
    {
      "en": "Headquarters: City, State/Country.",
      "hi": "मुख्यालय: शहर, राज्य/देश।"
    },
    {
      "en": "Nodal Ministry: Ministry Name.",
      "hi": "नोडल मंत्रालय: मंत्रालय का नाम।"
    }
  ]
}
Rules:
1. Always provide exactly 5 options (A to E). If options are pure numbers/dates, no slash is needed; if text/names, format as 'English / हिंदी'.
2. Provide 5 to 6 explanation_pairs where every English bullet is paired with its exact Hindi translation.
3. Provide 4 to 7 static_gk pairs covering Establishment, Headquarters, Nodal Ministry, Launch Year, or Act.
"""


def build_prompt_for_article(article: Dict[str, Any]) -> str:
    title = article.get("title_en") or article.get("title", "")
    summary = article.get("summary_en") or article.get("summary", "")
    return f"{EXAM_GENIUS_BILINGUAL_PROMPT}\n\nArticle Title: {title}\nArticle Text: {summary}\n"
