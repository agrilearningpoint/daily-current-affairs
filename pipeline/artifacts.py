"""Shared news artifact contract: canonical objects, legacy lists accepted on read."""

import hashlib
import json
from pathlib import Path

from pipeline.categories import CATEGORY_NAMES, normalize_category  # noqa: F401 (re-exported)


def normalize_item(item):
    if not isinstance(item, dict):
        raise ValueError("news item must be an object")
    out = dict(item)
    out["headline_en"] = item.get("headline_en") or item.get("title") or ""
    out["title"] = item.get("title") or out["headline_en"]
    out["raw_facts"] = item.get("raw_facts") or item.get("summary") or ""
    out["summary"] = item.get("summary") or out["raw_facts"]
    out["source_url"] = item.get("source_url") or item.get("link") or ""
    out["link"] = item.get("link") or out["source_url"]
    out["source_name"] = item.get("source_name") or item.get("source_feed") or ""
    tier = str(item.get("source_tier", "tier3"))
    out["source_tier"] = tier if tier.startswith("tier") else "tier" + tier
    category = item.get("category") or "National"
    out["category"] = normalize_category(category)
    out["event_id"] = item.get("event_id") or hashlib.sha256(
        (out["headline_en"] + "|" + out["source_url"]).encode("utf-8")
    ).hexdigest()[:16]
    return out


def news_items(data):
    if isinstance(data, dict):
        data = data.get("items", data.get("articles"))
    if not isinstance(data, list):
        raise ValueError("news artifact must contain an items/articles list")
    return [normalize_item(item) for item in data]


def read_news_items(path: Path):
    return news_items(json.loads(Path(path).read_text(encoding="utf-8")))


def run_agent(agent_class):
    """Execute a class-based agent with the real job context, never test IDs."""
    from pipeline.agent_context import get_context
    ctx = get_context()
    context = {"job_id": ctx.job_id, "job_type": ctx.job_type, "job_date": ctx.job_date}
    agent = agent_class(ctx.job_id, ctx.job_type, context)
    agent.run()
    if not agent.verify():
        raise RuntimeError(context.get("stage_failed", "agent verification failed"))
