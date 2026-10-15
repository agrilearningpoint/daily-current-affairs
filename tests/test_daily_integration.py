"""Offline regressions for CLI, artifact handoffs, and the publication gate."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Thread
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from xml.sax.saxutils import escape

import pytest

import main
from pipeline.agent_context import JobContext
from pipeline.artifacts import news_items
from pipeline.source_registry import SourceConfigError, load_sources

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("flag", ["--type", "--job-type"])
def test_cli_aliases(flag):
    args = main.build_parser().parse_args([flag, "daily", "--reset"])
    assert args.type == "daily" and args.reset
    assert main.build_parser().parse_args(["--watchdog", "--stuck-hours", "4"]).stuck_hours == 4


@pytest.mark.parametrize("wrapper", [None, "items", "articles"])
def test_news_schema_normalizes_legacy_inputs(wrapper):
    item = {"title": "Agriculture scheme", "summary": "Outlay Rs 5000 Crore",
            "link": "https://example.invalid/news", "source_tier": 1,
            "category": "agriculture", "source_name": "Diagnostic"}
    data = [item] if wrapper is None else {wrapper: [item]}
    normalized = news_items(data)[0]
    assert normalized["headline_en"] == item["title"]
    assert normalized["raw_facts"] == item["summary"]
    assert normalized["source_url"] == item["link"]
    assert normalized["source_tier"] == "tier1"
    assert normalized["category"] == "Agriculture"
    assert normalized["event_id"]
    assert "headline_en" not in item


def test_input_discovery_does_not_use_another_date(tmp_path):
    folder = tmp_path / "data/raw"
    folder.mkdir(parents=True)
    (folder / "daily_2026-10-01.json").write_text("[]")
    ctx = JobContext("daily_2026-10-05", "daily", "2026-10-05", "daily_2026-10-05", repo_root=tmp_path)
    assert ctx.find_input("raw") is None


def test_registry_accepts_curated_tuple_feeds():
    specs = load_sources()
    assert specs and all(1 <= spec.tier <= 3 for spec in specs)
    assert any(spec.name == "ICAR" and spec.tier == 1 for spec in specs)


def test_registry_rejects_invalid_tier(monkeypatch):
    import config.feeds
    monkeypatch.setattr(config.feeds, "VERIFIED_RSS", [("Bad", "https://example.invalid/rss", "bad", "general")])
    with pytest.raises(SourceConfigError, match="invalid tier"):
        load_sources()


def test_reset_clears_only_the_requested_job(tmp_path, monkeypatch):
    # Use a dedicated temporary file, not the committed job ledger.
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps({"daily_2026-10-05": {"status": "running"},
                                "weekly_2026-10-04": {"status": "success"}}))
    monkeypatch.setattr(main, "JOBS_STATE_PATH", path)
    monkeypatch.setattr(main, "execute_job", lambda *args: 0)
    assert main.main(["--job-type", "daily", "--date", "2026-10-05", "--reset"]) == 0
    assert main.load_jobs_state(strict=True) == {"weekly_2026-10-04": {"status": "success"}}


def load_publisher():
    spec = importlib.util.spec_from_file_location("publisher_test", ROOT / "agents/22_telegram_publisher.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("approval", ["missing", "rejected", "wrong_hash", "wrong_job", "approved"])
def test_publish_requires_exact_qa_approval(tmp_path, monkeypatch, approval):
    publisher = load_publisher()
    monkeypatch.setattr(publisher, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(publisher, "DRY_RUN", True)
    monkeypatch.setattr(publisher, "send_document", lambda *a, **k: pytest.fail("network publish attempted"))
    pdf = tmp_path / "daily_2026-10-05.pdf"
    pdf.write_bytes(b"diagnostic pdf bytes")
    qa = tmp_path / "logs/qa/daily_2026-10-05_qa.json"
    qa.parent.mkdir(parents=True)
    if approval != "missing":
        qa.write_text(json.dumps({
            "passed": approval != "rejected", "job_id": "wrong" if approval == "wrong_job" else pdf.stem,
            "file_sha256": "wrong" if approval == "wrong_hash" else hashlib.sha256(pdf.read_bytes()).hexdigest(),
        }))
    assert publisher.publish_pdf(pdf, {"records": {}}) is (approval == "approved")


def test_live_publish_rejects_unreviewed_translation(tmp_path, monkeypatch):
    publisher = load_publisher()
    monkeypatch.setattr(publisher, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(publisher, "DRY_RUN", False)
    monkeypatch.setattr(publisher, "send_document", lambda *a, **k: pytest.fail("network publish attempted"))
    pdf = tmp_path / "daily_2026-10-05.pdf"
    pdf.write_bytes(b"diagnostic pdf bytes")
    qa = tmp_path / "logs/qa/daily_2026-10-05_qa.json"
    qa.parent.mkdir(parents=True)
    qa.write_text(json.dumps({"passed": True, "job_id": pdf.stem,
                              "file_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()}))
    content = tmp_path / "data/content/daily_2026-10-05.json"
    content.parent.mkdir(parents=True)
    content.write_text(json.dumps({"items": [{"needs_review": True}]}))
    assert not publisher.publish_pdf(pdf, {"records": {}})


@pytest.mark.parametrize("interrupt_feed", [False, True])
def test_daily_pipeline_end_to_end_without_external_services(tmp_path, interrupt_feed):
    """Run actual stage subprocesses against a local synthetic RSS feed."""
    root = tmp_path / "repo"
    root.mkdir()
    for directory in ("agents", "pipeline", "config", "src", "assets"):
        shutil.copytree(ROOT / directory, root / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "images"))
    shutil.copy2(ROOT / "main.py", root / "main.py")
    headlines = [
        ("Cabinet Approves Agriculture Export Scheme with Rs 5000 Crore Outlay", "Union Cabinet approved an agriculture export scheme. Outlay Rs 5000 Crore for APEDA promotion."),
        ("RBI Keeps Repo Rate at 6.00 Percent and CPI Inflation at 4.6 Percent", "RBI monetary policy committee decision keeps repo rate at 6.00 percent. CPI inflation at 4.6 percent."),
        ("ISRO Launches NVS Navigation Satellite from Sriharikota", "ISRO launched a new navigation satellite from Sriharikota. This expands the national science mission."),
        ("India Wins Gold Medal in Asian Games Hockey Final", "India defeated Japan in the Asian Games hockey final. The team won a gold medal."),
        ("FAO Releases State of Food and Agriculture Report", "FAO published a report on farming and agriculture. Crop GDP growth measured 3.5 percent."),
        ("NABARD Announces Refinance Facility of Rs 20000 Crore", "NABARD announced a refinance facility for rural cooperative banks. Credit limit is Rs 20000 Crore."),
        ("ICAR Develops Drought Resistant Seed for Farmers", "ICAR reported a drought resistant crop variety for farmers. Irrigation research targets expansion in 2030."),
        ("World Bank Funds Soil Conservation Project in India", "World Bank approved a national soil conservation project. Agriculture investment is USD 300 million."),
    ]
    entries = "".join(
        f"<item><title>{escape(title)}</title><link>https://example.invalid/fixture/{i}</link>"
        f"<description>{escape(summary)}</description><pubDate>Sun, 04 Oct 2026 12:00:00 GMT</pubDate></item>"
        for i, (title, summary) in enumerate(headlines)
    )
    body = (f'<rss version="2.0"><channel><title>Synthetic test feed</title>{entries}</channel></rss>').encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if interrupt_feed and not getattr(self.server, "dropped_once", False):
                self.server.dropped_once = True
                self.connection.close()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/rss+xml")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/rss"
    (root / "config/feeds.py").write_text(f"VERIFIED_RSS = [('Diagnostic', {url!r}, 'tier1', 'agriculture')]\n")
    (root / "config/sources.py").write_text("ALL_SOURCES = []\n")
    env = {k: v for k, v in os.environ.items()
           if not k.endswith("API_KEY") and k not in ("LLM_API_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")}
    env.update(ALP_ROOT=str(root), ALP_MAX_RETRIES="0", ALP_DISABLE_LLM_VERIFY="1",
               ALP_DISABLE_POLISH="1", DRY_RUN="1", ORCHESTRATOR_SKIP_HEALTHCHECK="1")
    try:
        result = subprocess.run(
            [sys.executable, str(root / "main.py"), "--job-type", "daily", "--date", "2026-10-05"],
            cwd=root, env=env, capture_output=True, text=True, timeout=90,
        )
        if interrupt_feed:
            assert result.returncode == 1, result.stdout + result.stderr
            failed = json.loads((root / "state/jobs.json").read_text())["daily_2026-10-05"]
            assert failed["status"] == "failed" and failed["failed_stage"] == "01_source_fetch"
            assert not (root / "state/published_events.json").exists()
            result = subprocess.run(
                [sys.executable, str(root / "main.py"), "--type", "daily", "--date", "2026-10-05"],
                cwd=root, env=env, capture_output=True, text=True, timeout=90)
            recovered = json.loads((root / "state/jobs.json").read_text())["daily_2026-10-05"]
            assert recovered["window"] == failed["window"]
            assert recovered["run_attempts"] == 2
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert result.returncode == 0, result.stdout + result.stderr
    job_id = "daily_2026-10-05"
    state = json.loads((root / "state/jobs.json").read_text())
    assert state[job_id]["status"] == "success"
    for stage in ("raw", "verified", "dedup", "scored", "selected", "content", "mcq"):
        assert (root / f"data/{stage}/{job_id}.json").is_file(), stage
    pdf = root / f"output/{job_id}.pdf"
    qa = json.loads((root / f"logs/qa/{job_id}_qa.json").read_text())
    assert qa["passed"] and qa["file_sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert not (root / "state/published_events.json").exists(), "dry-run must not write a real publication ledger"

    # With the RSS server now OFFLINE, completed daily jobs must be a real no-op.
    health = json.loads((root / f"logs/qa/{job_id}_health.json").read_text())
    assert health["passed"] and state[job_id]["last_success_stage"] == "24_final_health_audit"
    before = (root / "state/jobs.json").read_bytes()
    rerun = subprocess.run([sys.executable, str(root / "main.py"), "--type", "daily", "--date", "2026-10-05"],
                           cwd=root, env=env, capture_output=True, text=True, timeout=90)
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
    assert "already complete with intact checkpoints" in rerun.stdout
    assert (root / "state/jobs.json").read_bytes() == before

    # Both period editions use the verified shared database with ALL network unavailable.
    for kind, edition in [("weekly", "2026-10-04"), ("monthly", "2026-10-14")]:
        run = subprocess.run([sys.executable, str(root / "main.py"), "--type", kind, "--date", edition],
                             cwd=root, env=env, capture_output=True, text=True, timeout=90)
        assert run.returncode == 0, run.stdout + run.stderr
        period_id = f"{kind}_{edition}"
        state = json.loads((root / "state/jobs.json").read_text())
        assert state[period_id]["status"] == "success"
        assert state[period_id]["last_success_stage"] == "24_final_health_audit"
        health = json.loads((root / f"logs/qa/{period_id}_health.json").read_text())
        assert health["passed"] and health["dry_run"]
        verification = subprocess.run([sys.executable, str(ROOT / "scripts/verify_e2e.py"), "--root", str(root),
                                       "--job-type", kind, "--date", edition],
                                      env=env, capture_output=True, text=True, timeout=30)
        assert verification.returncode == 0, verification.stdout + verification.stderr
    assert not (root / "state/published_events.json").exists()

    # Simulate an interrupted process immediately after PDF QA. No RSS is available.
    state = json.loads((root / "state/jobs.json").read_text())
    state[job_id]["status"] = "running"
    state[job_id]["last_success_stage"] = "19_pdf_qa"
    (root / "state/jobs.json").write_text(json.dumps(state))
    raw_before = (root / f"data/raw/{job_id}.json").read_bytes()
    recovery = subprocess.run([sys.executable, str(root / "main.py"), "--type", "daily", "--date", "2026-10-05"],
                              cwd=root, env=env, capture_output=True, text=True, timeout=90)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    assert "resuming after completed stage '19_pdf_qa'" in recovery.stdout
    assert (root / f"data/raw/{job_id}.json").read_bytes() == raw_before
    assert not (root / "state/published_events.json").exists()


@pytest.mark.parametrize("message_id", [None, 0, -1, True, "5"])
def test_live_publish_rejects_invalid_message_ids(tmp_path, monkeypatch, message_id):
    publisher = load_publisher()
    monkeypatch.setattr(publisher, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(publisher, "DRY_RUN", False)
    monkeypatch.setattr(publisher, "call_with_retry", lambda *a, **k: {"message_id": message_id})
    monkeypatch.setattr(publisher, "save_ledger", lambda *a: None)
    pdf = tmp_path / "daily_2026-10-05.pdf"
    pdf.write_bytes(b"unit-test PDF bytes")
    qa = tmp_path / "logs/qa/daily_2026-10-05_qa.json"
    qa.parent.mkdir(parents=True)
    qa.write_text(json.dumps({"passed": True, "job_id": pdf.stem,
                              "file_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()}))
    content = tmp_path / "data/content/daily_2026-10-05.json"
    content.parent.mkdir(parents=True)
    content.write_text(json.dumps({"items": [{"needs_review": False, "verification_passed": True}]}))
    ledger = {"records": {}}
    assert not publisher.publish_pdf(pdf, ledger)
    assert all(record["status"] != "success" for record in ledger["records"].values())
