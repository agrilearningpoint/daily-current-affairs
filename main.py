# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — MASTER ORCHESTRATOR (production)
Runs the 24-agent pipeline with: atomic job-lock, full state machine,
exponential-backoff retries (2s/4s/8s), resume-from-last-stage, watchdog alerts.
SECURITY: no hardcoded tokens — TELEGRAM_BOT_TOKEN only from env (GitHub Secrets).

Usage: python main.py --type daily --date 2026-10-05
       python main.py --watchdog          # monitor running/stalled jobs
"""

import argparse, json, os, sys, time, logging, traceback
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.workflow import WORKFLOW_ORDER, MASTER_RULE
from pipeline.state import (ensure_dirs, load_job, save_job, read_json, write_json_atomic,
                            job_path, JobLock, TZ, now_iso)
from pipeline.telegram_api import alert_admin
from pipeline import store


def load_agent(agent_id):
    module = __import__(f'agents.{agent_id}', fromlist=['Agent'])
    return module.Agent


def setup_logging(job_id):
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(level=logging.INFO, datefmt="%H:%M:%S",
                        format='[%(asctime)s] %(message)s',
                        handlers=[logging.FileHandler(f"logs/{job_id}.log"), logging.StreamHandler()])


def run_pipeline(job_type, job_date, force=False):
    ensure_dirs()
    # PERSISTENT EVENT DB: pull Git-committed memory/published-log before starting
    try:
        store.pull()
    except Exception as e:
        logging.warning(f"persistent store pull failed (continuing local-only): {e}")
    job_id = f"{job_type}_{job_date}"
    setup_logging(job_id)
    logging.info(f"=== START PIPELINE {job_id} ===")
    logging.info(f"MASTER RULE: {MASTER_RULE}")

    # ---- ATOMIC LOCK: prevents duplicate/racing runs of the same job ----
    # P0 FIX: Never return SUCCESS when locked — GitHub would mark workflow green while pipeline never ran
    lock = JobLock(job_id)
    if not lock.acquire():
        logging.error(f"Job {job_id} already RUNNING elsewhere (lock held) — refusing silent success")
        print(f"::error::Job {job_id} is already locked — another runner is active")
        raise SystemExit(2)
    try:
        job = load_job(job_id, job_type, job_date)
        if job.get("status") == "COMPLETE" and not force:
            logging.info(f"Job {job_id} already COMPLETE — skipping duplicate")
            return "SKIPPED_DONE"

        context = {"job_id": job_id, "job_type": job_type, "job_date": job_date,
                   "tz": "Asia/Kolkata", "window": f"{job_date} 06:00 IST",
                   "date_display": datetime.strptime(job_date, "%Y-%m-%d").strftime("%d %B %Y")}

        start_idx = 0
        last = job.get("last_success_stage")
        # P0 FIX: FAILED_FINAL must also resume from last_success_stage (not from 0)
        # Watchdog recovery: 03✅ 04✅ 05❌ → resume at 05, not 03
        if last and last in WORKFLOW_ORDER:
            if job.get("status") in ("FAILED_FINAL", "QA_REJECTED", "FAILED", "RETRYING"):
                # Resume after last successful stage, even for failed jobs
                if WORKFLOW_ORDER.index(last) + 1 < len(WORKFLOW_ORDER):
                    start_idx = WORKFLOW_ORDER.index(last) + 1
                    logging.info(f"RESUME after {job.get('status')}: from after {last} -> {WORKFLOW_ORDER[start_idx]}")
                else:
                    logging.info(f"RESUME: {last} was last stage — job already at end")
            elif job.get("status") != "COMPLETE":
                start_idx = WORKFLOW_ORDER.index(last) + 1
                logging.info(f"RESUME: from after {last} -> {WORKFLOW_ORDER[start_idx]}")

        job = load_job(job_id, job_type, job_date)
        # If QA already approved the PDF, restore that gate state so a resumed
        # run doesn't wedge Agent 22 ("publish blocked: state=RECOVERED").
        if job.get("last_success_stage") == "19_pdf_qa":
            save_job(job, state="QA_APPROVED")
        elif start_idx > 0:
            save_job(job, state="RECOVERED")   # mid-pipeline resume: keep artefacts
        else:
            save_job(job, state="COLLECTING")

        # Per-agent post-success states — STATE OWNERSHIP LIVES HERE ONLY.
        # Agents write artefacts + context; the orchestrator alone transitions
        # the job state machine (single writer, no split ownership).
        # P0 FIX: Agent 19 must NOT call save_job(QA_REJECTED) directly — orchestrator does.
        STAGE_STATE = {"03_news_collection": "COLLECTED", "04_fact_verification": "VERIFIED",
                       "05_deduplication": "DEDUPLICATED", "06_news_importance": "SCORED",
                       "10_final_news_selection": "SELECTED", "12_content_editor": "CONTENT_READY",
                       "17_mcq_validator": "MCQ_VALIDATED", "18_pdf_design": "PDF_GENERATED",
                       "19_pdf_qa": "QA_APPROVED"}

        for agent_id in WORKFLOW_ORDER[start_idx:]:
            # P0 FIX: Granular RUNNING tracking so watchdog can see exactly which stage is active
            # Previously state stayed at COLLECTED while 04 was running and crash left stale state
            try:
                job = load_job(job_id, job_type, job_date)
                save_job(job, state="RUNNING", stage=agent_id, current_stage=agent_id, heartbeat_at=now_iso(), started_at=now_iso())
                store.write_job_state(job)
            except Exception as e:
                logging.warning(f"RUNNING state update failed for {agent_id}: {e}")
            TOTAL_ATTEMPTS, backoffs = 3, [2, 4, 8]  # 3 total tries = 1 initial + up to 2 retries
            last_err = None
            for attempt in range(TOTAL_ATTEMPTS):
                try:
                    logging.info(f"--> Running {agent_id} (attempt {attempt+1}/{TOTAL_ATTEMPTS})")
                    Agent = load_agent(agent_id)
                    agent = Agent(job_id, job_type, context)
                    context = agent.run()
                    # ---- QUALITY GATE: agent must self-report success ----
                    if context.get("stage_failed"):
                        raise RuntimeError(f"{agent_id} reported failure: {context['stage_failed']}")
                    job = load_job(job_id, job_type, job_date)
                    summary = {k: v for k, v in context.items()
                               if isinstance(v, (int, float, str, bool))}
                    extra = {}
                    if agent_id == "22_telegram_publisher" and context.get("telegram_message_id"):
                        extra["telegram_message_id"] = context["telegram_message_id"]
                    if agent_id == "24_final_health_audit":
                        extra["watchdog"] = "healthy"
                    save_job(job, state=STAGE_STATE.get(agent_id), stage=agent_id,
                             context_summary=summary, **extra)
                    store.write_job_state(job)   # cross-run visibility for watchdog
                    break
                except Exception as e:
                    last_err = e
                    logging.error(f"Agent {agent_id} failed (attempt {attempt+1}/{TOTAL_ATTEMPTS}): {e}")
                    traceback.print_exc()
                    if attempt < TOTAL_ATTEMPTS - 1:
                        job = load_job(job_id, job_type, job_date)
                        save_job(job, state="RETRYING", error=str(e)[:500], retry=attempt + 1)
                        time.sleep(backoffs[attempt])
            else:
                job = load_job(job_id, job_type, job_date)
                # P0 FIX: QA failures become QA_REJECTED (blocks publish), others FAILED_FINAL
                if agent_id == "19_pdf_qa" or "QA_REJECTED" in str(last_err):
                    save_job(job, state="QA_REJECTED", error=str(last_err)[:500], failed_checks=str(last_err)[:500], failed_at=agent_id)
                    store.write_job_state(job)
                    try:
                        store.push(f"state: {job_id} QA_REJECTED at {agent_id}")
                    except Exception:
                        pass
                    alert_admin(f"🚨 PDF QA REJECTED: {job_id} at {agent_id} — {str(last_err)[:400]}")
                else:
                    save_job(job, state="FAILED_FINAL", error=str(last_err)[:500], failed_at=agent_id)
                    store.write_job_state(job)      # persist failure for cross-run watchdog
                    try:
                        store.push(f"state: {job_id} FAILED_FINAL at {agent_id}")
                    except Exception:
                        pass
                    alert_admin(f"🚨 WATCHDOG ALERT: {job_id} FAILED at {agent_id} — {str(last_err)[:400]}")
                raise SystemExit(f"Pipeline failed at {agent_id}: {last_err}")

        job = load_job(job_id, job_type, job_date)
        save_job(job, state="COMPLETE")
        store.remove_job_state(job_id)          # clean cross-run watchdog entry
        # P0 FIX: state push failure must FAIL workflow (not warning) — otherwise next runner loses state
        # GitHub requires contents: write — 403 previously hid as warning, now fails loudly
        try:
            if job_type == "monthly":
                store.prune(retain_days=75)     # keep event DB lean each month
            pushed = store.push(f"state: {job_id} complete ({job.get('last_success_stage','')})")
            if not pushed:
                logging.info(f"State already up-to-date for {job_id} — no push needed")
        except Exception as e:
            logging.error(f"persistent state push failed for {job_id}: {e} — failing workflow to prevent state loss")
            print(f"::error::State push failed for {job_id} — check GitHub permissions (contents: write) — {e}")
            raise SystemExit(1)
        logging.info(f"=== PIPELINE {job_id} COMPLETE ===")
        return "COMPLETE"
    finally:
        lock.release()


def watchdog_check(max_age_min=90):
    """Scan LOCAL data/jobs AND PERSISTENT committed state/jobs.json for stalled/failed
    jobs → alert admin + write recovery_plan.json consumed by the workflow retry step."""
    ensure_dirs(); setup_logging("watchdog")
    problems, recoveries = [], []
    try:
        store.pull()          # get latest committed job states from other runners
    except Exception as e:
        logging.warning(f"watchdog store pull failed: {e}")
    seen = {}
    jd = "data/jobs"
    if os.path.isdir(jd):
        for fn in sorted(os.listdir(jd)):
            if fn.endswith(".json"):
                jj = read_json(os.path.join(jd, fn)) or {}
                if jj.get("job_id"):
                    seen[jj["job_id"]] = jj
    for jid, jj in (store._load(store.JOBS_F) or {}).items():   # persistent mirror if fresher
        cur = seen.get(jid)
        if not cur or (jj.get("updated", "") >= cur.get("updated", "")):
            seen[jid] = jj
    for jid in sorted(seen):
        j = seen[jid]
        st = j.get("status")
        if st in ("RUNNING", "RETRYING", "COLLECTING", "VERIFYING", "PUBLISHED"):
            upd = j.get("updated")
            if upd:
                try:
                    age = (datetime.now(TZ) - datetime.fromisoformat(upd)).total_seconds() / 60
                except ValueError:
                    age = 0
                if age > max_age_min:
                    problems.append(f"⏰ STALLED {jid} state={st} age={age:.0f}min stage={j.get('last_success_stage')}")
                    recoveries.append(jid)
        elif st == "FAILED_FINAL":
            problems.append(f"💥 FAILED_FINAL {jid} at {j.get('failed_at')}: {str(j.get('error',''))[:120]}")
            recoveries.append(jid)
    if recoveries:
        with open("recovery_plan.json", "w", encoding="utf-8") as f:
            json.dump(recoveries, f)
    if problems:
        alert_admin("🐕 WATCHDOG:\n" + "\n".join(problems))
        print("\n".join(problems))
        return 1
    logging.info("Watchdog: all jobs healthy")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["daily", "weekly", "monthly"])
    parser.add_argument("--date", help="YYYY-MM-DD in Asia/Kolkata")
    parser.add_argument("--force", action="store_true", help="rerun even if COMPLETE")
    parser.add_argument("--watchdog", action="store_true", help="monitor mode")
    args = parser.parse_args()
    if args.watchdog:
        sys.exit(watchdog_check())
    if not (args.type and args.date):
        parser.error("--type and --date are required for a pipeline run")
    # P0 FIX: Propagate pipeline exit code so GitHub Actions correctly marks SUCCESS/FAILURE
    # Previously SKIPPED_LOCKED returned 0 (SUCCESS) even though pipeline never ran — now raises SystemExit(2)
    result = run_pipeline(args.type, args.date, force=args.force)
    if isinstance(result, str):
        if result == "SKIPPED_DONE":
            logging.info(f"Pipeline already COMPLETE — idempotent success")
            sys.exit(0)
        elif result.startswith("SKIPPED"):
            print(f"::error::Pipeline skipped: {result}")
            sys.exit(2)
    sys.exit(0)
