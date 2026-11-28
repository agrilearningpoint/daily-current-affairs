# -*- coding: utf-8 -*-
"""Phase 8-13 regression tests: Branding, Image Hardening, Visual PDF QA, Release Gate,
Self-Improvement Engine, and Edition Report Generator."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_agent(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, str(ROOT / rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestBrandingAndImages:
    def test_godl_license_accepted(self):
        from pipeline.news_images import FREE_LICENSE_RE
        assert FREE_LICENSE_RE.match("GODL-India")
        assert FREE_LICENSE_RE.match("CC-BY-SA 4.0")
        assert FREE_LICENSE_RE.match("Public Domain")
        assert not FREE_LICENSE_RE.match("All rights reserved")

    def test_branding_palette_unified_with_generate_pdf(self):
        from config.branding import BRAND_PALETTE
        import src.generate_pdf as gp
        assert set(BRAND_PALETTE.keys()).issubset(set(gp.COLORS.keys()))
        assert gp.COLORS["primary"].hexval().lower().endswith(BRAND_PALETTE["primary"].lstrip("#").lower())


class TestVisualPdfQaAndReleaseGate:
    def test_visual_qa_inspects_real_pdf_and_detects_blank(self, tmp_path):
        fitz = pytest.importorskip("fitz")
        from pipeline.pdf_visual_qa import inspect_pdf_visuals

        pdf_ok = tmp_path / "good.pdf"
        doc = fitz.open()
        p1 = doc.new_page(width=595, height=842)
        p1.insert_text((72, 100), "Agri Learning Point Cover", fontsize=18)
        p2 = doc.new_page(width=595, height=842)
        p2.insert_text((72, 120), "Main Story Section\nDetails follow here cleanly.", fontsize=12)
        doc.save(str(pdf_ok))
        doc.close()

        previews = tmp_path / "previews"
        res = inspect_pdf_visuals(pdf_ok, preview_dir=previews)
        assert res["available"] is True
        assert res["passed"] is True
        assert res["pages_rendered"] == 2
        assert res["blank_visual_pages"] == []
        assert len(res["preview_paths"]) == 2
        assert all(Path(p).is_file() for p in res["preview_paths"])

        # Now PDF with 2 blank pages should fail passed
        pdf_blank = tmp_path / "blank.pdf"
        doc2 = fitz.open()
        doc2.new_page(width=595, height=842)
        doc2.new_page(width=595, height=842)
        doc2.save(str(pdf_blank))
        doc2.close()
        res_blank = inspect_pdf_visuals(pdf_blank)
        assert res_blank["available"] is True
        assert res_blank["blank_visual_pages"] == [1, 2]
        assert res_blank["passed"] is False

    def test_release_signature_verification_and_tamper_detection(self):
        qa = _load_agent("agents/19_pdf_qa.py", "qa19_sig_test")
        sig = qa.release_signature_for("daily_2026-11-28", "abc123", True, True)
        doc = {
            "job_id": "daily_2026-11-28",
            "file_sha256": "abc123",
            "passed": True,
            "release_approval": {
                "approved": True,
                "visual_passed": True,
                "signature": sig,
            },
        }
        assert qa.verify_release_signature(doc) is True
        tampered = dict(doc, file_sha256="deadbeef")
        assert qa.verify_release_signature(tampered) is False


class TestSelfImprovementAndEditionReport:
    def test_self_improvement_analyzes_and_records(self, tmp_path):
        from pipeline.self_improvement import analyze_history, record_learning_cycle
        (tmp_path / "state" / "metrics").mkdir(parents=True)
        (tmp_path / "logs" / "qa").mkdir(parents=True)

        jobs = {
            "jobs": {
                "daily_2026-11-26": {"status": "success"},
                "daily_2026-11-27": {"status": "failed", "failed_stage": "12_content_editor"},
                "daily_2026-11-28": {"status": "failed", "failed_stage": "12_content_editor"},
                "daily_2026-11-29": {"status": "failed", "failed_stage": "12_content_editor"},
            }
        }
        (tmp_path / "state" / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
        (tmp_path / "logs" / "qa" / "daily_2026-11-26_qa.json").write_text(
            json.dumps({"hindi_pct": 22.5, "issues": [{"code": "few_photos"}]}),
            encoding="utf-8",
        )
        summary = record_learning_cycle("daily_2026-11-29", repo_root=tmp_path)
        assert summary["jobs_analyzed"] == 4
        assert summary["top_failed_stages"]["12_content_editor"] == 3
        assert any(r["target"] == "12_content_editor" and r["priority"] == "high"
                   for r in summary["recommendations"])
        assert (tmp_path / "state" / "metrics" / "self_improvement_recommendations.json").is_file()
        assert (tmp_path / "state" / "metrics" / "learning_history.json").is_file()

    def test_edition_report_creates_json_and_markdown(self, tmp_path):
        from pipeline.edition_report import build_edition_report
        for sub in ("data/raw", "data/verified", "data/content", "data/mcq", "logs/qa"):
            (tmp_path / sub).mkdir(parents=True)
        (tmp_path / "data/raw/daily_2026-11-28.json").write_text(json.dumps({"articles": [1, 2, 3]}), encoding="utf-8")
        (tmp_path / "data/content/daily_2026-11-28.json").write_text(
            json.dumps({"items": [{"id": 1}], "translation_stats": {"ai_passed": 5}}),
            encoding="utf-8",
        )
        (tmp_path / "data/mcq/daily_2026-11-28.json").write_text(json.dumps([{"q": 1}]), encoding="utf-8")
        (tmp_path / "logs/qa/daily_2026-11-28_qa.json").write_text(
            json.dumps({"passed": True, "page_count": 18, "hindi_pct": 25.0,
                        "mcq_count": 15, "duplicate_questions": 0, "substantive_pages": 14}),
            encoding="utf-8",
        )
        rep = build_edition_report("daily_2026-11-28", "daily", repo_root=tmp_path)
        assert rep["funnel"]["raw"] == 3
        assert rep["funnel"]["content"] == 1
        assert rep["funnel"]["mcqs"] == 1
        assert rep["pdf_qa"]["page_count"] == 18
        assert (tmp_path / "reports" / "daily_2026-11-28_edition_report.json").is_file()
        md = (tmp_path / "reports" / "daily_2026-11-28_edition_report.md").read_text(encoding="utf-8")
        assert "# Edition Report — daily_2026-11-28" in md
        assert "Valid" in md or "18" in md
