# -*- coding: utf-8 -*-
"""
MCQ GENERATOR AGENT v5 — one validated MCQ per final story, FAIL-CLOSED.

Every story printed in the PDF is a question unit, so a story without a valid
MCQ would silently disappear from the edition (run 41425513692: 15 stories,
8 MCQs, 7 stories missing).  This stage therefore:

1. asks the LLM for the reference-format MCQ of each story, checking every
   attempt against the schema *and* the generic validator (retry with the
   rejection reasons);
2. falls back per story to bilingual deterministic templates, then to the
   legacy templates — the first candidate that passes ``validate_mcqs`` wins;
3. drops a story only when no candidate validates, and promotes the next
   reserve story (built by stage 12) in its place, so the edition keeps its
   target count;
4. writes the validated MCQs and the reconciled content (items == stories
   with an MCQ) atomically.  Validation failure still stops the pipeline.
"""
import logging
import os

COMMAND = "Generate one validated bilingual MCQ per final story; backfill from reserves. Validation failure = pipeline failure."
MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts."


class Agent:
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "MCQ GENERATOR AGENT v5 (FAIL-CLOSED)"

    def run(self):
        from pipeline.state import CONTENT_DIR, MCQ_DIR, data_path, read_json, write_json_atomic
        from pipeline.content import (_build_pools, _evidence_text, _qkey, refresh_content_summaries,
                                      renumber_mcqs, validate_mcqs)
        from pipeline.mcq_builder import candidates_for_item, first_valid
        from pipeline.mcq_schema import generate_llm_mcqs, llm_mode_enabled

        content_path = data_path(CONTENT_DIR, self.job_id)
        content = read_json(content_path)
        items = [i for i in (content.get("items") or []) if isinstance(i, dict)]
        reserves = [i for i in (content.get("reserve_items") or []) if isinstance(i, dict)]
        target = len(items)
        logging.info(f"[{self.name}] Generating MCQs for {target} items ({len(reserves)} reserve(s))...")

        def _check(m, item):
            ok, rej = validate_mcqs([m], [item])
            return [] if ok else list(rej[0].get("errors") or ["rejected"])

        use_llm = llm_mode_enabled()

        def _llm_for(batch):
            if not use_llm or not batch:
                return {}
            try:
                return generate_llm_mcqs(batch, _evidence_text, extra_check=_check)
            except Exception as exc:
                logging.warning(f"[{self.name}] LLM MCQ schema pass failed, using templates: {exc}")
                return {}

        llm_mcqs = _llm_for(items)
        self.context["mcqs_llm_schema"] = len(llm_mcqs)

        pools = _build_pools(items + reserves)
        final_items, mcqs, seen_q, dropped = [], [], set(), []
        spare_cands = {}

        def _assign(ci, llm_map):
            cands = candidates_for_item(ci, _evidence_text(ci), pools, items + reserves,
                                        llm_map.get(str(ci.get("event_id", ""))))
            spare_cands[str(ci.get("event_id", ""))] = cands
            m, reasons = first_valid(cands, ci, seen_q)
            if m is None:
                dropped.append({"event_id": ci.get("event_id"), "headline": ci.get("headline_en", "")[:90],
                                "reasons": reasons[:6]})
                logging.warning(f"[{self.name}] no valid MCQ for {ci.get('event_id')}: {reasons[:4]}")
                return False
            seen_q.add(_qkey(m.get("question_en")))
            final_items.append(ci)
            mcqs.append(m)
            return True

        for ci in items:
            _assign(ci, llm_mcqs)

        promoted = 0
        while len(final_items) < target and reserves:
            ci = reserves.pop(0)
            if _assign(ci, _llm_for([ci])):
                promoted += 1
        if promoted:
            logging.info(f"[{self.name}] promoted {promoted} reserve stor(y/ies) to keep {len(final_items)}/{target}")

        # Sparse editions: PDF QA expects min(10, 2 x stories) questions, so give
        # stories a second validated question (different template) round-robin.
        want = min(10, 2 * len(final_items))
        if len(mcqs) < want:
            extra = []
            for ci in final_items:
                if len(mcqs) + len(extra) >= want:
                    break
                used = {_qkey(m.get("question_en")) for m in mcqs if m.get("event_id") == ci.get("event_id")}
                rest = [c for c in spare_cands.get(str(ci.get("event_id", "")), [])
                        if _qkey(c.get("question_en")) not in used]
                m2, _ = first_valid(rest, ci, seen_q)
                if m2 is not None:
                    seen_q.add(_qkey(m2.get("question_en")))
                    extra.append(m2)
            if extra:
                order = {str(i.get("event_id")): n for n, i in enumerate(final_items)}
                mcqs = sorted(mcqs + extra, key=lambda m: order.get(str(m.get("event_id")), 10 ** 6))
                logging.info(f"[{self.name}] sparse edition: added {len(extra)} second question(s)")

        by_type = {}
        for m in mcqs:
            by_type[m.get("type", "?")] = by_type.get(m.get("type", "?"), 0) + 1
        logging.info(f"[{self.name}] MCQ sources: {by_type}")

        # ═══════════════ FAIL-CLOSED whole-set validation (same as stage 17) ═══════════════
        try:
            valid_mcqs, rejected = validate_mcqs(mcqs, final_items)
        except Exception as e:
            error_msg = f"MCQ validation failed with exception: {e}. Cannot proceed with unvalidated MCQs."
            logging.error(f"[{self.name}] {error_msg}")
            self.context["stage_failed"] = error_msg
            raise RuntimeError(error_msg)
        if rejected:  # cannot normally happen: every MCQ was validated individually
            bad = {str(r.get("event_id")) for r in rejected}
            final_items = [i for i in final_items if str(i.get("event_id")) not in bad]
            logging.warning(f"[{self.name}] whole-set validation removed {len(rejected)} MCQ(s)")
        if not valid_mcqs:
            error_msg = f"MCQ validation returned 0 valid MCQs for {target} stories"
            logging.error(f"[{self.name}] {error_msg}")
            self.context["stage_failed"] = error_msg
            raise RuntimeError(error_msg)

        min_mcqs = min(8, target)
        if len(valid_mcqs) < min_mcqs:
            error_msg = (f"only {len(valid_mcqs)} valid MCQs for {target} news (need >={min_mcqs}). "
                         "Validation is working correctly - rejecting low quality.")
            logging.error(f"[{self.name}] {error_msg}")
            self.context["stage_failed"] = error_msg
            raise RuntimeError(error_msg)

        renumber_mcqs(valid_mcqs)
        write_json_atomic(data_path(MCQ_DIR, self.job_id), valid_mcqs)

        # Content now lists exactly the stories that have a question unit.
        content["items"] = final_items
        content["reserve_items"] = reserves
        content["mcq_reconciliation"] = {"target": target, "final": len(final_items),
                                         "promoted_reserves": promoted, "dropped_no_mcq": dropped}
        refresh_content_summaries(content)
        write_json_atomic(content_path, content)

        if len(final_items) < target:
            logging.warning(f"[{self.name}] edition has {len(final_items)}/{target} stories "
                            f"(reserves exhausted; {len(dropped)} without a valid MCQ)")
        logging.info(f"[{self.name}] ✓ Final: {len(valid_mcqs)} VALIDATED MCQs for {len(final_items)} stories")
        self.context["mcqs_generated"] = len(valid_mcqs)
        self.context["stories_final"] = len(final_items)
        self.context["validation_method"] = "mcq_validator_v2"
        self.context["validation_status"] = "PASSED"
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    from pipeline.artifacts import run_agent
    logging.basicConfig(level=logging.INFO)
    run_agent(Agent)
