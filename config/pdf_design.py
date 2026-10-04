# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — PROFESSIONAL PDF LAYOUT — FINAL DESIGN COMMAND
Mobile-first, premium, intelligent space usage — DO NOT optimize for page count
"""

PDF_DESIGN_SPEC = {
    "principle": "Use space intelligently. Do NOT leave unnecessary blank space. Never place heading alone at bottom/top. If heading followed by only 1-2 lines, move heading together with content to next page. Do NOT force too much content onto one page. Goal: Maximum useful info + excellent readability + minimum wasted space.",
    "page_break_rules": [
        "New page only when major category genuinely needs fresh page",
        "Large table cannot fit properly",
        "Major visual story requires full-width",
        "Current page naturally full",
        "Starting next section on current page would damage readability",
        "Otherwise continue naturally on same page"
    ],
    "no_orphan_headings": "Never allow heading followed by only 1 line/1 bullet/empty area/table on next page. Keep heading attached to at least first meaningful content block.",
    "content_flow": ["News Headline", "Key Points", "Important Facts / Static Facts", "Exam Fact", "Explanation / MCQ"],
    "layout": {
        "type": "Single-column mobile-first",
        "margins": {"top": "12-15mm", "bottom": "12-15mm", "left": "12-14mm", "right": "12-14mm"},
        "actual": {"top": "13mm", "bottom": "13mm", "left": "13mm", "right": "13mm"},
        "note": "Do not create oversized margins"
    },
    "font_hierarchy": {
        "main_title": "18-20pt Bold",
        "hindi_headline": "17-19pt Bold — Mukta",
        "section_heading": "15-17pt Bold — 16pt used",
        "sub_heading_keypoints": "13-14pt Semi-bold",
        "main_body_en": "11.5-12.5pt — Poppins 12pt, leading 16 (1.33)",
        "hindi_body": "12-13pt — Mukta 12.5pt, leading 16.5 (1.32)",
        "static_facts": "11.5-12pt",
        "exam_fact": "12-13pt Bold/semibold — 12.5pt",
        "mcq_question": "12-13pt — 12.5pt",
        "mcq_options": "11.5-12pt — 11.5pt",
        "explanation": "11-12pt — 11pt",
        "footer": "8.5-9.5pt — 9pt",
        "watermark": "8-10pt Very subtle — 0.09 alpha, logo centered 90mm"
    },
    "mobile_optimal": {
        "hindi": "Mukta 12.5pt",
        "english": "Poppins 12pt (Inter fallback)",
        "headline": "18pt",
        "section": "16pt",
        "mcq": "12.5pt",
        "footer": "9pt",
        "line_spacing": "1.25-1.35 (actual 1.30-1.33)",
        "note": "10pt or less body avoid — would require zoom. Prefer less content per page + big readable font + white space. Do not compress 50-page into 25."
    },
    "fonts": {
        "hindi": "Mukta (Regular, SemiBold, Bold) — Primary for Hindi",
        "english": "Poppins (Regular, SemiBold, Bold) — Primary for English, Inter as fallback",
        "max_families": 2,
        "limit": "Maximum 2 primary font families"
    },
    "tables": {
        "use_when": ["Appointments", "Awards", "Reports & Rankings", "Schemes", "Organizations", "Headquarters", "Dates", "Agri stats", "Banking facts", "Country comparisons", "Crop/variety", "Govt initiatives"],
        "must_be": ["compact", "readable on mobile", "properly aligned", "visually separated", "never overcrowded"],
        "if_too_wide": "Convert to vertical fact card instead of tiny text"
    },
    "cards": ["EXAM FACT", "STATIC FACTS", "IMPORTANT", "REMEMBER", "AGRICULTURE FOCUS"],
    "images": "Only when adds educational/visual value. One meaningful image, proportional, beside/above info, text priority. Never random stock to fill space.",
    "colors": {
        "Agriculture": "Green #1B5E20/#2E7D32",
        "Banking & Finance": "Blue #0D47A1",
        "National": "Orange #E65100",
        "International": "Purple #4A148C",
        "Science & Technology": "Cyan/Blue #01579B",
        "Environment": "Green/Teal #33691E",
        "Awards": "Gold #F57F17",
        "Important/Alert": "Red #B71C1C",
        "Exam Fact": "Yellow/Gold #FFF9C4/#FBC02D",
        "use_for": ["headings", "section labels", "borders", "cards", "important facts", "tables"]
    },
    "header": "Compact: AGRI LEARNING POINT + logo on every page, not too tall, do not waste space",
    "footer": "Agri Learning Point | BY SATYAM SIR | Page X — compact 9pt",
    "content_density": "No fixed page count. Do not compress to reduce pages, do not expand to increase. Natural by content importance + readability + layout quality.",
    "smart_page_filling": "Before new page, check if remaining space can accommodate heading + 2-3 lines/table/fact box/next short news. If yes continue, if no move complete block to next page.",
    "section_continuity": "If section continues, use small label 'Agriculture & Allied — Continued' only when necessary, do not repeat entire section.",
    "mcq_section": "2-4 MCQs per page, format: Question / A-E Options / Answer: B / Explanation short exam-focused",
    "bilingual": "EN upar, Hindi directly below, no large gaps, consistent alignment, same facts/numbers/names/dates",
    "quality_control": ["No orphan heading", "No unnecessary blank", "No huge empty areas", "No overcrowded", "No tiny text", "No broken tables", "Tables not cut incorrectly", "Images not overlapping", "Content not cut off", "No blank page", "No duplicate", "Header present", "Footer present", "Page number correct", "Hindi rendering correct", "English correct", "Consistent spacing/typography", "Professional balance"],
    "final_rule": "PDF should look like professionally edited competitive-exam book, not AI-generated pages. Optimize for best reading experience + maximum useful info per page. Do not optimize for fewer/more pages."
}

# Previous best colors (kept as final)
COLORS = {
    "primary_green": "#1B5E20",
    "agri_accent": "#2E7D32",
    "banking_blue": "#0D47A1",
    "national_orange": "#E65100",
    "international_purple": "#4A148C",
    "economy_teal": "#006064",
    "science_cyan": "#01579B",
    "environment_green": "#33691E",
    "sports_red": "#B71C1C",
    "awards_gold": "#F57F17",
    "exam_yellow": "#FFF9C4",
    "exam_yellow_border": "#FBC02D",
}
