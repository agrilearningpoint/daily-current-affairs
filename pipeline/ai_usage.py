"""Append-only record of AI calls and aggregated provider/key-slot observability.

Writes:
  - logs/ai_usage.jsonl       (ALP_AI_USAGE_LOG)
  - logs/provider_health.json (ALP_PROVIDER_HEALTH_PATH)
  - logs/provider_summary.json (ALP_PROVIDER_SUMMARY_PATH)

Never raises and never persists raw credentials.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pipeline.persistence import write_json_atomic

_ROOT = Path(__file__).resolve().parent.parent

# Published standard per-1M token rates for metered APIs; known free-tier models
# report $0.0 without guessing unverified pricing.
_MODEL_PRICE_PER_1M: Dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
}


def usage_log_path() -> Path:
    override = os.getenv("ALP_AI_USAGE_LOG")
    return Path(override) if override else _ROOT / "logs" / "ai_usage.jsonl"


def provider_health_path(root: Optional[Path] = None) -> Path:
    override = os.getenv("ALP_PROVIDER_HEALTH_PATH")
    if override:
        return Path(override)
    base = Path(root) if root else _ROOT
    return base / "logs" / "provider_health.json"


def provider_summary_path(root: Optional[Path] = None) -> Path:
    override = os.getenv("ALP_PROVIDER_SUMMARY_PATH")
    if override:
        return Path(override)
    base = Path(root) if root else _ROOT
    return base / "logs" / "provider_summary.json"


def estimate_cost_usd(
    provider: str,
    model: str,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
) -> Optional[float]:
    if provider in {"groq", "gemini", "mistral", "llm7", "nvidia", "cohere"}:
        return 0.0
    if provider == "openrouter" and (str(model).endswith(":free") or model == "openrouter/free"):
        return 0.0
    rates = _MODEL_PRICE_PER_1M.get(str(model or "").strip())
    if not rates or prompt_tokens is None or completion_tokens is None:
        return None
    in_cost = (int(prompt_tokens) / 1_000_000.0) * rates[0]
    out_cost = (int(completion_tokens) / 1_000_000.0) * rates[1]
    return round(in_cost + out_cost, 6)


def record_ai_usage(
    provider: str,
    model: str,
    task: str,
    ok: bool,
    detail: str = "",
    *,
    key_slot: str = "",
    latency_ms: Optional[float] = None,
    error_category: str = "",
    retry_count: int = 0,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    cost_usd: Optional[float] = None,
    cache_hit: bool = False,
    agent: str = "",
) -> None:
    try:
        path = usage_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            total_tokens = int(prompt_tokens) + int(completion_tokens)
        if cost_usd is None:
            cost_usd = estimate_cost_usd(str(provider or ""), str(model or ""), prompt_tokens, completion_tokens)
        row: Dict[str, Any] = {
            "at": datetime.now(timezone.utc).isoformat(),
            "job": os.getenv("ALP_JOB_ID", ""),
            "stage": os.getenv("ALP_STAGE_ID", ""),
            "agent": str(agent or os.getenv("ALP_STAGE_ID", "")),
            "provider": str(provider or ""),
            "model": str(model or ""),
            "key_slot": str(key_slot or ""),
            "task": str(task or ""),
            "ok": bool(ok),
            "retry_count": int(retry_count or 0),
            "cache_hit": bool(cache_hit),
        }
        if latency_ms is not None:
            row["latency_ms"] = round(float(latency_ms), 2)
        if error_category:
            row["error_category"] = str(error_category)[:48]
        if prompt_tokens is not None:
            row["prompt_tokens"] = int(prompt_tokens)
        if completion_tokens is not None:
            row["completion_tokens"] = int(completion_tokens)
        if total_tokens is not None:
            row["total_tokens"] = int(total_tokens)
        if cost_usd is not None:
            row["cost_usd"] = float(cost_usd)
        if detail:
            row["detail"] = str(detail)[:80]
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - accounting is best effort
        pass


def build_provider_summary(
    *,
    root: Optional[Path] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    usage_path = usage_log_path() if root is None else (
        Path(os.getenv("ALP_AI_USAGE_LOG")) if os.getenv("ALP_AI_USAGE_LOG") else Path(root) / "logs" / "ai_usage.jsonl"
    )
    target_job = job_id if job_id is not None else os.getenv("ALP_JOB_ID", "")
    by_provider: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "calls": 0, "successes": 0, "failures": 0, "rate_limits": 0,
            "cache_hits": 0, "prompt_tokens": 0, "completion_tokens": 0,
            "total_tokens": 0, "estimated_cost_usd": 0.0, "models": [],
        }
    )
    by_key_slot: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "successes": 0, "failures": 0, "rate_limits": 0, "total_tokens": 0}
    )
    by_task: Dict[str, Dict[str, int]] = defaultdict(lambda: {"calls": 0, "successes": 0, "failures": 0})
    totals = {
        "calls": 0, "successes": 0, "failures": 0, "rate_limits": 0,
        "fallback_events": 0, "cache_hits": 0, "prompt_tokens": 0,
        "completion_tokens": 0, "total_tokens": 0, "estimated_cost_usd": 0.0,
    }

    if usage_path.is_file():
        for raw_line in usage_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw_line.strip():
                continue
            try:
                row = json.loads(raw_line)
            except ValueError:
                continue
            if target_job and row.get("job") and row.get("job") != target_job:
                continue
            prov = str(row.get("provider") or "unknown")
            task = str(row.get("task") or "general")
            slot = str(row.get("key_slot") or f"{prov}:default")
            ok = bool(row.get("ok"))
            err_cat = str(row.get("error_category") or row.get("detail") or "")
            pt = int(row.get("prompt_tokens") or 0)
            ct = int(row.get("completion_tokens") or 0)
            tt = int(row.get("total_tokens") or (pt + ct))
            cost = float(row.get("cost_usd") or 0.0)
            cache_hit = bool(row.get("cache_hit"))
            is_rl = "rate_limit" in err_cat.lower() or "429" in err_cat
            retries = int(row.get("retry_count") or 0)

            totals["calls"] += 1
            totals["successes" if ok else "failures"] += 1
            if is_rl:
                totals["rate_limits"] += 1
            if retries > 0:
                totals["fallback_events"] += retries
            if cache_hit:
                totals["cache_hits"] += 1
            totals["prompt_tokens"] += pt
            totals["completion_tokens"] += ct
            totals["total_tokens"] += tt
            totals["estimated_cost_usd"] = round(totals["estimated_cost_usd"] + cost, 6)

            p_rec = by_provider[prov]
            p_rec["calls"] += 1
            p_rec["successes" if ok else "failures"] += 1
            if is_rl:
                p_rec["rate_limits"] += 1
            if cache_hit:
                p_rec["cache_hits"] += 1
            p_rec["prompt_tokens"] += pt
            p_rec["completion_tokens"] += ct
            p_rec["total_tokens"] += tt
            p_rec["estimated_cost_usd"] = round(p_rec["estimated_cost_usd"] + cost, 6)
            mdl = str(row.get("model") or "")
            if mdl and mdl not in p_rec["models"]:
                p_rec["models"].append(mdl)

            s_rec = by_key_slot[slot]
            s_rec["calls"] += 1
            s_rec["successes" if ok else "failures"] += 1
            if is_rl:
                s_rec["rate_limits"] += 1
            s_rec["total_tokens"] += tt

            t_rec = by_task[task]
            t_rec["calls"] += 1
            t_rec["successes" if ok else "failures"] += 1

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "job_id": target_job,
        "totals": totals,
        "by_provider": dict(by_provider),
        "by_key_slot": dict(by_key_slot),
        "by_task": dict(by_task),
    }


def update_provider_observability(
    *,
    root: Optional[Path] = None,
    health_state: Optional[Dict[str, Any]] = None,
    providers: Optional[Iterable[Any]] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Atomically write logs/provider_health.json and logs/provider_summary.json."""
    target_job = job_id if job_id is not None else os.getenv("ALP_JOB_ID", "")
    summary = build_provider_summary(root=root, job_id=target_job)

    prov_health: Dict[str, Any] = {}
    key_stats = (health_state or {}).get("key_stats") or {}
    blocks = (health_state or {}).get("blocks") or {}
    shared = (health_state or {}).get("shared_quota") or {}

    for p in providers or ():
        pname = getattr(p, "name", "")
        slots = list(getattr(p, "key_slots", []) or [])
        pool = list(getattr(p, "key_pool", []) or [])
        if not slots and pool:
            slots = [f"{pname}:slot_{i}" for i in range(len(pool))]
        slot_entries: List[Dict[str, Any]] = []
        for idx, slot_id in enumerate(slots):
            st = dict(key_stats.get(slot_id) or {})
            blk = blocks.get(f"{pname}#slot:{idx}") or {}
            slot_entries.append({
                "slot_id": slot_id,
                "active": idx == getattr(p, "key_idx", 0),
                "requests": int(st.get("requests", 0)),
                "successes": int(st.get("successes", 0)),
                "failures": int(st.get("failures", 0)),
                "rate_limits": int(st.get("rate_limits", 0)),
                "tokens_total": int(st.get("total_tokens", 0)),
                "auth_status": st.get("auth_status", "unknown"),
                "cooldown_until": float(blk.get("until", st.get("cooldown_until", 0.0)) or 0.0),
                "last_success_at": st.get("last_success_at"),
                "last_error": st.get("last_error"),
                "last_error_category": st.get("last_error_category"),
            })
        prov_health[pname] = {
            "configured_slots": len(slots),
            "active_slot": slots[getattr(p, "key_idx", 0)] if slots and getattr(p, "key_idx", 0) < len(slots) else "",
            "active_model": getattr(p, "model", ""),
            "available": bool(p.is_available()) if hasattr(p, "is_available") else True,
            "shared_quota_suspected": bool(shared.get(pname)),
            "slots": slot_entries,
        }

    health_doc = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "job_id": target_job,
        "providers": prov_health,
        "shared_quota": shared,
    }
    try:
        write_json_atomic(provider_health_path(root), health_doc)
        write_json_atomic(provider_summary_path(root), summary)
    except OSError:
        pass
    return {"health": health_doc, "summary": summary}
