"""Locks in the code-consolidation decisions recorded in docs/production-audit.md.

Two parallel implementations were removed after proving they had zero
importers, CI references, tool references or documentation contracts:

* ``pipeline/mcq_validator.py``  — duplicate of ``pipeline.content.validate_mcqs``
  (the canonical validator used by agents/16 and agents/17);
* ``pipeline/model_manager_v2.py`` — duplicate AI manager, superseded by
  ``pipeline.ai_router`` (the canonical AI layer used by every agent).

These tests fail if the canonical entry points disappear, or if the duplicate
modules are reintroduced without deleting the consolidation record.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_canonical_mcq_validator_exists():
    from pipeline.content import validate_mcqs
    assert callable(validate_mcqs)


def test_canonical_ai_router_exists():
    from pipeline.ai_router import is_configured, route
    assert callable(route) and callable(is_configured)


@pytest.mark.parametrize("module", ["pipeline.mcq_validator", "pipeline.model_manager_v2"])
def test_duplicate_modules_are_removed(module: str):
    assert not (REPO_ROOT / (module.replace(".", "/") + ".py")).exists(), (
        f"{module} was consolidated away — see docs/production-audit.md. "
        f"If it must return, remove the consolidation record and this test."
    )
    spec = importlib.util.find_spec(module)
    assert spec is None, f"{module} is importable again — consolidation regressed"
