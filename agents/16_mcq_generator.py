# -*- coding: utf-8 -*-
"""MCQ GENERATOR AGENT v2 — AI Router powered, 18+ MCQs"""
import re, json, logging

COMMAND = "Generate 15-20 MCQs from verified content."
MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity."

class Agent:
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "MCQ GENERATOR AGENT v2"

    def run(self):
        from pipeline.state import CONTENT_DIR, MCQ_DIR, data_path, read_json, write_json_atomic
        content = read_json(data_path(CONTENT_DIR, self.job_id))
        items = content.get("items", [])
        n_items = len(items)
        logging.info(f"[{self.name}] Generating MCQs for {n_items} items...")
        target_mcqs = {"daily": 18, "weekly": 25, "monthly": 30}.get(self.job_type, 18)
        try:
            from pipeline.ai_router import get_router, chunked
            router = get_router()
            def gen_chunk(chunk):
                mcqs = []
                for item in chunk:
                    mcqs.extend(self._gen_ai(router, item))
                return mcqs
            all_mcqs = chunked(items, gen_chunk, chunk_size=4, delay=4)
        except Exception as e:
            logging.warning(f"[{self.name}] AI Router unavailable ({e}), using deterministic")
            from pipeline.content import generate_mcqs
            all_mcqs = generate_mcqs(items)
        min_mcqs = min(8, n_items)
        if len(all_mcqs) < min_mcqs:
            try:
                from pipeline.content import generate_mcqs
                extra = generate_mcqs(items)
                existing = {m.get("question", "")[:50] for m in all_mcqs}
                for m in extra:
                    if m.get("question", "")[:50] not in existing:
                        all_mcqs.append(m)
            except Exception:
                pass
        if len(all_mcqs) < min_mcqs:
            self.context["stage_failed"] = f"only {len(all_mcqs)} MCQs (need >={min_mcqs})"
            raise RuntimeError(self.context["stage_failed"])
        all_mcqs = all_mcqs[:target_mcqs]
        write_json_atomic(data_path(MCQ_DIR, self.job_id), all_mcqs)
        logging.info(f"[{self.name}] generated {len(all_mcqs)} MCQs")
        self.context["mcqs_generated"] = len(all_mcqs)
        return self.context

    def _gen_ai(self, router, item):
        headline = item.get("headline_en", "")
        key_points = item.get("key_points_en", [])
        static_fact = item.get("static_fact", "")
        content_text = headline + "\n" + "\n".join(key_points)
        if static_fact:
            content_text += f"\nStatic Fact: {static_fact}"
        prompt = f"""Generate exactly 2 MCQs from this content for competitive exams.

CONTENT:
{content_text}

Rules: 4 options (A-D), exactly 1 correct, verbatim from content. Include explanation.

Respond ONLY in JSON array:
[{{"question": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, "correct": "A", "explanation": "...", "type": "direct"}}]"""
        try:
            response = router.generate(prompt, task="mcq")
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                mcqs = json.loads(json_match.group())
                for mcq in mcqs:
                    mcq["source_event_id"] = item.get("event_id", "")
                    mcq["source_headline"] = headline[:100]
                return mcqs
        except Exception as e:
            logging.warning(f"AI MCQ failed: {e}")
        return self._deterministic_mcq(item)

    def _deterministic_mcq(self, item):
        headline = item.get("headline_en", "")
        key_points = item.get("key_points_en", [])
        mcqs = []
        for kp in key_points[:2]:
            numbers = re.findall(r'(?:₹|Rs\.?\s?)[\d,]+(?:\.\d+)?(?:\s?(?:%|crore|lakh|billion|million))?', kp)
            if numbers:
                mcqs.append({
                    "question": f"What figure is mentioned regarding: {headline[:60]}?",
                    "options": {"A": numbers[0], "B": "Not mentioned", "C": "Data unavailable", "D": "None of these"},
                    "correct": "A", "explanation": f"As per news: {kp[:100]}",
                    "type": "direct", "source_event_id": item.get("event_id", ""),
                    "source_headline": headline[:100],
                })
                break
        if len(mcqs) < 2 and headline:
            mcqs.append({
                "question": f"Which relates to: '{headline[:80]}'?",
                "options": {"A": key_points[0][:60] if key_points else "Related topic",
                            "B": "Unrelated scheme", "C": "International body only", "D": "None"},
                "correct": "A", "explanation": f"News: {headline[:100]}",
                "type": "direct", "source_event_id": item.get("event_id", ""),
                "source_headline": headline[:100],
            })
        return mcqs

    def verify(self):
        return not self.context.get("stage_failed")
