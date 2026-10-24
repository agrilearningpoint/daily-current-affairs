#!/usr/bin/env bash
# ==============================================================================
# Agri Learning Point - Exam Genius Style Bilingual PDF Upgrade Installer & Push
# ==============================================================================
# Run this script from the root of your cloned `daily-current-affairs` repo:
#   bash apply_and_push.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/4] Copying updated Agri Learning Point files and assets into repository..."
cp -v "${SCRIPT_DIR}/assets/logo.png" ./assets/logo.png
cp -v "${SCRIPT_DIR}/assets/watermark_logo.png" ./assets/watermark_logo.png
cp -v "${SCRIPT_DIR}/config/branding.py" ./config/branding.py
cp -v "${SCRIPT_DIR}/src/generate_pdf.py" ./src/generate_pdf.py
cp -v "${SCRIPT_DIR}/pipeline/static_gk_db.py" ./pipeline/static_gk_db.py
cp -v "${SCRIPT_DIR}/pipeline/content.py" ./pipeline/content.py
cp -v "${SCRIPT_DIR}/pipeline/gemini_helper.py" ./pipeline/gemini_helper.py
cp -v "${SCRIPT_DIR}/agents/12_content_editor.py" ./agents/12_content_editor.py
cp -v "${SCRIPT_DIR}/agents/16_mcq_generator.py" ./agents/16_mcq_generator.py
cp -v "${SCRIPT_DIR}/agents/17_mcq_validator.py" ./agents/17_mcq_validator.py
cp -v "${SCRIPT_DIR}/agents/18_pdf_design.py" ./agents/18_pdf_design.py
cp -v "${SCRIPT_DIR}/agents/19_pdf_qa.py" ./agents/19_pdf_qa.py

echo "[2/4] Staging all updated files in git..."
git add assets/logo.png assets/watermark_logo.png \
        config/branding.py \
        src/generate_pdf.py \
        pipeline/static_gk_db.py pipeline/content.py pipeline/gemini_helper.py \
        agents/12_content_editor.py agents/16_mcq_generator.py agents/17_mcq_validator.py \
        agents/18_pdf_design.py agents/19_pdf_qa.py

echo "[3/4] Committing changes..."
git commit -m "feat(pdf): upgrade to Exam-Genius-style Bilingual MCQ-First PDF layout with Agri Learning Point branding & 3 social handles"

echo "[4/4] Pushing to origin main..."
git push origin main

echo "✅ Done! All changes have been committed and pushed to origin/main."
