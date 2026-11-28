"""Central Master Supervisor coordinating PLAN -> EXECUTE -> OBSERVE -> CRITIQUE -> REPAIR -> RETEST -> APPROVE/REJECT."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from pipeline.persistence import file_lock, write_json_atomic

STAGE_STATUS_PASS = "PASS"
STAGE_STATUS_PASS_WITH_LIMITATION = "PASS_WITH_APPROVED_LIMITATION"
STAGE_STATUS_RETRY = "RETRY_REQUIRED"
STAGE_STATUS_REPAIR = "REPAIR_REQUIRED"
STAGE_STATUS_BLOCKED = "BLOCKED"
STAGE_STATUS_FAILED_FINAL = "FAILED_FINAL"

VALID_STAGE_STATUSES = {
    STAGE_STATUS_PASS,
    STAGE_STATUS_PASS_WITH_LIMITATION,
    STAGE_STATUS_RETRY,
    STAGE_STATUS_REPAIR,
    STAGE_STATUS_BLOCKED,
    STAGE_STATUS_FAILED_FINAL,
}


def load_supervisor_policy(root: Path) -> Dict[str, Any]:
    """Load config/supervisor_policy.json with safe deterministic defaults."""
    policy_path = root / "config" / "supervisor_policy.json"
    if policy_path.is_file():
        try:
            data = json.loads(policy_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            pass
    return {
        "version": 1,
        "max_repair_cycles_per_defect": 3,
        "overall_run_deadline_seconds": 3600,
        "stage_contracts": {},
        "critical_sections_by_type": {},
    }


def supervisor_state_path(root: Path, job_id: str) -> Path:
    return root / "logs" / "supervisor" / f"{job_id}.json"


def release_approval_path(root: Path, job_id: str) -> Path:
    return root / "logs" / "qa" / f"{job_id}_release_approval.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_json(path: Path) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return None


@dataclass
class StageCritique:
    stage: str
    status: str
    reasons: List[str] = field(default_factory=list)
    repair_target: Optional[str] = None
    defect_key: Optional[str] = None
    severity: str = "P0"
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "reasons": list(self.reasons),
            "repair_target": self.repair_target,
            "defect_key": self.defect_key,
            "severity": self.severity,
            "metrics": dict(self.metrics),
        }


class MasterSupervisor:
    """Single authoritative lifecycle supervisor embedded into main.py."""

    def __init__(self, root: Path, job_id: str, job_type: str, edition_date: str):
        self.root = Path(root)
        self.job_id = job_id
        self.job_type = job_type
        self.edition_date = edition_date
        self.policy = load_supervisor_policy(self.root)
        self.started_monotonic = datetime.now(timezone.utc).timestamp()
        self.state_path = supervisor_state_path(self.root, job_id)
        self.state = self._load_or_init_state()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "edition_date": self.edition_date,
            "edition_type": self.job_type,
            "current_stage": None,
            "completed_stages": [],
            "pending_stages": [],
            "failed_stages": [],
            "stage_statuses": {},
            "artifact_paths": {},
            "artifact_hashes": {},
            "source_registry": {},
            "claim_verification_status": {},
            "translation_status": {},
            "MCQ_validation_status": {},
            "image_validation_status": {},
            "PDF_QA_status": {},
            "visual_QA_status": {},
            "repair_attempts": {},
            "repair_history": [],
            "API_usage": {},
            "provider_health": {},
            "final_release_decision": {
                "decision": "PENDING",
                "approved": False,
                "reasons": [],
                "decided_at": None,
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _load_or_init_state(self) -> Dict[str, Any]:
        existing = _safe_json(self.state_path)
        base = self._default_state()
        if isinstance(existing, dict) and existing.get("job_id") == self.job_id:
            base.update(existing)
        return base

    def save(self) -> None:
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        lock_path = self.root / "state" / "locks" / f"supervisor_{self.job_id}.lock"
        with file_lock(lock_path):
            write_json_atomic(self.state_path, self.state)

    def deadline_remaining_seconds(self) -> float:
        raw = os.getenv("ALP_SUPERVISOR_RUN_DEADLINE", "").strip()
        try:
            limit = float(raw) if raw else float(self.policy.get("overall_run_deadline_seconds", 3600))
        except ValueError:
            limit = 3600.0
        elapsed = datetime.now(timezone.utc).timestamp() - self.started_monotonic
        return max(0.0, limit - elapsed)

    def max_repairs_for(self, defect_key: str) -> int:
        raw = os.getenv("ALP_MAX_REPAIR_CYCLES", "").strip()
        try:
            if raw:
                return max(0, int(raw))
        except ValueError:
            pass
        return max(0, int(self.policy.get("max_repair_cycles_per_defect", 3)))

    def plan(self, stage_names: List[str], resume_from: Optional[str], artifacts: Dict[str, Any]) -> List[str]:
        """PLAN phase: compute completed/pending stages & invalidate changed upstream paths."""
        if resume_from and resume_from in stage_names:
            idx = stage_names.index(resume_from)
            completed = list(stage_names[: idx + 1])
            pending = list(stage_names[idx + 1 :])
        else:
            completed = []
            pending = list(stage_names)

        # Invalidate downstream stages if a known recorded artifact changed since last observe.
        prev_hashes = dict(self.state.get("artifact_hashes") or {})
        changed_producers: List[str] = []
        for stage_name in list(completed):
            contract = (self.policy.get("stage_contracts") or {}).get(stage_name, {})
            for rel_tpl in contract.get("required_outputs", []):
                rel = rel_tpl.format(job=self.job_id)
                fp = self.root / rel
                prev = prev_hashes.get(rel)
                if prev and (not fp.is_file() or _sha256_file(fp) != prev):
                    changed_producers.append(stage_name)
                    break

        if changed_producers:
            first_changed = min(stage_names.index(s) for s in changed_producers)
            invalidated = self.invalidate_downstream(stage_names, stage_names[first_changed])
            completed = [s for s in completed if s not in set(invalidated)]
            pending = [s for s in stage_names if s not in set(completed)]

        for rel, rec in (artifacts or {}).items():
            if isinstance(rec, dict) and isinstance(rec.get("sha256"), str):
                self.state["artifact_paths"][rel] = str((self.root / rel))
                self.state["artifact_hashes"][rel] = rec["sha256"]

        self.state["completed_stages"] = completed
        self.state["pending_stages"] = pending
        self.save()
        return completed

    def invalidate_downstream(self, stage_names: List[str], changed_stage: str) -> List[str]:
        """Mark changed_stage and all downstream dependent stages pending for rebuild."""
        if changed_stage not in stage_names:
            return []
        start_idx = stage_names.index(changed_stage)
        affected = list(stage_names[start_idx:])
        completed_set = set(self.state.get("completed_stages") or [])
        self.state["completed_stages"] = [s for s in stage_names if s in completed_set and s not in set(affected)]
        self.state["pending_stages"] = affected
        for st in affected:
            self.state.setdefault("stage_statuses", {}).pop(st, None)
        # Invalidate prior release approval whenever pre-publish stages rebuild.
        if start_idx <= stage_names.index("19_pdf_qa") if "19_pdf_qa" in stage_names else True:
            self.state["final_release_decision"] = {
                "decision": "PENDING",
                "approved": False,
                "reasons": [f"invalidated due to rebuild from {changed_stage}"],
                "decided_at": datetime.now(timezone.utc).isoformat(),
            }
            ap_path = release_approval_path(self.root, self.job_id)
            if ap_path.is_file():
                try:
                    ap_path.unlink()
                except OSError:
                    pass
            ap = release_approval_path(self.root, self.job_id)
            if ap.is_file():
                try:
                    ap.unlink()
                except OSError:
                    pass
        self.save()
        return affected

    def _validate_stage_contract(
        self, stage: str, *, strict_files: bool
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Verify actual on-disk artifacts & domain metrics beyond exit code 0."""
        contracts = self.policy.get("stage_contracts") or {}
        contract = contracts.get(stage) or {}
        reasons: List[str] = []
        metrics: Dict[str, Any] = {}

        dry_run = os.getenv("DRY_RUN", "0") == "1"
        required_outputs = list(contract.get("required_outputs", []))
        if dry_run and stage in {"22_telegram_publisher", "23_telegram_pin_verifier"}:
            # Dry-run simulations intentionally avoid writing live publication/pin ledgers.
            required_outputs = []

        if not strict_files:
            # Mocked unit tests stub run_stage + capture without emitting disk files;
            # still validate any real files if the test created them.
            any_real = any(
                (self.root / rel.format(job=self.job_id)).is_file()
                for rel in required_outputs
            )
            if not any_real:
                return reasons, metrics

        for rel_tpl in required_outputs:
            rel = rel_tpl.format(job=self.job_id)
            path = self.root / rel
            if not path.is_file() or path.stat().st_size == 0:
                reasons.append(f"missing or empty required output: {rel}")
                continue
            self.state["artifact_paths"][rel] = str(path)
            self.state["artifact_hashes"][rel] = _sha256_file(path)
            if rel.endswith(".pdf"):
                try:
                    head = path.read_bytes()[:5]
                    if head != b"%PDF-":
                        reasons.append(f"invalid PDF header in {rel}")
                except OSError as exc:
                    reasons.append(f"unreadable PDF {rel}: {exc}")
            elif rel.endswith(".json"):
                parsed = _safe_json(path)
                if parsed is None:
                    reasons.append(f"invalid JSON in {rel}")
                    continue
                min_len = contract.get("min_list_len")
                list_key = contract.get("list_key")
                if min_len is not None:
                    if isinstance(parsed, dict):
                        seq = parsed.get(list_key) if list_key else None
                        if seq is None:
                            for k in ("items", "mcqs", "entries", "articles", "stories"):
                                if isinstance(parsed.get(k), list):
                                    seq = parsed[k]
                                    break
                    else:
                        seq = parsed
                    if not isinstance(seq, list) or len(seq) < int(min_len):
                        reasons.append(f"{rel} has fewer than {min_len} record(s)")
                    else:
                        metrics["record_count"] = len(seq)

        # Stage-specific semantic telemetry & critical section checks
        self._collect_stage_telemetry(stage, reasons, metrics, strict_files=strict_files)
        return reasons, metrics

    def _collect_stage_telemetry(
        self, stage: str, reasons: List[str], metrics: Dict[str, Any], *, strict_files: bool
    ) -> None:
        dry_run = os.getenv("DRY_RUN", "0") == "1"
        offline_ai = os.getenv("AI_ROUTER_DISABLED", "0") == "1"
        allow_fallback_tr = os.getenv("ALP_ALLOW_FALLBACK_TRANSLATION", "0") == "1"

        if stage == "00_model_orchestrator":
            ms = _safe_json(self.root / "state" / "model_status.json")
            if isinstance(ms, dict):
                self.state["provider_health"] = {
                    "status": ms.get("status"),
                    "healthy_count": ms.get("healthy_count", 0),
                    "total_count": ms.get("total_count", 0),
                    "checked_at": ms.get("checked_at"),
                }
            ph = _safe_json(self.root / "logs" / "provider_health.json")
            if isinstance(ph, dict):
                self.state["provider_health"]["slots"] = ph.get("providers", {})

        elif stage == "01_source_fetch":
            raw = _safe_json(self.root / "data" / "raw" / f"{self.job_id}.json")
            if isinstance(raw, dict):
                self.state["source_registry"] = {
                    "sources_enabled": raw.get("sources_enabled", 0),
                    "sources_fetched_ok": raw.get("sources_fetched_ok", 0),
                    "sources_failed": raw.get("sources_failed", 0),
                    "article_count": raw.get("article_count", len(raw.get("articles") or [])),
                }

        elif stage == "04_fact_verification":
            ver = _safe_json(self.root / "data" / "verified" / f"{self.job_id}.json")
            if isinstance(ver, dict):
                items = ver.get("items") or []
                claim_checked = sum(1 for it in items if isinstance(it, dict) and "claim_verification" in it)
                self.state["claim_verification_status"] = {
                    "verified_count": len(items),
                    "claim_checked_count": claim_checked,
                    "stats": ver.get("verification_stats", {}),
                }

        elif stage == "12_content_editor":
            content = _safe_json(self.root / "data" / "content" / f"{self.job_id}.json")
            if isinstance(content, dict):
                items = content.get("items") or []
                needs_rev = sum(1 for it in items if isinstance(it, dict) and it.get("needs_review"))
                self.state["translation_status"] = {
                    "items_count": len(items),
                    "needs_review_count": needs_rev,
                    "translation_stats": content.get("translation_stats", {}),
                    "completeness_passed": (content.get("completeness_report") or {}).get("passed", True),
                }
                if not dry_run and not allow_fallback_tr and items and needs_rev == len(items):
                    reasons.append("all content stories flagged needs_review in strict mode")

        elif stage in {"16_mcq_generator", "17_mcq_validator"}:
            mcqs = _safe_json(self.root / "data" / "mcq" / f"{self.job_id}.json")
            mcq_list = mcqs if isinstance(mcqs, list) else (mcqs.get("mcqs", []) if isinstance(mcqs, dict) else [])
            examiner = _safe_json(self.root / "logs" / "qa" / f"{self.job_id}_mcq_exam.json")
            self.state["MCQ_validation_status"] = {
                "stage": stage,
                "mcq_count": len(mcq_list),
                "examiner": examiner if isinstance(examiner, dict) else {},
            }
            if stage == "17_mcq_validator" and isinstance(examiner, dict) and examiner.get("passed") is False:
                reasons.append("MCQ examiner rejected question set")

        elif stage == "17b_auto_sections":
            content = _safe_json(self.root / "data" / "content" / f"{self.job_id}.json")
            if isinstance(content, dict) and self.job_type == "daily" and strict_files and not dry_run and not offline_ai:
                if os.getenv("ALP_AUTO_SECTIONS", "1") != "0":
                    has_agri = bool((content.get("agri_corner") or {}).get("items"))
                    has_qb = bool(content.get("quick_bites"))
                    metrics["has_agri_corner"] = has_agri
                    metrics["has_quick_bites"] = has_qb
                    if not has_agri and os.getenv("ALP_ALLOW_MISSING_SECTIONS", "0") != "1":
                        reasons.append("daily Agriculture Corner missing after 17b_auto_sections")
                    if not has_qb and os.getenv("ALP_ALLOW_MISSING_SECTIONS", "0") != "1":
                        reasons.append("daily Quick Bites missing after 17b_auto_sections")

        elif stage == "17c_static_gk_validator":
            sgk = _safe_json(self.root / "logs" / "qa" / f"{self.job_id}_static_gk.json")
            if isinstance(sgk, dict):
                metrics["static_gk_validation"] = sgk
                if strict_files and not dry_run and sgk.get("errors") and os.getenv("ALP_ALLOW_MISSING_SECTIONS", "0") != "1":
                    reasons.append(f"static_gk_validator reported errors={sgk.get('errors')}")

        elif stage == "18_pdf_design":
            content = _safe_json(self.root / "data" / "content" / f"{self.job_id}.json")
            if isinstance(content, dict) and isinstance(content.get("image_stats"), dict):
                self.state["image_validation_status"] = content["image_stats"]

        elif stage == "19_pdf_qa":
            qa = _safe_json(self.root / "logs" / "qa" / f"{self.job_id}_qa.json")
            if isinstance(qa, dict):
                self.state["PDF_QA_status"] = {
                    "passed": qa.get("passed"),
                    "pages": qa.get("pages"),
                    "score": qa.get("score"),
                    "file_sha256": qa.get("file_sha256"),
                    "error_count": sum(1 for i in (qa.get("issues") or []) if i.get("severity") == "error"),
                    "warning_count": sum(1 for i in (qa.get("issues") or []) if i.get("severity") == "warning"),
                }
                if qa.get("passed") is not True:
                    reasons.append("19_pdf_qa reported passed=False")
                vis = _safe_json(self.root / "logs" / "qa" / f"{self.job_id}_visual_qa.json")
                if isinstance(vis, dict):
                    self.state["visual_QA_status"] = {
                        "passed": vis.get("passed"),
                        "pages_inspected": vis.get("pages_inspected"),
                        "p0_count": vis.get("p0_count", 0),
                        "p1_count": vis.get("p1_count", 0),
                    }
                    if vis.get("passed") is False:
                        reasons.append("visual QA inspection failed")

        self._refresh_api_usage_summary()

    def _refresh_api_usage_summary(self) -> None:
        ps = _safe_json(self.root / "logs" / "provider_summary.json")
        if isinstance(ps, dict):
            self.state["API_usage"] = ps
            return
        usage_log = Path(os.getenv("ALP_AI_USAGE_LOG") or (self.root / "logs" / "ai_usage.jsonl"))
        if usage_log.is_file():
            try:
                calls = 0
                ok_calls = 0
                for line in usage_log.read_text(encoding="utf-8", errors="replace").splitlines():
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if row.get("job") in ("", self.job_id, None):
                        calls += 1
                        if row.get("ok"):
                            ok_calls += 1
                self.state["API_usage"] = {"calls": calls, "ok": ok_calls, "failed": calls - ok_calls}
            except (OSError, ValueError):
                pass

    def observe_and_critique(
        self,
        stage: str,
        *,
        exit_ok: bool,
        msg: str,
        duration_s: float,
        strict_files: bool,
    ) -> StageCritique:
        """OBSERVE + CRITIQUE phase: classify stage output cleanly and identify repair target."""
        self.state["current_stage"] = stage
        contract_reasons, metrics = self._validate_stage_contract(stage, strict_files=strict_files)
        all_reasons = ([] if exit_ok else [msg]) + contract_reasons
        contracts = self.policy.get("stage_contracts") or {}
        repair_target = (contracts.get(stage) or {}).get("repair_route") or stage
        severity = "P0"

        if stage == "19_pdf_qa":
            qa = _safe_json(self.root / "logs" / "qa" / f"{self.job_id}_qa.json") or {}
            repair_target = self._infer_qa_repair_target(qa) or repair_target

        if not all_reasons:
            status = STAGE_STATUS_PASS
        elif stage in {"17b_auto_sections", "17c_static_gk_validator"} and (
            os.getenv("DRY_RUN", "0") == "1" or os.getenv("ALP_ALLOW_MISSING_SECTIONS", "0") == "1"
        ):
            status = STAGE_STATUS_PASS_WITH_LIMITATION
            severity = "P2"
        elif repair_target and self._can_repair(f"{stage}:{'|'.join(all_reasons[:1])}"):
            status = STAGE_STATUS_REPAIR
        else:
            status = STAGE_STATUS_FAILED_FINAL

        critique = StageCritique(
            stage=stage,
            status=status,
            reasons=all_reasons,
            repair_target=repair_target if status == STAGE_STATUS_REPAIR else None,
            defect_key=f"{stage}:{all_reasons[0][:80]}" if all_reasons else None,
            severity=severity,
            metrics={"duration_s": round(duration_s, 3), **metrics},
        )
        self.state.setdefault("stage_statuses", {})[stage] = critique.to_dict()
        if status in {STAGE_STATUS_PASS, STAGE_STATUS_PASS_WITH_LIMITATION}:
            if stage not in self.state["completed_stages"]:
                self.state["completed_stages"].append(stage)
            self.state["pending_stages"] = [s for s in self.state["pending_stages"] if s != stage]
        else:
            if stage not in self.state["failed_stages"]:
                self.state["failed_stages"].append(stage)
        self.save()
        return critique

    def _infer_qa_repair_target(self, qa: Dict[str, Any]) -> Optional[str]:
        issues = qa.get("issues") or []
        codes = {str(i.get("code") or "") for i in issues}
        if codes & {"stale_qa_report", "qa_hash_mismatch", "missing_qa_report"}:
            return "19_pdf_qa"
        if codes & {
            "broken_mcq_template", "duplicate_questions", "insufficient_mcqs", "missing_answers",
            "mcq_stem_monotony", "agency_recognition_mcq", "dangling_preposition_in_mcq",
            "explanation_dateline_leakage", "answer_key_mismatch", "wrong_mcq_answer",
            "mcq_repeat_from_earlier_edition",
        }:
            return "16_mcq_generator"
        if codes & {
            "story_missing_from_pdf", "title_only_stories", "truncated_dangling_sentence",
            "untranslated_or_english_filler", "clipped_headline", "critical_hindi_defect",
            "missing_content_hi", "corrupt_hindi_unicode", "incomplete_hindi_sentence",
        }:
            return "12_content_editor"
        if codes & {"static_gk_filler_defect", "broken_hindi_grammar"}:
            return "17c_static_gk_validator"
        if codes & {
            "near_empty_pages", "blank_pages", "text_overflow", "excessive_pages",
            "visual_edge_clipping", "visual_blank_pages", "isolated_hindi_matra",
            "corrupt_pdf", "empty_pdf",
        }:
            return "18_pdf_design"
        return "18_pdf_design"

    def preserve_failure_snapshot(self, stage: str, reasons: Iterable[str]) -> Optional[Path]:
        """Archive failed diagnostic state and QA summary before repair overwrites artifacts."""
        fail_dir = self.root / "logs" / "failures"
        try:
            fail_dir.mkdir(parents=True, exist_ok=True)
            qa_path = self.root / "logs" / "qa" / f"{self.job_id}_qa.json"
            qa_snap = _safe_json(qa_path) if qa_path.is_file() else None
            snap_path = fail_dir / f"{self.job_id}_{stage}.json"
            write_json_atomic(snap_path, {
                "job_id": self.job_id,
                "stage": stage,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "reasons": list(reasons)[:10],
                "qa_snapshot": qa_snap,
            })
            return snap_path
        except OSError:
            return None

    def _can_repair(self, defect_key: str) -> bool:
        if self.deadline_remaining_seconds() <= 30.0:
            return False
        used = int((self.state.get("repair_attempts") or {}).get(defect_key, 0))
        return used < self.max_repairs_for(defect_key)

    def record_repair_attempt(self, defect_key: str, target_stage: str, reasons: Iterable[str]) -> int:
        attempts = self.state.setdefault("repair_attempts", {})
        count = int(attempts.get(defect_key, 0)) + 1
        attempts[defect_key] = count
        self.state.setdefault("repair_history", []).append({
            "at": datetime.now(timezone.utc).isoformat(),
            "defect_key": defect_key,
            "target_stage": target_stage,
            "attempt": count,
            "reasons": list(reasons)[:5],
        })
        self.save()
        return count

    def issue_release_decision(self, *, strict_files: bool = True) -> Dict[str, Any]:
        """APPROVE/REJECT phase executed strictly BEFORE 22_telegram_publisher."""
        dry_run = os.getenv("DRY_RUN", "0") == "1"
        pdf_path = self.root / "output" / f"{self.job_id}.pdf"
        qa_path = self.root / "logs" / "qa" / f"{self.job_id}_qa.json"
        vis_path = self.root / "logs" / "qa" / f"{self.job_id}_visual_qa.json"

        reasons: List[str] = []
        pdf_sha = ""
        qa_sha = ""

        if strict_files or qa_path.is_file():
            if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
                reasons.append("missing or empty edition PDF")
            else:
                pdf_sha = _sha256_file(pdf_path)
            if not qa_path.is_file():
                reasons.append("missing Stage 19 PDF QA report")
            else:
                qa = _safe_json(qa_path)
                qa_sha = _sha256_file(qa_path)
                if not isinstance(qa, dict) or qa.get("passed") is not True:
                    reasons.append("Stage 19 PDF QA did not pass")
                elif qa.get("job_id") != self.job_id:
                    reasons.append("PDF QA job_id mismatch")
                elif pdf_sha and qa.get("file_sha256") != pdf_sha:
                    reasons.append("PDF QA hash does not match current PDF")
                else:
                    # Check P0/P1 severity release policy
                    strict_qa = os.getenv("PDF_QA_STRICT", "1" if not dry_run else "0") == "1"
                    for iss in qa.get("issues") or []:
                        sev = str(iss.get("severity") or "").lower()
                        if sev == "error":
                            reasons.append(f"P0 QA error: {iss.get('code')}")
                        elif sev == "warning" and strict_qa:
                            reasons.append(f"P1 QA warning in strict mode: {iss.get('code')}")

            if vis_path.is_file():
                vis = _safe_json(vis_path)
                if not isinstance(vis, dict) or vis.get("passed") is not True:
                    reasons.append("Visual QA gate did not pass")
                elif pdf_sha and vis.get("file_sha256") and vis.get("file_sha256") != pdf_sha:
                    reasons.append("Visual QA hash mismatch")

            # Verify no prior stage ended in FAILED_FINAL or BLOCKED
            for st_name, st_rec in (self.state.get("stage_statuses") or {}).items():
                if st_name.startswith(("22_", "23_", "24_")):
                    continue
                if st_rec.get("status") in {STAGE_STATUS_FAILED_FINAL, STAGE_STATUS_BLOCKED}:
                    reasons.append(f"stage {st_name} status is {st_rec.get('status')}")

        approved = not reasons
        decided_at = datetime.now(timezone.utc).isoformat()
        payload_sig = hashlib.sha256(
            f"{self.job_id}|{pdf_sha}|{qa_sha}|{approved}|{decided_at}".encode("utf-8")
        ).hexdigest()
        record = {
            "job_id": self.job_id,
            "edition_date": self.edition_date,
            "edition_type": self.job_type,
            "approved": approved,
            "decision": "APPROVED" if approved else "REJECTED",
            "reasons": reasons,
            "pdf_sha256": pdf_sha,
            "qa_report_sha256": qa_sha,
            "visual_qa_status": self.state.get("visual_QA_status") or {},
            "structural_qa_status": "PASS" if approved else "FAIL",
            "content_qa_status": "PASS" if approved else "FAIL",
            "mandatory_gates": {
                "pdf_qa": self.state.get("PDF_QA_status") or {},
                "translation": self.state.get("translation_status") or {},
                "mcq": self.state.get("MCQ_validation_status") or {},
            },
            "dry_run": dry_run,
            "decided_at": decided_at,
            "approval_token": payload_sig,
        }
        self.state["final_release_decision"] = record
        self.save()
        if strict_files or qa_path.is_file():
            write_json_atomic(release_approval_path(self.root, self.job_id), record)
        return record


def verify_release_approval(
    root: Path,
    job_id: str,
    pdf_sha256: str,
    qa_report_sha256: str,
    *,
    require_approval_file: bool = False,
) -> Tuple[bool, str]:
    """Independent verification consumed by Stage 22 publisher and Stage 24 audit."""
    path = release_approval_path(Path(root), job_id)
    if not path.is_file():
        if require_approval_file:
            return False, "missing supervisor release approval record"
        return True, "legacy run without supervisor approval file"
    data = _safe_json(path)
    if not isinstance(data, dict):
        return False, "unreadable supervisor release approval record"
    if data.get("job_id") != job_id:
        return False, "release approval job_id mismatch"
    if data.get("approved") is not True or data.get("decision") != "APPROVED":
        return False, f"supervisor rejected release: {data.get('reasons')}"
    if data.get("pdf_sha256") != pdf_sha256:
        return False, "release approval pdf_sha256 mismatch"
    if data.get("qa_report_sha256") != qa_report_sha256:
        return False, "release approval qa_report_sha256 mismatch"
    expected_token = hashlib.sha256(
        f"{job_id}|{pdf_sha256}|{qa_report_sha256}|True|{data.get('decided_at')}".encode("utf-8")
    ).hexdigest()
    if data.get("approval_token") != expected_token:
        return False, "release approval token verification failed"
    return True, "approved"
