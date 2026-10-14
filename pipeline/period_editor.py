"""Best-of-week/month selection from the shared, verified event database."""

from datetime import datetime
from email.utils import parsedate_to_datetime
import os

from pipeline.artifacts import normalize_item
from pipeline.persistence import write_json_atomic
from pipeline.scoring import deduplicate, score_all
from pipeline.store import load_memory
from pipeline.windows import IST, collect_window


def publication_time(value):
    if not value:
        return None
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        try:
            result = parsedate_to_datetime(str(value))
        except (ValueError, TypeError):
            return None
    # Unknown timezones are not silently stamped as current news.
    return result if result.tzinfo is not None else None


def prepare(ctx):
    if ctx.job_type not in {"weekly", "monthly"}:
        raise ValueError("period editor requires weekly/monthly job context")
    start, end = collect_window(ctx.job_type, ctx.job_date)
    dry_run = os.getenv("DRY_RUN", "0") == "1"
    eligible = []
    for record in load_memory().values():
        if not isinstance(record, dict) or record.get("is_verified") is not True:
            continue
        if not dry_run and (record.get("verification_mode") != "live" or record.get("provenance_verified") is not True):
            continue
        published = publication_time(record.get("published") or record.get("pub_time_ist"))
        if published is None or not start <= published.astimezone(IST) <= end:
            continue
        item = normalize_item(record)
        if item["headline_en"] and item["source_url"]:
            eligible.append(item)
    scored = score_all(deduplicate(eligible))
    minimum = 5 if ctx.job_type == "weekly" else 8
    if len(scored) < minimum:
        raise ValueError(f"only {len(scored)} verified {ctx.job_type} events in requested period (min {minimum})")
    target = 35 if ctx.job_type == "weekly" else 40
    # Round-robin categories after ranking, rather than concatenating daily PDFs.
    groups = {}
    for item in scored:
        groups.setdefault(item["category"], []).append(item)
    selected = []
    while len(selected) < target and any(groups.values()):
        for items in groups.values():
            if items and len(selected) < target:
                selected.append(items.pop(0))
    metadata = {"start": start.isoformat(), "end": end.isoformat(), "type": ctx.job_type}
    write_json_atomic(ctx.output_path("scored"), {"items": scored, "period": metadata})
    write_json_atomic(ctx.output_path("selected"), {"items": selected, "period": metadata})
    print(f"{ctx.job_type}: selected {len(selected)} verified events; {start.isoformat()} .. {end.isoformat()}")
    return 0
