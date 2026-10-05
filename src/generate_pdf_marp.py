# -*- coding: utf-8 -*-
"""
Marp-based Vector Hindi PDF Generator — Phase A
Converts content JSON → Markdown → Marp PDF via Chrome (HarfBuzz)
Uses Noto Sans Devanagari via config/theme_agri.css (scrape pattern)
Fallback: if marp not installed, use existing reportlab with 450DPI RAQM
"""
import os, json, subprocess, tempfile, shutil
from pathlib import Path

ROOT = os.environ.get("ALP_ROOT", os.getcwd())
THEME = os.path.join(ROOT, "config", "theme_agri.css")

def content_to_markdown(content, mcqs):
    # Build markdown for Marp
    lines = [
        "---",
        "marp: true",
        "theme: agri",
        "paginate: true",
        "size: A4",
        "style: |",
        f"  @import url('{THEME}');",
        "---",
        ""
    ]
    lines.append(f"# Agri Learning Point — {content.get('date','')} Current Affairs")
    lines.append("")
    for idx, it in enumerate(content.get("items",[]), 1):
        cat = it.get("category","general")
        klass = "agri" if "agri" in cat.lower() else "banking" if "bank" in cat.lower() else "general"
        lines.append(f'<div class="news-card {klass}">')
        lines.append(f"## {idx}. {it.get('headline_en','')} / {it.get('headline_hi','')}")
        lines.append("")
        # Key points bilingual
        lines.append("**Key Points:**")
        for kp_en, kp_hi in zip(it.get("key_points_en",[]), it.get("key_points_hi",[])):
            lines.append(f"- {kp_en} / {kp_hi}")
        lines.append("")
        # Static facts
        if it.get("static_facts"):
            lines.append('<div class="static-facts">')
            for k,v in it["static_facts"].items():
                lines.append(f"- **{k}:** {v}")
            lines.append('</div>')
            lines.append("")
        # Exam fact
        if it.get("exam_fact_en"):
            lines.append(f'<div class="exam-fact">💡 {it["exam_fact_en"]} / {it.get("exam_fact_hi","")}</div>')
            lines.append("")
        lines.append(f'<small>Source: {it.get("source","")} | {it.get("category","")}</small>')
        lines.append('</div>')
        lines.append("")
        lines.append("---")
        lines.append("")
    # MCQs
    lines.append("# MCQs")
    lines.append("")
    for q in mcqs.get("mcqs",[]):
        lines.append('<div class="mcq">')
        lines.append(f"**Q{q.get('q_num')}. {q.get('question_en','')}**")
        if q.get("question_hi"):
            lines.append(f"*{q['question_hi']}*")
        lines.append("")
        for i, opt in enumerate(q.get("options_en",[])):
            marker = "✅" if i == q.get("correct",-1) else "○"
            lines.append(f"- {marker} {opt} / {q.get('options_hi',['']*4)[i] if i < len(q.get('options_hi',[])) else ''}")
        lines.append("")
        lines.append(f"**Explanation:** {q.get('explanation_en','')} / {q.get('explanation_hi','')}")
        lines.append('</div>')
        lines.append("")
    return "\n".join(lines)

def generate_pdf_marp(content, mcqs, output_path=None):
    md = content_to_markdown(content, mcqs)
    if not output_path:
        output_path = os.path.join(ROOT, "output", f"Agri Learning Point {content.get('date','')} Marp.pdf")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(md)
        md_path = f.name
    # Try marp
    if shutil.which("npx") or shutil.which("marp"):
        try:
            cmd = ["npx", "-y", "@marp-team/marp-cli", md_path, "--pdf", "--allow-local-files", "--theme", THEME, "-o", output_path]
            subprocess.run(cmd, check=True, timeout=60)
            print(f"✓ Marp PDF: {output_path}")
            return output_path
        except Exception as e:
            print(f"Marp failed ({e}), falling back to reportlab RAQM")
    else:
        print("Marp not installed, fallback to reportlab RAQM")
    # fallback to existing reportlab
    from src.generate_pdf import generate_pdf as rb_pdf
    return rb_pdf(content, mcqs, output_path)

if __name__ == "__main__":
    import sys
    c = json.load(open(sys.argv[1], encoding="utf-8"))
    m = json.load(open(sys.argv[2], encoding="utf-8"))
    print(generate_pdf_marp(c,m))
