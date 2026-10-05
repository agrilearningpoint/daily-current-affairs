# -*- coding: utf-8 -*-
"""
FINAL NEWS SELECTION AGENT
Main focus: pipeline का सबसे important decision — final news चुनना।

Command:
> "Select the final edition set purely by merit: daily 10-12, weekly 15-18 Best-of-Week, monthly 20-25 Best-of-Month. If fewer qualify, ship fewer — NEVER fill with weak news. Ensure category balance (agri/banking/international visible)."

Work: Merit-based threshold selection
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Select the final edition set purely by merit: daily 10-12, weekly 15-18 Best-of-Week, monthly 20-25 Best-of-Month. If fewer qualify, ship fewer — NEVER fill with weak news. Ensure category balance (agri/banking/international visible)."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- rank by student_relevance & importance_score; per-type targets as MAXIMUM caps;
- quality floor: daily 25 / weekly 60 / monthly 62 (student_relevance scale); never pads;
  writes data/selected/<job_id>.json"""


class Agent:
    """FINAL NEWS SELECTION AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "FINAL NEWS SELECTION AGENT"

    def run(self):
        import logging
        from pipeline.state import SCORED_DIR, SELECTED_DIR, data_path, read_json, write_json_atomic
        items = read_json(data_path(SCORED_DIR, self.job_id), {"items": []})["items"]
        # VARIABLE QUANTITY, FIXED QUALITY — per spec:
        # daily:  4-15 (floor 25), weekly: 8-18 (floor 60), monthly: 10-25 (floor 62)
        # Never pad weak news to hit 12; publish 4 excellent > 10 mediocre
        cfg = {"daily": (4, 15, 25), "weekly": (8, 18, 60), "monthly": (10, 25, 62)}[self.job_type]
        lo, hi, floor = cfg
        from pipeline import store
        try:
            published = store.published_event_ids()
        except Exception:
            published = set()
        # P0 FIX: Never fallback to published events — daily must not re-publish old news to fill quota
        # Previously `or items` caused published events to reappear when fresh empty → duplicate
        fresh = [i for i in items if i["event_id"] not in published]
        if not fresh:
            logging.warning(f"[{self.name}] no fresh events after published filter — will publish 0 (variable quantity, not filling with published)")
            # Do not fallback to published; variable quantity allows 0-4 publish
            fresh = []
        # Sort fresh by relevance before filtering so best quality survives cap
        fresh_sorted = sorted(fresh, key=lambda x: -x.get("student_relevance", x.get("importance_score",0)))
        candidates = [i for i in fresh_sorted if i.get("student_relevance", i.get("importance_score", 0)) >= floor]
        # Variable quantity logic (spec table):
        # 4 verified -> 4-5, 10 verified -> 8-12, 30 verified -> 12-15, 100+ -> 12-15
        # Implementation: take all candidates up to hi, but allow very low counts
        if len(candidates) <= lo:
            chosen = candidates  # very low: publish what we have (4)
        elif len(candidates) <= 12:
            chosen = candidates[:12]  # normal
        else:
            chosen = candidates[:hi]  # high / very high -> cap at hi (15 daily, 18 weekly, 25 monthly)

        # SOFT BALANCE — targets, not mandatory quotas (per spec):
        # Agri 35-40%, Banking 20-25%, Govt/Schemes 15-20%, International 10-15%, Science 5-10%, Awards 5-10%
        # We ensure diversity without sacrificing quality: try to meet targets by replacement, not by adding weak
        def soft_ensure(cat_key, target_pct, label):
            if not chosen:
                return
            desired = max(1, round(len(chosen) * target_pct))
            have = sum(1 for c in chosen if c.get(cat_key))
            if have >= desired:
                return
            # Candidates for this category that passed floor but were cut by cap
            pool = [it for it in candidates if it.get(cat_key) and it not in chosen]
            if not pool:
                # Try from fresh below floor but close? No — never pad weak, so skip
                return
            pool.sort(key=lambda x: -x.get("student_relevance",0))
            for it in pool:
                if sum(1 for c in chosen if c.get(cat_key)) >= desired:
                    break
                # Replace weakest non-essential if at cap
                if len(chosen) < hi:
                    chosen.append(it)
                else:
                    non_essential = [c for c in chosen if not c.get(cat_key)]
                    if not non_essential:
                        break
                    non_essential.sort(key=lambda x: x.get("student_relevance",0))
                    weakest = non_essential[0]
                    # Only replace if candidate not much weaker (within 10 points) to preserve quality
                    if it.get("student_relevance",0) + 10 >= weakest.get("student_relevance",0):
                        chosen.remove(weakest)
                        chosen.append(it)
                        logging.info(f"[{self.name}] soft-balance {label}: replaced {weakest.get('headline_en','')[:40]} -> {it.get('headline_en','')[:40]}")
                    else:
                        break

        # Apply soft targets based on current chosen size
        soft_ensure("agri_focus", 0.35, "Agriculture 35%")
        soft_ensure("banking_focus", 0.22, "Banking 22%")
        # Govt/Schemes via category check
        def govt_soft():
            have = sum(1 for c in chosen if c.get("category") in ("Government Schemes","National","Governance"))
            desired = max(1, round(len(chosen)*0.18))
            if have >= desired: return
            pool = [it for it in candidates if it.get("category") in ("Government Schemes","National","Governance") and it not in chosen]
            pool.sort(key=lambda x: -x.get("student_relevance",0))
            for it in pool:
                if sum(1 for c in chosen if c.get("category") in ("Government Schemes","National","Governance")) >= desired: break
                if len(chosen) < hi:
                    chosen.append(it)
                else:
                    # replace weakest not govt
                    non = [c for c in chosen if c.get("category") not in ("Government Schemes","National","Governance")]
                    if not non: break
                    non.sort(key=lambda x: x.get("student_relevance",0))
                    if it.get("student_relevance",0)+10 >= non[0].get("student_relevance",0):
                        chosen.remove(non[0]); chosen.append(it)
                    else: break
        govt_soft()

        chosen.sort(key=lambda x: -x.get("student_relevance", x.get("importance_score",0)))
        # Hard cap enforcement (variable, but never exceed hi)
        if len(chosen) > hi:
            chosen = chosen[:hi]
            logging.warning(f"[{self.name}] capped to {hi} after balance")
        # Log diversity
        cats = {}
        for c in chosen: cats[c.get("category","Other")] = cats.get(c.get("category","Other"),0)+1
        agri_n = sum(1 for c in chosen if c.get("agri_focus"))
        bank_n = sum(1 for c in chosen if c.get("banking_focus"))
        logging.info(f"[{self.name}] selected {len(chosen)} (candidates {len(candidates)}, target {lo}-{hi}, floor {floor}) agri {agri_n} banking {bank_n} cats {cats}")
        # CORE coverage gate — GOOD >=70%, DEGRADED 50-70%, BLOCKED <50% (audit #9)
        try:
            from pipeline.collector import core_coverage_report
            cov = core_coverage_report(candidates if candidates else items)
            ratio = cov.get("coverage_ratio", 0)
            if ratio >= 0.7:
                logging.info(f"[{self.name}] CORE coverage GOOD {ratio:.0%} ({cov['covered']}/{cov['attempted']})")
            elif ratio >= 0.5:
                logging.warning(f"[{self.name}] CORE coverage DEGRADED {ratio:.0%} — {cov['missing'][:3]} missing, but continuing")
            else:
                logging.error(f"[{self.name}] CORE coverage BLOCKED {ratio:.0%} — too many CORE sources failed, refusing publish")
                self.context["stage_failed"] = f"CORE coverage BLOCKED {ratio:.0%} ({cov['covered']}/{cov['attempted']}) — {cov['missing'][:2]}"
                raise RuntimeError(self.context["stage_failed"])
        except RuntimeError:
            raise
        except Exception as e:
            logging.warning(f"CORE gate check failed (non-blocking): {e}")
        # Variable quantity check — allow 4-15, never pad weak
        if len(chosen) < lo:
            # If we have fewer than lo but candidates were exactly that many, it's okay to publish low
            # Only fail if we have 0 or below dynamic minimum (4 daily)
            if len(chosen) == 0:
                self.context["stage_failed"] = f"selection too small: {len(chosen)} (min {lo} for {self.job_type}) — refusing to pad (MASTER_RULE)"
                raise RuntimeError(self.context["stage_failed"])
            logging.warning(f"[{self.name}] low news day: publishing {len(chosen)} excellent events (target {lo}-{hi}) — variable quantity, fixed quality")
        write_json_atomic(data_path(SELECTED_DIR, self.job_id), {"items": chosen})
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
