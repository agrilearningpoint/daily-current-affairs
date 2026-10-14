"""Edition-local checkpoints: never skip work using missing or changed outputs."""

import hashlib
from pathlib import Path

STAGE_FILES = {
    "01_source_fetch": "data/raw/{job}.json",
    "04_fact_verification": "data/verified/{job}.json",
    "05_deduplication": "data/dedup/{job}.json",
    "06_news_importance": "data/scored/{job}.json",
    "07_student_domain_relevance": "data/scored/{job}.json",
    "10_final_news_selection": "data/selected/{job}.json",
    "11_importance_memory": "data/selected/{job}.json",
    "20_weekly_editor": "data/selected/{job}.json",
    "21_monthly_editor": "data/selected/{job}.json",
    "12_content_editor": "data/content/{job}.json",
    "16_mcq_generator": "data/mcq/{job}.json",
    "17_mcq_validator": "data/mcq/{job}.json",
    "18_pdf_design": "output/{job}.pdf",
    "19_pdf_qa": "logs/qa/{job}_qa.json",
    "24_final_health_audit": "logs/qa/{job}_health.json",
}


def capture(root: Path, job_id: str, stage: str, previous: dict) -> dict:
    """Mutable shared outputs retain their earliest producing stage for rewind."""
    artifacts = dict(previous)
    templates = [STAGE_FILES[stage]] if stage in STAGE_FILES else []
    if stage in {"20_weekly_editor", "21_monthly_editor"}:
        templates.append("data/scored/{job}.json")
    for template in templates:
        relative = template.format(job=job_id)
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"stage {stage} did not produce {relative}")
        artifacts[relative] = {
            "stage": previous.get(relative, {}).get("stage", stage),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    return artifacts


def resume_after(root: Path, job_id: str, entry: dict, stage_names: list[str]):
    last = entry.get("last_success_stage")
    if last not in stage_names:
        return None
    last_index = stage_names.index(last)
    artifacts = entry.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return None
    # Legacy checkpoints have no digests: inspect all required stage outputs.
    checks = dict(artifacts)
    for stage in stage_names[:last_index + 1]:
        template = STAGE_FILES.get(stage)
        if template:
            relative = template.format(job=job_id)
            checks.setdefault(relative, {"stage": stage})
    first_invalid = last_index + 1
    for relative, record in checks.items():
        if not isinstance(record, dict) or record.get("stage") not in stage_names:
            return None
        # A ledger loaded from disk must not authorize reading arbitrary paths.
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()):
            return None
        producer = stage_names.index(record["stage"])
        if producer > last_index:
            continue
        valid = path.is_file() and path.stat().st_size > 0
        if valid and record.get("sha256"):
            valid = hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        if not valid:
            first_invalid = min(first_invalid, producer)
    if first_invalid <= 1:
        return None
    return stage_names[first_invalid - 1] if first_invalid <= last_index else last
