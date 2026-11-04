#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Re-verify config/current_facts.json against each entry's official source_url.

For every fact:
  1. Fetch source_url (timeout 25 s).  Unreachable -> the entry is left as is
     and reported ("unreachable"); nothing is guessed.
  2. If the recorded name (or an alias / Hindi name) is on the page -> still
     verified: ``verified_on`` is bumped to today.
  3. Otherwise ask an LLM (pipeline.llm_helper.call_llm) who holds the post
     according to THIS page text only.  The answer is accepted only when the
     returned name appears verbatim on the page (strict check) and the page
     mentions the post.  An accepted change rewrites name/since/aliases and
     clears name_hi (the validator then blanks unverified Hindi names).
     Anything else -> entry kept, reported as "needs review".
  Multi-holder posts (``names``) are only checked, never rewritten by the LLM.

Writes the file only when something changed and prints a Markdown summary
(used as the PR body by .github/workflows/refresh-current-facts.yml).

Usage: python scripts/refresh_current_facts.py [--facts PATH] [--summary PATH] [--no-llm]
Exit code is always 0 unless the facts file itself is unreadable (2).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FACTS = ROOT / "config" / "current_facts.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")


def page_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", raw or "")
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def norm(s: str) -> str:
    s = re.sub(r"^(?:shri|smt|sri|dr|mr|ms|mrs|prof|gen|general|adm|admiral|air chief marshal|justice)\.?\s+", "",
               str(s or "").strip(), flags=re.I)
    return re.sub(r"[^a-z0-9\u0900-\u097f]+", " ", s.lower()).strip()


def on_page(name: str, text: str) -> bool:
    n = norm(name)
    return bool(n) and f" {n} " in f" {norm(text)} "


def default_fetch(url: str) -> Tuple[int, str]:
    import requests
    r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*",
                                   "Accept-Language": "en-US,en;q=0.9"}, timeout=25)
    return r.status_code, r.text


def default_llm(prompt: str) -> str:
    from pipeline.llm_helper import call_llm
    txt, _model = call_llm(prompt)
    return txt or ""


PROMPT = """You read an official web page and report who CURRENTLY holds one post.
Use ONLY the PAGE TEXT below. If the page does not clearly name the current holder, answer null.
POST: {post}
PAGE TEXT (truncated):
{text}

Reply with ONLY JSON: {{"name": "<full name exactly as written on the page>" or null, "since": "<YYYY-MM-DD if stated, else null>"}}"""


def ask_llm(fact: Dict, text: str, llm: Callable[[str], str]) -> Tuple[Optional[str], Optional[str]]:
    # Give the LLM the part of the page around the post words first.
    words = [w for w in re.findall(r"[A-Za-z]{3,}", fact.get("post", "")) if w.lower() not in {"the", "and"}]
    idx = min([i for i in (text.lower().find(w.lower()) for w in words) if i >= 0] or [0])
    snippet = text[max(0, idx - 3000): idx + 5000]
    raw = llm(PROMPT.format(post=fact.get("post"), text=snippet))
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None, None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None, None
    name = data.get("name")
    since = data.get("since")
    if not isinstance(name, str) or not name.strip():
        return None, None
    since = since if isinstance(since, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", since) else None
    return name.strip(), since


def post_on_page(fact: Dict, text: str) -> bool:
    low = text.lower()
    phrases = [fact.get("post", "")] + list(fact.get("match") or [])
    for p in phrases:
        p = p.lower().strip()
        if p and p in low:
            return True
    # loose: every distinctive word of the post somewhere on the page
    ws = [w for w in re.findall(r"[a-z]{4,}", fact.get("post", "").lower()) if w not in {"union", "india"}]
    return bool(ws) and all(w in low for w in ws)


def refresh(facts_doc: Dict, *, fetch: Callable[[str], Tuple[int, str]] = default_fetch,
            llm: Optional[Callable[[str], str]] = default_llm, today: Optional[str] = None) -> Dict[str, List[str]]:
    today = today or dt.date.today().isoformat()
    res: Dict[str, List[str]] = {"verified": [], "changed": [], "unreachable": [], "review": []}
    for f in facts_doc.get("facts") or []:
        fid, url = f.get("id"), f.get("source_url")
        try:
            status, raw = fetch(url)
        except Exception as exc:
            res["unreachable"].append(f"{fid}: {type(exc).__name__}")
            continue
        if status != 200 or not raw:
            res["unreachable"].append(f"{fid}: HTTP {status}")
            continue
        text = page_text(raw)
        names = list(f.get("names") or [])
        if names:
            missing = [n for n in names if not on_page(n, text)]
            if missing:
                res["review"].append(f"{fid}: not on page: {', '.join(missing)}")
            else:
                f["verified_on"] = today
                res["verified"].append(fid)
            continue
        cands = [f.get("name", ""), *(f.get("aliases") or []), f.get("name_hi", "")]
        if any(on_page(c, text) for c in cands if c):
            f["verified_on"] = today
            res["verified"].append(fid)
            continue
        if llm is None:
            res["review"].append(f"{fid}: '{f.get('name')}' not found on page (LLM disabled)")
            continue
        try:
            new, since = ask_llm(f, text, llm)
        except Exception as exc:
            res["review"].append(f"{fid}: LLM failed ({type(exc).__name__})")
            continue
        # STRICT: the LLM's name must be printed on the page, and the page must be about the post.
        if new and on_page(new, text) and post_on_page(f, text) and norm(new) != norm(f.get("name")):
            old = f.get("name")
            f.update({"name": new, "since": since, "aliases": [], "name_hi": "", "verified_on": today})
            res["changed"].append(f"{fid}: {old} -> {new} ({url})")
        else:
            res["review"].append(f"{fid}: '{f.get('name')}' not found on page; LLM answer "
                                 f"{new!r} failed the strict on-page check")
    return res


def summary_md(res: Dict[str, List[str]], today: str) -> str:
    lines = [f"## Current facts refresh — {today}", "",
             f"- verified: {len(res['verified'])}", f"- changed: {len(res['changed'])}",
             f"- unreachable: {len(res['unreachable'])}", f"- needs review: {len(res['review'])}", ""]
    for key, title in (("changed", "Changed (LLM answer confirmed verbatim on the official page)"),
                       ("review", "Needs human review (left unchanged)"), ("unreachable", "Unreachable (left unchanged)")):
        if res[key]:
            lines.append(f"### {title}")
            lines.extend(f"- {x}" for x in res[key])
            lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", default=str(FACTS))
    ap.add_argument("--summary", default="")
    ap.add_argument("--no-llm", action="store_true")
    a = ap.parse_args(argv)
    path = Path(a.facts)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        return 2
    before = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    today = dt.date.today().isoformat()
    res = refresh(doc, llm=None if a.no_llm else default_llm, today=today)
    if res["changed"]:
        doc["updated"] = today
    after = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    if after != before:
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    md = summary_md(res, today)
    print(md)
    if a.summary:
        Path(a.summary).write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
