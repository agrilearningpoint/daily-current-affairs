# -*- coding: utf-8 -*-
"""NEWS COLLECTION AGENT v2 — Extended 200+ items for 15+ pages"""
import hashlib, logging
from datetime import datetime
import pytz

COMMAND = "Collect current-affairs news for 15+ page coverage."
MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity."

class Agent:
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "NEWS COLLECTION AGENT v2"

    def run(self):
        from pipeline.collector import collect_all, collect_window, in_window
        from pipeline.state import RAW_DIR, data_path, write_json_atomic
        max_items = {"daily": 200, "weekly": 300, "monthly": 400}.get(self.job_type, 200)
        items, errors = collect_all(max_items=max_items, job_type=self.job_type)
        start, end = collect_window(self.job_type, self.context["job_date"])
        self.context["window_start"] = start.isoformat()
        self.context["window_end"] = end.isoformat()
        fresh = [i for i in items if in_window(i, start, end)]
        try:
            from pipeline.ai_router import collect_news
            logging.info(f"[{self.name}] Fetching NewsData.io...")
            en_news = collect_news("agriculture OR banking OR economy OR government India", language="en", country="in", limit=50)
            hi_news = collect_news("कृषि OR बैंकिंग OR अर्थव्यवस्था OR सरकार", language="hi", country="in", limit=30)
            for article in en_news + hi_news:
                item = self._convert_newsdata(article)
                if item and item["source_url"] not in {i["source_url"] for i in fresh}:
                    fresh.append(item)
            logging.info(f"[{self.name}] NewsData: +{len(en_news) + len(hi_news)} items")
        except Exception as e:
            logging.warning(f"[{self.name}] NewsData unavailable: {e}")
        try:
            from pipeline.collector import core_coverage_report
            cov = core_coverage_report(fresh)
            logging.info(f"[{self.name}] CORE: {cov['covered']}/{cov['attempted']} ({cov['coverage_ratio']:.0%})")
        except Exception:
            pass
        logging.info(f"[{self.name}] collected={len(items)} in-window={len(fresh)}")
        min_items = {"daily": 30, "weekly": 50, "monthly": 70}.get(self.job_type, 30)
        if len(fresh) < min_items:
            self.context["stage_failed"] = f"only {len(fresh)} items (min {min_items})"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(RAW_DIR, self.job_id), {"items": fresh, "errors": errors})
        return self.context

    def _convert_newsdata(self, article):
        TZ = pytz.timezone("Asia/Kolkata")
        title = (article.get("title") or "").strip()
        link = (article.get("link") or "").strip()
        if not title or not link:
            return None
        pub_date = None
        pub_str = article.get("pubDate") or article.get("published_date")
        if pub_str:
            try:
                from dateutil import parser as dtparser
                pub_date = dtparser.parse(pub_str)
                if pub_date.tzinfo is None:
                    pub_date = pytz.utc.localize(pub_date)
                pub_date = pub_date.astimezone(TZ)
            except Exception:
                pass
        norm_title = title.lower()[:60]
        date_key = pub_date.strftime("%Y-%m-%d") if pub_date else ""
        eid = hashlib.sha1(f"{norm_title}|{date_key}".encode()).hexdigest()[:16]
        from pipeline.collector import infer_category
        category = infer_category(title + " " + (article.get("description") or ""))
        return {
            "event_id": eid, "headline_en": title,
            "pub_time_ist": pub_date.isoformat() if pub_date else None,
            "source_name": article.get("source_name", "NewsData"),
            "source_url": link, "source_tier": "tier2", "source_level": 4,
            "priority_score": 80, "verification_required": True,
            "category": category, "raw_facts": (article.get("description") or "")[:600],
            "image_url": article.get("image_url", ""),
            "needs_primary_verification": True, "discovery_role": "discovery",
            "collected_at": datetime.now(TZ).isoformat(),
            "language": article.get("language", "en"),
        }

    def verify(self):
        return not self.context.get("stage_failed")
