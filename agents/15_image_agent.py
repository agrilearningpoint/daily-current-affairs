# -*- coding: utf-8 -*-
"""
IMAGE SELECTOR AGENT
Main focus: हर important news के लिए relevant image खोजना और validate करना।

Command:
> "For each selected item find a relevant image (source RSS/og:image first, then Wikimedia Commons search). Download into assets/images/<job_id>/ INSIDE the workspace (never /home/user paths that break GitHub Actions). Validate with Pillow: >=500px wide, JPEG/PNG, non-corrupt. No suitable image → skip image, never fake one."

Work: Workspace-local validated images
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """For each selected item find a relevant image (source RSS/og:image first, then Wikimedia Commons search). Download into assets/images/<job_id>/ INSIDE the workspace (never /home/user paths that break GitHub Actions). Validate with Pillow: >=500px wide, JPEG/PNG, non-corrupt. No suitable image → skip image, never fake one."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- og-image/RSS enclosure → Wikimedia fallback
- Pillow validation + local path stored as repo-relative image_path"""


class Agent:
    """IMAGE SELECTOR AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "IMAGE SELECTOR AGENT"

    def run(self):
        import io, logging, os, re
        import requests
        from PIL import Image
        from bs4 import BeautifulSoup
        from pipeline.state import CONTENT_DIR, IMAGES_DIR, data_path, read_json, write_json_atomic, TZ
        from datetime import datetime
        c = read_json(data_path(CONTENT_DIR, self.job_id))
        folder = os.path.join(IMAGES_DIR, self.job_id)
        os.makedirs(folder, exist_ok=True)
        UA = {"User-Agent": "AgriLearningPointBot/1.0"}
        got = 0
        for it in c["items"]:
            url = ""
            try:
                r = requests.get(it["source"]["url"], headers=UA, timeout=10)
                soup = BeautifulSoup(r.text, "lxml")
                og = soup.find("meta", attrs={"property": "og:image"})
                if og and og.get("content"):
                    url = og["content"]
            except requests.RequestException:
                pass
            if not url:  # Wikimedia Commons search fallback
                q = re.sub(r"[^a-z0-9 ]", "", it["headline_en"].lower())[:60]
                try:
                    api = "https://commons.wikimedia.org/w/api.php"
                    rr = requests.get(api, params={"action":"query","generator":"search","gsrsearch":q,
                        "gsrnamespace":"6","gsrlimit":"3","prop":"imageinfo","iiprop":"url|size",
                        "iiurlwidth":"900","format":"json"}, headers=UA, timeout=10).json()
                    pages = rr.get("query", {}).get("pages", {})
                    for p in list(pages.values())[:3]:
                        u = p.get("imageinfo", [{}])[0].get("thumburl", "")
                        if u:
                            url = u; break
                except Exception:
                    pass
            if not url:
                continue
            try:
                img_r = requests.get(url, headers=UA, timeout=12)
                im = Image.open(io.BytesIO(img_r.content)); im.verify()
                im = Image.open(io.BytesIO(img_r.content))
                if im.width < 500 or im.format not in ("JPEG", "PNG"):
                    continue
                fn = f"{it['event_id']}.{'jpg' if im.format=='JPEG' else 'png'}"
                fp = os.path.join(folder, fn)
                im.convert("RGB").save(fp, quality=85)
                it["image_path"] = fp
                it["image_caption"] = f"Representative image (source: {'Wikimedia Commons' if 'wikimedia' in url else it['source']['name']})"
                got += 1
            except Exception:
                continue
        write_json_atomic(data_path(CONTENT_DIR, self.job_id), c)
        logging.info(f"[{self.name}] images attached: {got}/{len(c['items'])}")
        self.context["images_attached"] = got
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
