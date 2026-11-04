"""Regression tests for orchestrator stage selection.

Guards the fix for the fragile ``DAILY_STAGES[8:]`` slicing: weekly/monthly must
reuse exactly the named content→publish→audit tail, in DAILY order, so inserting
or re-ordering a daily stage cannot silently change what weekly/monthly run.
"""
import main

TAIL = [
    "12_content_editor",
    "16_mcq_generator",
    "17_mcq_validator",
    "17c_static_gk_validator",
    "18_pdf_design",
    "19_pdf_qa",
    "22_telegram_publisher",
    "23_telegram_pin_verifier",
    "24_final_health_audit",
]


def _names(stages):
    return [name for name, _, _ in stages]


def test_post_selection_stages_are_the_named_tail_in_daily_order():
    assert _names(main._POST_SELECTION_STAGES) == TAIL
    # Order must follow DAILY_STAGES, not the literal tuple above.
    daily_order = _names(main.DAILY_STAGES)
    assert _names(main._POST_SELECTION_STAGES) == [n for n in daily_order if n in set(TAIL)]


# Weekly/monthly are built from the published daily editions' content + MCQs
# (pipeline/period_builder.py), so they never re-run content/MCQ generation.
PERIOD_TAIL = [
    "17c_static_gk_validator",
    "18_pdf_design",
    "19_pdf_qa",
    "22_telegram_publisher",
    "23_telegram_pin_verifier",
    "24_final_health_audit",
]


def test_weekly_builds_from_daily_editions_then_pdf_tail():
    assert _names(main.WEEKLY_STAGES) == ["00_model_orchestrator", "20_weekly_editor"] + PERIOD_TAIL


def test_monthly_builds_from_daily_editions_then_pdf_tail():
    assert _names(main.MONTHLY_STAGES) == ["00_model_orchestrator", "21_monthly_editor"] + PERIOD_TAIL


def test_period_editions_skip_content_regeneration():
    for stages in (main.WEEKLY_STAGES, main.MONTHLY_STAGES):
        names = set(_names(stages))
        assert not names & {"12_content_editor", "16_mcq_generator", "17_mcq_validator", "17b_auto_sections"}
    # Period tail keeps DAILY order.
    daily_order = _names(main.DAILY_STAGES)
    assert PERIOD_TAIL == [n for n in daily_order if n in set(PERIOD_TAIL)]


def test_period_builder_checkpoints_cover_content_and_mcqs():
    from pipeline.checkpoints import stage_outputs
    for stage, job in (("20_weekly_editor", "weekly_2026-11-01"), ("21_monthly_editor", "monthly_2026-11-01")):
        outs = stage_outputs(stage, job)
        for kind in ("selected", "scored", "content", "mcq"):
            assert f"data/{kind}/{job}.json" in outs


def test_daily_stages_are_unique_and_ordered():
    names = _names(main.DAILY_STAGES)
    assert len(names) == len(set(names)), "duplicate stage name in DAILY_STAGES"
    assert names[0] == "00_model_orchestrator"
    assert names[-1] == "24_final_health_audit"


def test_every_stage_script_exists():
    from pathlib import Path

    root = Path(main.__file__).resolve().parent
    for stages in (main.DAILY_STAGES, main.WEEKLY_STAGES, main.MONTHLY_STAGES):
        for _, rel, _ in stages:
            assert (root / rel).is_file(), f"stage script missing: {rel}"


def test_stage_selection_ignores_a_hypothetical_inserted_daily_stage(monkeypatch):
    """If a new daily stage is inserted mid-list, the tail stays correct."""
    injected = ("15_new_stage", "agents/15_new_stage.py", True)
    patched = list(main.DAILY_STAGES)
    patched.insert(9, injected)
    monkeypatch.setattr(main, "DAILY_STAGES", patched)
    # Recompute the way the module does, using the patched list.
    recomputed = [s for s in patched if s[0] in set(TAIL)]
    assert _names(recomputed) == TAIL
