"""Final fail-closed audit of this edition's evidence and publication state."""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone


def main():
    from pipeline.agent_context import get_context
    from pipeline.persistence import write_json_atomic
    from main import load_jobs_state, STAGES_BY_TYPE
    from pipeline.checkpoints import resume_after

    ctx = get_context()
    root = ctx.repo_root
    issues = []
    entry = load_jobs_state(strict=True).get(ctx.job_id, {})
    names = [stage[0] for stage in STAGES_BY_TYPE[ctx.job_type]]
    if (not entry.get("artifacts") or entry.get("last_success_stage") != "23_telegram_pin_verifier"
            or resume_after(root, ctx.job_id, entry, names) != "23_telegram_pin_verifier"):
        issues.append("pipeline has not completed all pre-audit checkpoints")
    for relative, record in entry.get("artifacts", {}).items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            issues.append(f"missing checkpoint artifact: {relative}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != record.get("sha256"):
            issues.append(f"checkpoint artifact changed: {relative}")
    try:
        qa = json.loads(ctx.qa_report_path().read_text(encoding="utf-8"))
        if (qa.get("passed") is not True or qa.get("job_id") != ctx.job_id
                or qa.get("file_sha256") != hashlib.sha256(ctx.pdf_path().read_bytes()).hexdigest()):
            issues.append("PDF QA approval is absent, failed, or does not match the PDF")
    except (OSError, ValueError):
        issues.append("PDF/QA evidence unreadable")
    dry_run = os.getenv("DRY_RUN", "0") == "1"
    if not dry_run:
        from pipeline.publication import publication_issues
        pdf_hash = hashlib.sha256(ctx.pdf_path().read_bytes()).hexdigest() if ctx.pdf_path().is_file() else ""
        issues.extend(publication_issues(root, ctx.job_id, pdf_hash, os.getenv("TELEGRAM_CHAT_ID")))
    report = {"job_id": ctx.job_id, "passed": not issues, "dry_run": dry_run,
              "issues": issues, "checked_at": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(root / "logs" / "qa" / f"{ctx.job_id}_health.json", report)
    print(json.dumps(report, ensure_ascii=False))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
