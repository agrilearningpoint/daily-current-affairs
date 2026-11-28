# Self-Healing, Supervision & Learning Policy

Implemented in [`pipeline/supervisor.py`](../pipeline/supervisor.py), [`config/supervisor_policy.json`](../config/supervisor_policy.json), [`agents/25_auto_healer.py`](../agents/25_auto_healer.py), [`agents/26_master_supervisor.py`](../agents/26_master_supervisor.py), and [`pipeline/self_improvement.py`](../pipeline/self_improvement.py).

---

## 1. Bounded Stage Self-Repair (`MasterSupervisor`)

For every stage execution:
1. **PLAN / EXECUTE / OBSERVE:** Records duration, exit status, and artifact SHA-256 checksums.
2. **CRITIQUE:** Validates expected non-empty artifact schemas and domain invariants (e.g., content review status, MCQ count/examiner parity, PDF QA pass status).
3. **BOUNDED REPAIR:** On recoverable defect:
   - Maps defect stage to earliest responsible producer stage via `config/supervisor_policy.json`.
   - Invalidates all downstream checkpoint hashes to prevent stale data reuse.
   - Re-executes up to `max_stage_repairs` (bounded; never enters infinite retry loops).
4. **APPROVE / REJECT:** Fails closed if critical defects remain after bounded repair exhaustion.

---

## 2. Auto-Healer Safety Contract (`agents/25_auto_healer.py`)

- Inspects failure logs and `state/jobs.json` safely in read/append mode for diagnostics.
- **Strict State Preservation:** Never overwrites valid `state/jobs.json` records during recovery triage and maintains full compatibility with checkpoint recovery plans (`recovery_plan.json`).

---

## 3. Bounded Cross-Run Learning (`pipeline/self_improvement.py`)

At the end of every edition audit (`24_final_health_audit`), `record_learning_cycle()` inspects:
- Job pass/fail history (`state/jobs.json`)
- Recent QA issue frequency and Devanagari coverage (`logs/qa/*_qa.json`)
- Provider call error hotspots (`logs/ai_usage.jsonl` / `state/metrics/ai_usage.jsonl`)

Outputs safe operational guidance (`state/metrics/self_improvement_recommendations.json`) and trend metrics (`state/metrics/learning_history.json`) without mutating source code or weakening verification/QA thresholds.
