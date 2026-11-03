# -*- coding: utf-8 -*-
"""FINAL NEWS SELECTION AGENT v2 — 25-30 items for 15+ pages"""
import logging
import os
import re

COMMAND = "Select top 25-30 news items with category diversity."
RAW_FILE_RE = re.compile(
    r"(?:\b[\w\-_.]+\.(?:pdf|docx?|xlsx?|csv|pptx)\b)|(?:^\s*[\w\-_.]+\.(?:pdf|docx?|xlsx?)\b)",
    re.IGNORECASE,
)
MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity."

# NON_NEWS_RE / topic_key live in pipeline.news_filters (shared with the Quick Bites
# and Agriculture Corner builder); re-exported here for backward compatibility.
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

if str(_Path(__file__).resolve().parent.parent) not in _sys.path:
    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from pipeline.news_filters import NON_NEWS_RE, topic_key as _topic_key  # noqa: E402


class Agent:
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "FINAL NEWS SELECTION AGENT v2"

    def run(self):
        from pipeline.state import SCORED_DIR, SELECTED_DIR, data_path, read_json, write_json_atomic
        scored = read_json(data_path(SCORED_DIR, self.job_id), {"items": []})["items"]
        if not scored:
            self.context["stage_failed"] = "no scored items"
            raise RuntimeError(self.context["stage_failed"])
        target = {"daily": 28, "weekly": 35, "monthly": 40}.get(self.job_type, 28)
        env_target = os.getenv("ALP_TARGET_NEWS_COUNT")
        if env_target and env_target.isdigit():
            target = int(env_target)
        def _is_valid_candidate(x: dict) -> bool:
            h = (x.get("headline_en") or x.get("title") or "").strip()
            if not h:
                return True
            if len(h) < 15 or len(h.split()) < 2:
                return False
            if len(h.split()) < 3 and not (x.get("must_include") and re.search(r"[A-Z]{2,}|\d", h)):
                return False  # two-word titles only for official releases like "GSLV-F18/NVS-03 Mission"
            if RAW_FILE_RE.search(h):
                return False
            if re.search(r"\buntitled\b", h, re.I):
                return False
            if h.startswith(("-", "—", "–", ":")):
                return False
            if re.match(r"^(?:Department|Ministry)\s+of\s+[A-Za-z\s,&-]+$", h, re.I):
                return False
            if re.match(r"^Sports Authority of India$", h, re.I):
                return False
            if os.getenv("ALP_FILTER_NON_NEWS", "1") != "0" and NON_NEWS_RE.search(h):
                return False
            return True

        scored = [x for x in scored if _is_valid_candidate(x)]
        scored = self._drop_previous_edition_repeats(scored)
        scored.sort(key=lambda x: x.get("student_relevance", x.get("importance_score", 0)), reverse=True)
        n_before = len(scored)
        selected = self._diverse_selection(scored, target)
        selected = self._ensure_official(selected, scored, target)
        # Reserves: the next-best candidates, used by stage 12 (stories dropped for
        # unreviewed translation) and stage 16 (stories without a valid MCQ) to
        # backfill so the edition still reaches its target count.
        try:
            n_res = int(os.getenv("ALP_SELECTION_RESERVES", str(max(8, target // 2))))
        except ValueError:
            n_res = max(8, target // 2)
        chosen = {id(x) for x in selected}
        reserves = [x for x in scored if id(x) not in chosen][:max(0, n_res)]
        logging.info(f"[{self.name}] selected {len(selected)} items (target={target}), "
                     f"{len(reserves)} reserve(s); {n_before} valid candidates")
        cats = {}
        for item in selected:
            cat = item.get("category", "Other")
            cats[cat] = cats.get(cat, 0) + 1
        for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
            logging.info(f"  {cat}: {cnt}")
        # Scheduled production runs require enough verified stories for a
        # substantive student revision booklet. Offline diagnostics can retain
        # the permissive default by omitting this setting.
        min_items = 1 if self.job_type == "daily" else 5
        if self.job_type == "daily":
            raw_min = os.getenv("ALP_MIN_DAILY_NEWS", str(min_items)).strip()
            try:
                min_items = int(raw_min)
            except ValueError as exc:
                raise RuntimeError(
                    "ALP_MIN_DAILY_NEWS must be a whole number between 1 and 40"
                ) from exc
            if not 1 <= min_items <= 40:
                raise RuntimeError("ALP_MIN_DAILY_NEWS must be between 1 and 40")
        if len(selected) < min_items:
            self.context["stage_failed"] = (
                f"only {len(selected)} selected (min {min_items} for {self.job_type})"
            )
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(SELECTED_DIR, self.job_id), {"items": selected, "reserves": reserves})
        self.context["selected_count"] = len(selected)
        self.context["reserve_count"] = len(reserves)
        return self.context

    def _drop_previous_edition_repeats(self, scored):
        """Daily only: never re-print a story an earlier daily edition (last
        ALP_REPEAT_LOOKBACK_DAYS, default 3) already carried. Overlapping
        windows (late cron / reset) made 5 of 15 stories of daily_2026-11-03
        repeats of daily_2026-11-02. ALP_ALLOW_REPEATS=1 disables it."""
        if self.job_type != "daily" or os.getenv("ALP_ALLOW_REPEATS", "0") == "1":
            return scored
        try:
            from pipeline import store
            from pipeline.news_filters import story_key
            days = int(os.getenv("ALP_REPEAT_LOOKBACK_DAYS", "3"))
            seen = store.recently_selected(self.job_id, days)
        except Exception as exc:  # memory unreadable -> do not block the edition
            logging.warning(f"[{self.name}] repeat filter skipped: {exc}")
            return scored
        if not any(seen.values()):
            return scored
        kept = []
        for x in scored:
            key = story_key(x.get("headline_en") or x.get("title") or "")
            if (str(x.get("event_id")) in seen["ids"] or (x.get("link") and x["link"] in seen["links"])
                    or (key and key in seen["keys"])):
                continue
            kept.append(x)
        logging.info(f"[{self.name}] dropped {len(scored) - len(kept)} candidate(s) already "
                     f"published in the previous {days} daily edition(s)")
        self.context["repeat_dropped"] = len(scored) - len(kept)
        return kept

    def _diverse_selection(self, scored, target):
        """Category round-robin with a per-publisher cap (ALP_MAX_PER_SOURCE_PCT,
        default 40% of the target) so one feed cannot fill the edition; the cap is
        relaxed only when the other sources cannot reach the target."""
        try:
            pct = float(os.getenv("ALP_MAX_PER_SOURCE_PCT", "0.4"))
        except ValueError:
            pct = 0.4
        cap = max(3, -(-int(target * pct * 100) // 100)) if 0 < pct < 1 else target
        def _src(x):
            return str(x.get("source_name") or x.get("source_id") or "")
        from pipeline.official_sources import is_must_include
        official_cap = max(cap, -(-target * 6 // 10))
        counts = {}
        capped = []
        topic_counts = {}
        try:
            topic_cap = max(1, int(os.getenv("ALP_MAX_PER_TOPIC", "2")))
        except ValueError:
            topic_cap = 2
        for x in scored:
            k = _src(x)
            topic = _topic_key(x)
            if topic and topic_counts.get(topic, 0) >= topic_cap:
                continue  # e.g. ten "Cyclone Murasu: ..." updates -> keep the best two
            # Official wires (PIB alone carries every ministry's releases) get a higher cap.
            if counts.get(k, 0) < (official_cap if is_must_include(x) else cap):
                counts[k] = counts.get(k, 0) + 1
                if topic:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
                capped.append(x)
        picked = self._round_robin(capped, target)
        if len(picked) < target:
            seen = {id(x) for x in picked}
            picked += [x for x in scored if id(x) not in seen][:target - len(picked)]
        return picked

    def _ensure_official(self, selected, scored, target):
        """Official PIB/PMO/MEA/RBI/ISRO/IMD/SEBI releases are must-include: guarantee
        at least ALP_MIN_OFFICIAL_STORIES (default 5, capped at a third of the target)
        of the best of them, replacing the weakest non-official picks."""
        from pipeline.official_sources import is_must_include
        try:
            want = int(os.getenv("ALP_MIN_OFFICIAL_STORIES", "5"))
        except ValueError:
            want = 5
        want = max(0, min(want, max(1, target // 3)))
        rel = lambda x: x.get("student_relevance", x.get("importance_score", 0))
        have = [x for x in selected if is_must_include(x)]
        if len(have) >= want:
            return selected
        chosen = {id(x) for x in selected}
        pool = [x for x in scored if id(x) not in chosen and is_must_include(x) and rel(x) >= 20]
        out = list(selected)
        for cand in pool[: want - len(have)]:
            weak = [x for x in out if not is_must_include(x) and not x.get("agri_focus") and not x.get("banking_focus")]
            if len(out) >= target and weak:
                out.remove(min(weak, key=rel))
            out.append(cand)
        return out[:target] if len(out) > target else out

    def _round_robin(self, scored, target):
        selected = []
        by_category = {}
        for item in scored:
            cat = item.get("category", "Other")
            by_category.setdefault(cat, []).append(item)
        priority_cats = [
            "Agriculture", "Banking & Finance", "Economy", "Government Schemes",
            "National", "International", "Science & Technology", "Environment",
            "Sports", "Awards & Honours", "Appointments", "Defence", "Education"
        ]
        cat_idx = {cat: 0 for cat in priority_cats}
        # Category diversity must not promote weak stories over clearly stronger ones:
        # the round-robin only takes items within reach of the day's best story; the
        # rest of the edition is filled strictly by relevance.
        rel = lambda x: x.get("student_relevance", x.get("importance_score", 0)) or 0
        try:
            floor_pct = float(os.getenv("ALP_ROUND_ROBIN_FLOOR", "0.6"))
        except ValueError:
            floor_pct = 0.6
        floor = floor_pct * max((rel(x) for x in scored), default=0)
        for cat in list(by_category):
            by_category[cat] = [x for x in by_category[cat] if rel(x) >= floor]
        while len(selected) < target:
            added = False
            for cat in priority_cats:
                if len(selected) >= target:
                    break
                items = by_category.get(cat, [])
                idx = cat_idx[cat]
                if idx < len(items):
                    item = items[idx]
                    if item not in selected:
                        selected.append(item)
                        cat_idx[cat] = idx + 1
                        added = True
            if not added:
                for item in scored:
                    if len(selected) >= target:
                        break
                    if item not in selected:
                        selected.append(item)
                break
        if len(selected) < target:
            for item in scored:
                if len(selected) >= target:
                    break
                if item not in selected:
                    selected.append(item)
        return selected[:target]

    def verify(self):
        return not self.context.get("stage_failed")


# =============================================================================
# STANDALONE ENTRYPOINT (for pipeline integration)
# =============================================================================
if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path

    # Ensure repo root importable
    _REPO = Path(__file__).resolve().parent.parent
    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))

    # Basic logging
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    # --- Load job context from env (set by main.py) ---
    _job_id = os.getenv("ALP_JOB_ID") or os.getenv("JOB_ID") or ""
    _job_type = os.getenv("ALP_JOB_TYPE") or os.getenv("JOB_TYPE") or "daily"
    _job_date = os.getenv("ALP_JOB_DATE") or ""

    if not _job_date and _job_id and "_" in _job_id:
        _job_date = _job_id.split("_", 1)[1]

    if not _job_date:
        from datetime import datetime, timezone
        _job_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not _job_id:
        _job_id = f"{_job_type}_{_job_date}"

    print(f"[10_final_news_selection] job={_job_id} type={_job_type} date={_job_date}")

    # --- Run agent ---
    _context = {}
    _exit_code = 0

    try:
        _agent = Agent(job_id=_job_id, job_type=_job_type, context=_context)
        _agent.run()
        print(f"[10] OK — selected_count={_context.get('selected_count', '?')}")
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[10] FAILED: {exc}", file=sys.stderr)
        _exit_code = 1

    sys.exit(_exit_code)
