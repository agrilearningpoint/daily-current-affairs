"""Exercise non-dry publication/pin/audit paths without any real network effects.

Pre-QA artifacts are seeded fixtures. The separate daily integration tests run
actual content/MCQ/PDF/QA subprocesses. Here every HTTP call is intercepted.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
import requests

import main
from pipeline.checkpoints import STAGE_FILES, capture
from pipeline.persistence import write_json_atomic
from pipeline.publication import publication_issues

ROOT = Path(__file__).resolve().parents[1]
JOB = "daily_2026-10-05"
CHAT = "-100000777"
MESSAGE = 321


def load_agent(number):
    path = next((ROOT / "agents").glob(f"{number}_*.py"))
    spec = importlib.util.spec_from_file_location(f"publication_test_{number}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def publication_tail(tmp_path, monkeypatch):
    publisher, pin, health = (load_agent(number) for number in ("22", "23", "24"))
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    for key, value in {"DRY_RUN": "0", "ALP_ROOT": str(tmp_path), "ALP_JOB_ID": JOB,
                       "ALP_JOB_TYPE": "daily", "ALP_JOB_DATE": "2026-10-05",
                       "ALP_OUTPUT_PREFIX": JOB, "TELEGRAM_CHAT_ID": CHAT}.items():
        monkeypatch.setenv(key, value)
    for agent in (publisher, pin):
        monkeypatch.setattr(agent, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(agent, "DRY_RUN", False)
        monkeypatch.setattr(agent, "TELEGRAM_CHAT_ID", CHAT)
        monkeypatch.setattr(agent, "TELEGRAM_BOT_TOKEN", "diagnostic-token-not-a-credential")
    monkeypatch.setattr(publisher, "LEDGER_FILE", tmp_path / "state/published_events.json")
    monkeypatch.setattr(pin, "PUBLISHED_LEDGER", publisher.LEDGER_FILE)
    monkeypatch.setattr(pin, "PIN_LEDGER", tmp_path / "state/pin_verification.json")
    monkeypatch.setattr(pin, "PIN_NOTIFY", False)
    pdf = tmp_path / f"output/{JOB}.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\nSeeded publication-tail fixture, not real news\n%%EOF")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    artifacts = {}
    for stage, _, _ in main.DAILY_STAGES:
        template = STAGE_FILES.get(stage)
        if template:
            path = tmp_path / template.format(job=JOB)
            if stage == "19_pdf_qa":
                write_json_atomic(path, {"passed": True, "job_id": JOB, "file_sha256": digest})
            elif stage != "18_pdf_design":
                write_json_atomic(path, {"items": [{"needs_review": False, "verification_passed": True}]})
            artifacts = capture(tmp_path, JOB, stage, artifacts)
        if stage == "19_pdf_qa":
            break
    write_json_atomic(main.JOBS_STATE_PATH, {JOB: {"status": "running", "dry_run": False,
                      "last_success_stage": "19_pdf_qa", "artifacts": artifacts}})
    remote = {"pinned": None, "calls": [], "pin_error": None, "send_timeout": False}

    class Response:
        headers = {}

        def __init__(self, body, status=200):
            self.body, self.status_code = body, status

        def json(self):
            return self.body

    def fake_post(url, **kwargs):
        # Never delegate to requests: an unrecognized endpoint fails the test.
        method = url.rsplit("/", 1)[-1]
        assert url.startswith("https://api.telegram.org/botdiagnostic-token-not-a-credential/")
        remote["calls"].append(method)
        if method == "sendDocument":
            assert kwargs["data"]["chat_id"] == CHAT
            if remote["send_timeout"]:
                raise requests.ReadTimeout("diagnostic accepted-send response was lost")
            return Response({"ok": True, "result": {"message_id": MESSAGE}})
        if method == "getChat":
            result = {} if remote["pinned"] is None else {"pinned_message": {"message_id": remote["pinned"]}}
            return Response({"ok": True, "result": result})
        if method == "pinChatMessage":
            assert kwargs["json"]["message_id"] == MESSAGE
            if remote["pin_error"] == "permissions":
                return Response({"ok": False, "description": "not enough rights", "error_code": 403}, 403)
            remote["pinned"] = MESSAGE
            if remote["pin_error"] == "lost_response":
                raise requests.ReadTimeout("diagnostic pin acknowledgement lost")
            return Response({"ok": True, "result": True})
        pytest.fail(f"unexpected Telegram method: {method}")

    monkeypatch.setattr(requests, "post", fake_post)
    # Guard other HTTP entry points too, even though no stage should use them.
    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail("unexpected GET"))
    agents = {"22_telegram_publisher": publisher, "23_telegram_pin_verifier": pin,
              "24_final_health_audit": health}

    def run_stage(name, script, critical, extra_env):
        assert name in agents, f"re-entered a pre-QA stage: {name}"
        with monkeypatch.context() as context:
            for key, value in extra_env.items():
                context.setenv(key, value)
            code = agents[name].main()
        return code == 0, f"fixture HTTP stage returned {code}"

    monkeypatch.setattr(main, "run_stage", run_stage)
    return publisher, pin, health, remote, digest, tmp_path


@pytest.mark.parametrize("pin_error", [None, "lost_response", "permissions"])
def test_non_dry_publish_pin_audit_contract(publication_tail, pin_error):
    publisher, pin, _, remote, digest, root = publication_tail
    remote["pin_error"] = pin_error
    code = main.execute_job("daily", "2026-10-05")
    if pin_error == "permissions":
        assert code == 1
        assert main.load_jobs_state(strict=True)[JOB]["failed_stage"] == "23_telegram_pin_verifier"
        assert not (root / f"logs/qa/{JOB}_health.json").exists()
        remote["pin_error"] = None
        assert main.execute_job("daily", "2026-10-05") == 0
    else:
        assert code == 0
    assert remote["calls"].count("sendDocument") == 1
    assert publication_issues(root, JOB, digest, CHAT) == []
    assert not (root / "state/published_jobs.json").exists(), "obsolete ledger must not be needed"
    report = json.loads((root / f"logs/qa/{JOB}_health.json").read_text())
    assert report["passed"] and report["dry_run"] is False
    before = list(remote["calls"])
    assert main.execute_job("daily", "2026-10-05") == 0
    assert remote["calls"] == before
    # A cached verified receipt must not mask someone removing the actual pin.
    remote["pin_error"], remote["pinned"] = None, None
    assert pin.main() == 0
    assert remote["pinned"] == MESSAGE
    assert remote["calls"].count("sendDocument") == 1


def test_ambiguous_send_is_not_retried_or_automatically_recovered(publication_tail):
    publisher, _, _, remote, digest, root = publication_tail
    remote["send_timeout"] = True
    assert main.execute_job("daily", "2026-10-05") == 1
    assert remote["calls"] == ["sendDocument"]
    ledger = publisher.load_ledger()
    key, record = next(iter(ledger["records"].items()))
    assert record["status"] == "uncertain"
    assert main.execute_job("daily", "2026-10-05") == 1
    assert remote["calls"] == ["sendDocument"]
    assert main.watchdog() == 2
    plan = json.loads((root / "recovery_plan.json").read_text())
    assert plan["actions"] == [] and plan["manual_attention"][0]["job_id"] == JOB
    # Simulate an operator reconciling an accepted message, NOT an automated resend.
    ledger["records"][key].update(status="success", message_id=MESSAGE)
    publisher.save_ledger(ledger)
    assert main.execute_job("daily", "2026-10-05") == 0
    assert remote["calls"].count("sendDocument") == 1
    assert publication_issues(root, JOB, digest, CHAT) == []


@pytest.mark.parametrize("mutation", ["old_pdf", "dry_run", "wrong_chat", "wrong_message", "no_pin", "corrupt"])
def test_final_audit_rejects_stale_or_mismatched_receipts(publication_tail, mutation):
    publisher, pin, health, _, _, root = publication_tail
    assert main.execute_job("daily", "2026-10-05") == 0
    ledger = publisher.load_ledger()
    record = next(iter(ledger["records"].values()))
    if mutation == "old_pdf":
        record["file_sha256"] = "0" * 64
    elif mutation == "dry_run":
        record["dry_run"] = True
    elif mutation == "wrong_chat":
        record["chat_id"] = "another-chat"
    publisher.save_ledger(ledger)
    pins = json.loads(pin.PIN_LEDGER.read_text())
    if mutation == "wrong_message":
        next(iter(pins["records"].values()))["message_id"] = MESSAGE + 1
    elif mutation == "no_pin":
        pins["records"] = {}
    write_json_atomic(pin.PIN_LEDGER, pins)
    if mutation == "corrupt":
        publisher.LEDGER_FILE.write_text("{broken")
    # Re-enter the audit from its legitimate pre-audit checkpoint.
    state = main.load_jobs_state(strict=True)
    state[JOB]["last_success_stage"] = "23_telegram_pin_verifier"
    state[JOB]["artifacts"].pop(f"logs/qa/{JOB}_health.json", None)
    main.save_jobs_state(state)
    assert health.main() == 1
    assert not json.loads((root / f"logs/qa/{JOB}_health.json").read_text())["passed"]


@pytest.mark.parametrize("text", ["{broken", "[null]", '{"records": []}', '{"records": {"bad": null}}'])
def test_corrupt_publication_ledger_never_becomes_an_empty_retry(publication_tail, text):
    publisher, _, _, remote, _, _ = publication_tail
    publisher.LEDGER_FILE.write_text(text)
    with pytest.raises(ValueError):
        publisher.load_ledger()
    assert publisher.LEDGER_FILE.read_text() == text
    assert remote["calls"] == []


def test_legacy_publication_ledger_preserves_history_and_blocks_duplicate(publication_tail):
    publisher, _, _, remote, _, root = publication_tail
    legacy = {"0907dd4d50b4e04b": {"jobs": [JOB], "last_published": "2026-10-05"}}
    publisher.LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    publisher.LEDGER_FILE.write_text(json.dumps(legacy))

    ledger = publisher.load_ledger()
    assert ledger["records"] == {}
    assert ledger["legacy_history"] == legacy
    assert not publisher.publish_pdf(root / f"output/{JOB}.pdf", ledger)
    assert remote["calls"] == []


def test_legacy_publication_history_allows_an_unpublished_job(publication_tail):
    publisher, _, _, remote, digest, root = publication_tail
    legacy = {"0907dd4d50b4e04b": {"jobs": ["daily_2026-10-04"],
                                  "last_published": "2026-10-04"}}
    publisher.LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    publisher.LEDGER_FILE.write_text(json.dumps(legacy))

    assert main.execute_job("daily", "2026-10-05") == 0
    ledger = publisher.load_ledger()
    assert ledger["legacy_history"] == legacy
    assert remote["calls"].count("sendDocument") == 1
    assert publication_issues(root, JOB, digest, CHAT) == []


def test_pin_refuses_a_foreign_chat(publication_tail):
    _, pin, _, remote, _, _ = publication_tail
    assert not pin.process_verification({"job_id": JOB, "chat_id": "foreign", "message_id": MESSAGE})
    assert remote["calls"] == []


def test_pre_publish_gate_rejects_changed_source_evidence(publication_tail):
    publisher, _, _, remote, _, root = publication_tail
    (root / f"data/raw/{JOB}.json").write_text('{"items": ["changed after QA"]}')
    assert publisher.main() == 1
    assert remote["calls"] == []
    assert not publisher.LEDGER_FILE.exists()


def test_completed_job_with_lost_publication_evidence_is_not_replayed(publication_tail):
    publisher, _, _, remote, _, _ = publication_tail
    assert main.execute_job("daily", "2026-10-05") == 0
    publisher.LEDGER_FILE.unlink()
    before = list(remote["calls"])
    assert main.execute_job("daily", "2026-10-05") == 1
    assert main.load_jobs_state(strict=True)[JOB]["recovery_blocked"]
    assert main.execute_job("daily", "2026-10-05") == 1
    assert main.watchdog() == 2
    assert remote["calls"] == before


def test_completed_edition_with_missing_pdf_fails_closed(tmp_path, monkeypatch):
    """A complete edition whose PDF is gone must fail closed, not crash on read.

    The guard is only reached when resume_after() still reports the edition
    complete (no recorded PDF artifact to rewind to), so it is exercised here
    directly rather than through the publication_tail fixture.
    """
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    monkeypatch.setenv("DRY_RUN", "0")
    names = [name for name, _, _ in main.DAILY_STAGES]
    write_json_atomic(main.JOBS_STATE_PATH, {JOB: {
        "status": "success", "dry_run": False,
        "last_success_stage": names[-1], "artifacts": {}}})
    monkeypatch.setattr(main, "resume_after", lambda *a, **k: names[-1])

    assert main.execute_job("daily", "2026-10-05") == 1
    state = main.load_jobs_state(strict=True)[JOB]
    assert state["status"] == "failed"
    assert state["recovery_blocked"]


def test_revision_of_already_published_edition_requires_reconciliation(publication_tail):
    publisher, _, _, remote, _, root = publication_tail
    assert main.execute_job("daily", "2026-10-05") == 0
    pdf = root / f"output/{JOB}.pdf"
    pdf.write_bytes(pdf.read_bytes() + b"\nchanged revision")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    write_json_atomic(root / f"logs/qa/{JOB}_qa.json", {"passed": True, "job_id": JOB, "file_sha256": digest})
    assert not publisher.publish_pdf(pdf, publisher.load_ledger())
    assert remote["calls"].count("sendDocument") == 1
    assert any(record["status"] == "blocked_revision" for record in publisher.load_ledger()["records"].values())


def test_killed_orchestrator_releases_lock_and_resumes_tail(publication_tail):
    """Kill the actual orchestrator + stage process group, then resume offline."""
    import os
    import shutil
    import signal
    import subprocess
    import sys
    import time

    _, _, _, _, _, root = publication_tail
    for directory in ("agents", "pipeline", "config", "src", "assets"):
        shutil.copytree(ROOT / directory, root / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "images"))
    shutil.copy2(ROOT / "main.py", root / "main.py")
    state = main.load_jobs_state(strict=True)
    state[JOB]["dry_run"] = True
    main.save_jobs_state(state)
    paused = root / "logs/paused-publication"
    paused.parent.mkdir(exist_ok=True)
    stage = root / "agents/22_telegram_publisher.py"
    stage.write_text("from pathlib import Path\nimport time\nPath('logs/paused-publication').write_text('ready')\ntime.sleep(60)\n")
    env = {key: value for key, value in os.environ.items()
           if not key.endswith(("_API_KEY", "_TOKEN")) and key not in {"LLM_API_URL", "TELEGRAM_CHAT_ID"}}
    env.update(DRY_RUN="1", ALP_ROOT=str(root), ALP_MAX_RETRIES="0", ALP_DISABLE_POLISH="1",
               ALP_DISABLE_LLM_VERIFY="1", ORCHESTRATOR_SKIP_HEALTHCHECK="1")
    command = [sys.executable, str(root / "main.py"), "--type", "daily", "--date", "2026-10-05"]
    with (root / "logs/killed-orchestrator.log").open("w") as log:
        process = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            for _ in range(100):
                if paused.exists() or process.poll() is not None:
                    break
                time.sleep(0.05)
            assert paused.exists(), (root / "logs/killed-orchestrator.log").read_text()
            if hasattr(os, "killpg"):
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                if hasattr(os, "killpg"):
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait(timeout=5)
    interrupted = main.load_jobs_state(strict=True)[JOB]
    assert interrupted["status"] == "running" and interrupted["last_success_stage"] == "19_pdf_qa"
    shutil.copy2(ROOT / "agents/22_telegram_publisher.py", stage)
    resumed = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=30)
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert "resuming after completed stage '19_pdf_qa'" in resumed.stdout
    complete = main.load_jobs_state(strict=True)[JOB]
    assert complete["status"] == "success" and complete["run_attempts"] == 2
    assert complete["window"] == interrupted["window"]


def test_confirmed_rate_limit_is_retryable_not_an_uncertain_send(publication_tail, monkeypatch):
    publisher, _, _, remote, _, _ = publication_tail
    original = publisher.call_with_retry

    def rate_limited(*args, **kwargs):
        raise publisher.TelegramRateLimit(1)

    monkeypatch.setattr(publisher, "call_with_retry", rate_limited)
    assert publisher.main() == 1
    assert remote["calls"] == []
    assert next(iter(publisher.load_ledger()["records"].values()))["status"] == "failed"
    monkeypatch.setattr(publisher, "call_with_retry", original)
    assert main.execute_job("daily", "2026-10-05") == 0
    assert remote["calls"].count("sendDocument") == 1


def test_explicit_revision_approval_allows_changed_pdf(publication_tail, monkeypatch):
    publisher, _, _, remote, _, root = publication_tail
    assert main.execute_job("daily", "2026-10-05") == 0
    pdf = root / f"output/{JOB}.pdf"
    pdf.write_bytes(pdf.read_bytes() + b"\noperator-approved correction")
    write_json_atomic(root / f"logs/qa/{JOB}_qa.json", {"passed": True, "job_id": JOB,
                       "file_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()})
    state = main.load_jobs_state(strict=True)
    state[JOB]["status"], state[JOB]["last_success_stage"] = "running", "19_pdf_qa"
    for stage in ("18_pdf_design", "19_pdf_qa"):
        state[JOB]["artifacts"] = capture(root, JOB, stage, state[JOB]["artifacts"])
    main.save_jobs_state(state)
    assert not publisher.publish_pdf(pdf, publisher.load_ledger())
    monkeypatch.setenv("ALP_ALLOW_EDITION_REVISION", "1")
    assert publisher.publish_pdf(pdf, publisher.load_ledger())
    assert remote["calls"].count("sendDocument") == 2
    assert len([r for r in publisher.load_ledger()["records"].values() if r["status"] == "success"]) == 2


def test_revision_approval_never_bypasses_an_uncertain_send(publication_tail, monkeypatch):
    _, _, _, remote, _, _ = publication_tail
    remote["send_timeout"] = True
    assert main.execute_job("daily", "2026-10-05") == 1
    monkeypatch.setenv("ALP_ALLOW_EDITION_REVISION", "1")
    assert main.execute_job("daily", "2026-10-05") == 1
    assert remote["calls"] == ["sendDocument"]
