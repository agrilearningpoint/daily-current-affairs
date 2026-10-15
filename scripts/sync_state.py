#!/usr/bin/env python3
"""Merge-safe state-only git synchronization, invoked explicitly by Actions.

No force pushes, implicit branch changes, credential handling, or git side effects
in the pipeline library. Concurrent upstream state is unioned before committing.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

FILES = ["state/jobs.json", "state/importance_memory.json", "state/published_events.json",
         "state/published_jobs.json", "state/pin_verification.json", "state/source_health.json",
         "recovery_plan.json"]


def timestamp(entry):
    values = []
    if isinstance(entry, dict):
        for field in ("updated_at", "last_seen", "published_at", "verified_at", "checked_at", "updated", "generated_at", "last_success_at", "last_failure_at", "at"):
            try:
                value = datetime.fromisoformat(str(entry.get(field, "")).replace("Z", "+00:00"))
                values.append(value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value)
            except ValueError:
                pass
    return max(values, default=datetime.min.replace(tzinfo=timezone.utc))


def union(local, remote):
    result = dict(remote)
    for key, value in local.items():
        if key not in result or timestamp(value) >= timestamp(result[key]):
            result[key] = value
    return result


def merge_document(path, local, remote):
    if path == "recovery_plan.json" and isinstance(local, (dict, list)) and isinstance(remote, (dict, list)):
        return local if timestamp(local) >= timestamp(remote) else remote
    if not isinstance(local, dict) or not isinstance(remote, dict):
        raise ValueError(f"cannot merge non-object state in {path}")
    if path == "state/jobs.json":
        a, b = local.get("jobs", local), remote.get("jobs", remote)
        if not isinstance(a, dict) or not isinstance(b, dict):
            raise ValueError("invalid jobs map")
        return union(a, b)
    if "records" in local or "records" in remote:
        return {"version": 1, "records": union(local.get("records", {k: v for k, v in local.items() if k != "version"}), remote.get("records", {k: v for k, v in remote.items() if k != "version"}))}
    if path == "state/source_health.json":
        return {"version": 1, "sources": union(local.get("sources", {}), remote.get("sources", {}))}
    if path == "state/importance_memory.json":
        return union(local.get("events", local), remote.get("events", remote))
    if path == "recovery_plan.json":
        return local if timestamp(local) >= timestamp(remote) else remote
    return union(local, remote)


def git(*args, check=True):
    return subprocess.run(["git", *args], text=True, capture_output=True, check=check, timeout=90)


def sync(branch, message):
    if git("branch", "--show-current").stdout.strip() != branch:
        raise ValueError("refusing to synchronize a different checked-out branch")
    # Do not accidentally commit or discard unrelated user changes.
    changed = git("diff", "--name-only").stdout.splitlines() + git("diff", "--cached", "--name-only").stdout.splitlines()
    if any(path not in FILES for path in changed):
        raise ValueError("non-state modifications present; refusing git synchronization")
    local = {path: json.loads(Path(path).read_text(encoding="utf-8")) for path in FILES if Path(path).is_file()}
    if not local:
        return
    for attempt in range(3):
        try:
            git("fetch", "origin", branch)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if attempt == 2:
                raise RuntimeError("fetch failed after three attempts; local state preserved")
            time.sleep(2 ** attempt)
            continue
        ref = f"origin/{branch}"
        remote = {}
        for path in FILES:
            content = git("show", f"{ref}:{path}", check=False)
            if content.returncode == 0:
                remote[path] = json.loads(content.stdout)
        for path, data in remote.items():
            local.setdefault(path, data)
        # Commit generated files before merging so git never discards dirty state.
        for path, data in local.items():
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        git("add", "-f", "--", *local)
        if git("diff", "--cached", "--quiet", check=False).returncode != 0:
            git("commit", "-m", f"{message} [skip ci]")
        merged = git("merge", "--no-commit", "--no-ff", ref, check=False)
        if merged.returncode:
            conflicts = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
            if not conflicts or any(path not in FILES for path in conflicts):
                git("merge", "--abort", check=False)
                raise RuntimeError("upstream merge failed outside allowed state files")
        for path, data in local.items():
            local[path] = merge_document(path, data, remote.get(path, {}))
            Path(path).write_text(json.dumps(local[path], ensure_ascii=False, indent=2), encoding="utf-8")
        git("add", "-f", "--", *local)
        pending_merge = git("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0
        if pending_merge or git("diff", "--cached", "--quiet", check=False).returncode != 0:
            git("commit", "-m", f"{message}: merge state [skip ci]")
        pushed = git("push", "origin", branch, check=False)
        if pushed.returncode == 0:
            print(f"State synchronized on attempt {attempt + 1}")
            return
        if attempt < 2:
            time.sleep(2 ** attempt)
    raise RuntimeError("state push failed after three attempts; artifacts remain for recovery")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--message", default="state: pipeline checkpoint")
    args = parser.parse_args()
    sync(args.branch, args.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
