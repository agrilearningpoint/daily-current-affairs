# -*- coding: utf-8 -*-
"""
CONTENT EDITOR AGENT
Main focus: selected news को student-facing bilingual content में बदलना।

Command:
> "For each selected event produce: headline_en, key_points (2-4 bullets), static-fact table rows, exam-fact note — strictly extracted from verified source text. Never invent facts; if AI polish is configured it may only reword, never add numbers."

Work: Deterministic extraction + optional guarded AI polish. Merged (audit refactor 2026-10):
Agent 13 Bilingual Editor + Agent 14 English Editor now run as inline passes in this stage.
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """For each selected event produce: headline_en, key_points (2-4 bullets), static-fact table rows, exam-fact note — strictly extracted from verified source text. Never invent facts; if AI polish is configured it may only reword, never add numbers."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- pipeline.content.build_content() → data/content/<job_id>.json"""


class Agent:
    """CONTENT EDITOR AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "CONTENT EDITOR AGENT"

    def run(self):
        import logging
        from pipeline.content import build_content
        from pipeline.state import SELECTED_DIR, CONTENT_DIR, data_path, read_json, write_json_atomic
        items = read_json(data_path(SELECTED_DIR, self.job_id), {"items": []})["items"]
        meta = {"id": self.job_id, "type": self.job_type, "date": self.context["job_date"],
                "date_display": self.context.get("date_display", self.context["job_date"])}
        content = build_content(items, meta)
        if not content["items"]:
            self.context["stage_failed"] = "content editor produced 0 items"
            raise RuntimeError(self.context["stage_failed"])
        # --- merged bilingual pass (former Agent 13): guarantee Hindi fields exist ---
        # Smart AI Router: Hindi via Gemini (best quality) -> Groq -> Mistral,
        # chunked 3 items/chunk with 5s delay so free-tier limits never hit.
        from pipeline.content import translate_headline
        try:
            from pipeline.ai_router import chunked, route
            HAS_ROUTER = True
        except ImportError:
            HAS_ROUTER = False
        fixed = 0

        def _translate_batch(batch):
            nonlocal fixed
            for it in batch:
                need = []
                if not it.get("headline_hi"):
                    need.append(it["headline_en"])
                if not it.get("key_points_hi"):
                    need.extend(it["key_points_en"])
                if not need:
                    continue
                lines = None
                if HAS_ROUTER:
                    try:
                        prompt = ("Translate each line to Hindi (Devanagari script, exam-style, "
                                  "keep numbers/names/schemes as-is). Return exactly "
                                  f"{len(need)} lines, one per input, no numbering:\n" + "\n".join(need))
                        out = route(prompt, task="bilingual")
                        got = [l.strip() for l in str(out).splitlines() if l.strip()]
                        if len(got) == len(need):
                            lines = got
                    except Exception as e:
                        logging.warning(f"[{self.name}] AI router translate fail: {e}")
                if not lines:  # safe offline fallback
                    lines = [">> " + translate_headline(x) for x in need]
                idx = 0
                if not it.get("headline_hi"):
                    it["headline_hi"] = lines[idx]; idx += 1
                if not it.get("key_points_hi"):
                    it["key_points_hi"] = lines[idx:idx + len(it["key_points_en"])]
                fixed += 1
            return batch

        pending = [it for it in content["items"]
                   if not it.get("headline_hi") or not it.get("key_points_hi")]
        if HAS_ROUTER and len(pending) > 3:
            chunked(pending, _translate_batch, chunk_size=3, delay=5)
        else:
            _translate_batch(pending)
        # --- merged english QA pass (former Agent 14): cleanup + source-link validation ---
        import re as _re
        for it in content["items"]:
            it["headline_en"] = _re.sub(r"\s+", " ", it["headline_en"]).strip()[:160]
            it["key_points_en"] = [_re.sub(r"\s+", " ", p).strip() for p in it["key_points_en"] if p.strip()]
            if not it["source"].get("url"):
                raise RuntimeError(f"item without source url: {it['event_id']}")
        write_json_atomic(data_path(CONTENT_DIR, self.job_id), content)
        logging.info(f"[{self.name}] content ready: {len(content['items'])} items (bilingual fixed={fixed})")
        self.context["content_items"] = len(content["items"])
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
