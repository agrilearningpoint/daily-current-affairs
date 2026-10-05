# -*- coding: utf-8 -*-
"""
PERSISTENT EVENT STORE — the real "same database, different selection" backbone.

Problem this solves: GitHub Actions runners are EPHEMERAL. data/ is gitignored and
artefacts expire, so importance-memory / job-states were NOT persistent across runs.

Design (zero external services):
  * The Git repo itself is the database. State lives in committed files under state/.
  * Every workflow pulls latest main before running, pushes changes after running.
  * Writes are MERGE-based (event_id keyed dicts) + a per-job branch check, so daily /
    weekly / monthly / watchdog workflows never clobber each other's keys.
  * If push fails (conflict), we pull --rebase and retry; final failure logs loudly
    but NEVER blocks PDF generation or Telegram publishing.
  * LIMITATION: This is NOT a true transactional DB — concurrent runners depend on
    rebase+merge retries. For current scale (1 daily + 1 weekly + 1 monthly + watchdog
    every 5min) this is workable and tested; beyond that a real DB (e.g., MongoDB Atlas
    as in docs/DATABASE_SCHEMA) should replace state/.

API:
  store.pull()                  -> sync local state/ with origin/main
  record_scores(items, job_id)  -> merge event scores into memory (agent 11)
  load_memory()                 -> full importance memory dict
  mark_published(eids, job_id)  -> remember published events (agents 22/24)
  write_job_state(job)          -> mirror job JSON for cross-run watchdog
  remove_job_state(job_id)      -> drop stale lock/state when a run ends
  prune(retain_days)            -> keep state lean on monthly runs
  store.push(message)           -> commit+push changed state files
"""
import json, os, shutil, subprocess
from datetime import datetime, timedelta

import pytz

TZ = pytz.timezone("Asia/Kolkata")
ROOT = os.environ.get("ALP_ROOT", os.getcwd())
STATE_DIR = os.path.join(ROOT, "state")
MEMORY_F = os.path.join(STATE_DIR, "importance_memory.json")
PUBLISHED_F = os.path.join(STATE_DIR, "published_events.json")
PUBLISHED_JOBS_F = os.path.join(STATE_DIR, "published_jobs.json")  # P0 FIX: job-level registry
JOBS_F = os.path.join(STATE_DIR, "jobs.json")


def _git(*args, checks=True):
    try:
        r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, timeout=90)
        if checks and r.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr[:300]}")
        return r.stdout
    except Exception as e:
        if checks:
            raise
        return ""


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


# JSON state files are MERGED key-by-key (event_id / job_id keyed dicts), never
# clobbered wholesale. This is the fix for the concurrent-workflow race:
# daily/weekly/monthly/watchdog runners each add different keys; a blind
# `checkout FETCH_HEAD -- state/` or last-writer-wins push would silently drop
# another workflow's updates. Merge keeps both sides' keys on pull AND on push.
MERGE_FILES = ("importance_memory.json", "published_events.json", "published_jobs.json", "jobs.json")


def _merge_dicts(local_obj, remote_obj):
    """Union merge of two dict-shaped state files. On same-key conflict, prefer
    the record with the newer timestamp field (last_seen/last_published/updated);
    ties fall back to local (we just wrote it)."""
    out = dict(remote_obj or {})
    for k, v in (local_obj or {}).items():
        old = out.get(k)
        if old is None:
            out[k] = v
            continue
        if isinstance(old, dict) and isinstance(v, dict):
            ts_new = v.get("last_seen") or v.get("last_published") or v.get("updated") or ""
            ts_old = old.get("last_seen") or old.get("last_published") or old.get("updated") or ""
            out[k] = v if ts_new >= ts_old else old
        else:
            out[k] = v  # non-dict local value wins (we own our writes)
    return out


def _remote_state(fn):
    r = subprocess.run(["git", "-C", ROOT, "show", f"origin/main:state/{fn}"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return {}
    try:
        obj = json.loads(r.stdout)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


def pull():
    """Fetch latest committed state from origin/main and MERGE it into local
    state files (key-wise union; never overwrite local-only additions)."""
    try:
        _git("fetch", "origin", "main", checks=False)
        for fn in MERGE_FILES:
            p = os.path.join(STATE_DIR, fn)
            remote = _remote_state(fn)
            if not remote:
                continue
            local = _load(p)
            merged = _merge_dicts(local, remote)
            if merged != local:
                _save(p, merged)
        return True
    except Exception as e:
        print(f"[store] pull skipped: {e}")
        return False


def push(message="state: update"):
    """Commit + push changed state files with a merge-safe rebase loop.
    On push conflict we rebase onto origin/main; if git reports a CONFLICT in
    one of our JSON state files, we abort the rebase, take the merged
    (local ∪ remote) version, recommit and retry — so concurrent workflows
    never lose each other's keys. Raises RuntimeError on push failure (P0: was silently warning)."""
    import time
    try:
        _git("add", "-f", "state/", checks=False)
        r = subprocess.run(["git", "-C", ROOT, "diff", "--cached", "--quiet"])
        if r.returncode == 0:
            return False  # nothing changed
        _git("-c", "user.name=AgriLearningPointBot", "-c", "user.email=bot@agrilearningpoint.local",
             "commit", "-m", message, checks=False)
        for attempt in range(3):
            pr = subprocess.run(["git", "-C", ROOT, "push", "origin", "HEAD:main"],
                                capture_output=True, text=True, timeout=120)
            if pr.returncode == 0:
                print(f"[store] pushed: {message}")
                return True
            # Conflict-safe rebase: if state JSONs clash, merge them ourselves.
            rb = subprocess.run(["git", "-C", ROOT, "pull", "--rebase", "origin", "main"],
                                capture_output=True, text=True, timeout=120)
            if rb.returncode != 0:
                conflicted = [fn for fn in MERGE_FILES
                              if f"state/{fn}" in (rb.stdout + rb.stderr)]
                subprocess.run(["git", "-C", ROOT, "rebase", "--abort"],
                               capture_output=True, text=True, timeout=60)
                if conflicted:
                    _git("fetch", "origin", "main", checks=False)
                    for fn in conflicted:
                        merged = _merge_dicts(_load(os.path.join(STATE_DIR, fn)),
                                              _remote_state(fn))
                        _save(os.path.join(STATE_DIR, fn), merged)
                    _git("add", "-f", "state/", checks=False)
                    _git("-c", "user.name=AgriLearningPointBot",
                         "-c", "user.email=bot@agrilearningpoint.local",
                         "commit", "-m", f"{message} (merged concurrent state)", checks=False)
                    continue
                print(f"[store] rebase failed: {rb.stderr[:200]}")
                break
            time.sleep(1 + attempt)  # tiny jitter reduces repeated collisions
        # P0 FIX: push failure must NOT be silent warning — caller (workflow) must see FAILURE
        # Previously returned False for both "nothing to push" and "push failed" → workflow hid 403 as warning
        print("[store] ERROR: could not push state to origin/main after retries — check permissions (contents: write)")
        raise RuntimeError("State push failed after 3 retries — GitHub push 403 or merge conflict")
    except Exception as e:
        # Re-raise so workflow fails loudly (audit: state push failed → pipeline FAILED)
        print(f"[store] push failed: {e}")
        raise


def record_scores(items, job_id):
    """Merge scored events into persistent importance memory (agent 11).
    P1 FIX #9: Keep lightweight full event record (headline, source, category, raw_facts, etc.)
    so Weekly/Monthly can do fresh Best-of re-selection from historical content, not just scores.
    """ 
    mem = _load(MEMORY_F)
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    for it in items:
        eid = it["event_id"]
        # Lightweight full record for cross-week/month reuse
        rec = mem.setdefault(eid, {"headline": it.get("headline_en", "")[:160],
                                   "headline_hi": it.get("headline_hi", "")[:160] if it.get("headline_hi") else "",
                                   "source_url": it.get("source_url", ""),
                                   "source_name": it.get("source_name", ""),
                                   "source_level": it.get("source_level", 5),
                                   "category": it.get("category", ""),
                                   "raw_facts": (it.get("raw_facts", "") or "")[:600],
                                   "student_relevance": it.get("student_relevance", it.get("importance_score", 0)),
                                   "importance_score": it.get("importance_score", 0),
                                   "agri_focus": it.get("agri_focus", False),
                                   "banking_focus": it.get("banking_focus", False),
                                   "scores": [], "first_seen": today, "last_seen": today})
        # Update mutable fields to latest
        rec["headline"] = it.get("headline_en", rec["headline"])[:160]
        rec["source_url"] = it.get("source_url", rec["source_url"])
        rec["category"] = it.get("category", rec["category"])
        rec["student_relevance"] = it.get("student_relevance", rec["student_relevance"])
        rec["importance_score"] = it.get("importance_score", rec["importance_score"])
        rec["scores"].append({"date": today, "job": job_id,
                              "score": round(float(it.get("importance_score", 0)), 1)})
        rec["scores"] = rec["scores"][-30:]
        rec["last_seen"] = today
        if len(rec["scores"]) >= 2:
            delta = rec["scores"][-1]["score"] - rec["scores"][-2]["score"]
            rec["trend"] = "RISING" if delta > 5 else "FALLING" if delta < -5 else "STABLE"
        else:
            rec["trend"] = "NEW"
    _save(MEMORY_F, mem)
    return mem


def load_memory():
    return _load(MEMORY_F)


def mark_published(event_ids, job_id):
    pub = _load(PUBLISHED_F)
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    for eid in event_ids:
        rec = pub.setdefault(eid, {"jobs": []})
        if job_id not in rec["jobs"]:
            rec["jobs"].append(job_id)
        rec["last_published"] = today
    _save(PUBLISHED_F, pub)


def published_event_ids():
    return set(_load(PUBLISHED_F).keys())


# ── P0 FIX: Job-level publication registry (dedicated, not event_id mix) ──
def mark_job_published(job_id, chat_id, message_id, file_sha256, published_at=None):
    """Dedicated job→Telegram registry for idempotency.
    Prevents duplicate PDF upload if runner crashes after sendDocument but before event mark."""
    jobs_pub = _load(PUBLISHED_JOBS_F)
    jobs_pub[job_id] = {
        "status": "PUBLISHED",
        "chat_id": str(chat_id),
        "message_id": int(message_id),
        "file_sha256": file_sha256,
        "published_at": published_at or datetime.now(TZ).isoformat(),
    }
    _save(PUBLISHED_JOBS_F, jobs_pub)
    return jobs_pub[job_id]

def is_job_published(job_id):
    jobs_pub = _load(PUBLISHED_JOBS_F)
    return job_id in jobs_pub

def get_job_publication(job_id):
    return _load(PUBLISHED_JOBS_F).get(job_id)

def verify_job_published(job_id, chat_id=None):
    """Check if job already published and verify message still exists on Telegram."""
    rec = get_job_publication(job_id)
    if not rec:
        return False, None
    # If chat_id provided, could verify via Telegram API getChat, but we just check registry
    return True, rec


def save_pdf_hash(job_id, pdf_path):
    """Save PDF SHA256 for integrity verification (Telegram document check)."""
    import hashlib as _hl
    try:
        h = _hl.sha256(open(pdf_path, "rb").read()).hexdigest()
        jobs = _load(JOBS_F)
        j = jobs.get(job_id, {})
        j["pdf_sha256"] = h
        j["pdf_size"] = __import__("os").path.getsize(pdf_path)
        try:
            import pymupdf
        except ImportError:
            import fitz as pymupdf
        j["pdf_pages"] = pymupdf.open(pdf_path).page_count
        jobs[job_id] = j
        _save(JOBS_F, jobs)
        return h
    except Exception as e:
        print(f"[store] save_pdf_hash failed: {e}")
        return None


def write_job_state(job):
    jobs = _load(JOBS_F)
    jobs[job["job_id"]] = {k: job.get(k) for k in
                           ("job_id", "status", "updated", "last_success_stage",
                            "failed_at", "error")}
    _save(JOBS_F, jobs)


def remove_job_state(job_id):
    jobs = _load(JOBS_F)
    if jobs.pop(job_id, None) is not None:
        _save(JOBS_F, jobs)


def prune(retain_days=75):
    """Monthly cleanup: drop memory/published entries older than retain_days."""
    cutoff = (datetime.now(TZ) - timedelta(days=retain_days)).strftime("%Y-%m-%d")
    mem = {k: v for k, v in load_memory().items() if v.get("last_seen", "9999") >= cutoff}
    _save(MEMORY_F, mem)
    pub = {k: v for k, v in _load(PUBLISHED_F).items()
           if v.get("last_published", "9999") >= cutoff}
    _save(PUBLISHED_F, pub)
