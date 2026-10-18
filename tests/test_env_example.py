"""Regression tests for configuration-name alignment and settings validation.

The audit found .env.example documented names the code never read
(STAGE_TIMEOUT_SECONDS, WATCHDOG_STUCK_HOURS, MAX_RESPONSE_BYTES, TEST_DATE, ...).
These tests pin the canonical ALP_-prefixed names, forbid the stale active
assignments from creeping back, and verify the legacy aliases still work.
"""
import re
from pathlib import Path

import pytest

import main

ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"

# Names the code actually reads and that operators must be able to configure.
REQUIRED_NAMES = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "ADMIN_ID",
    "DRY_RUN",
    "ALP_STAGE_TIMEOUT",
    "ALP_MAX_RETRIES",
    "ALP_RETRY_BASE_DELAY",
    "ALP_RUNNING_STUCK_HOURS",
    "ALP_FAILED_LOOKBACK_HOURS",
    "ALP_FEED_TIMEOUT",
    "ALP_ALLOW_FALLBACK_TRANSLATION",
    "ALP_ALLOW_UNSHAPED_DEV_PDF",
    "ALP_TRANSLATION_STRICT",
    "ALP_DISABLE_LLM_VERIFY",
    "ALP_DISABLE_POLISH",
    "MIN_CONFIDENCE_THRESHOLD",
    "MIN_VERIFIED_COUNT",
    "AI_ROUTER_TIMEOUT",
    "AI_ROUTER_MAX_CALLS_PER_HOUR",
    "JINA_API_KEY",
    "NEWSDATA_API_KEY",
    "DEDUP_SIMILARITY_THRESHOLD",
]

# Stale active assignments that must not reappear (the legacy alias is documented
# in a comment instead, and honoured by main._int_env/_float_env).
FORBIDDEN_ACTIVE_ASSIGNMENTS = [
    "STAGE_TIMEOUT_SECONDS",
    "MAX_STAGE_RETRIES",
    "WATCHDOG_STUCK_HOURS",
    "MAX_RESPONSE_BYTES",
    "MAX_ARTICLES_PER_SOURCE",
    "NEWS_SOURCES_FILE",
    "TEST_DATE",
]


def _active_assignments(text):
    names = set()
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        match = re.match(r"\s*([A-Z][A-Z0-9_]*)\s*=", line)
        if match:
            names.add(match.group(1))
    return names


def test_env_example_exists_and_declares_canonical_names():
    assert ENV_EXAMPLE.is_file()
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    active = _active_assignments(text)
    missing = [name for name in REQUIRED_NAMES if name not in active]
    assert not missing, f"missing canonical env names: {missing}"


def test_env_example_has_no_stale_active_assignments():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    active = _active_assignments(text)
    stale = sorted(set(FORBIDDEN_ACTIVE_ASSIGNMENTS) & active)
    assert not stale, f"stale env names are active in .env.example: {stale}"


def _quoted_references(name):
    """True when NAME appears as a quoted literal in non-test code or a workflow."""
    pattern = re.compile(rf"""["']{re.escape(name)}["']""")
    root = ENV_EXAMPLE.parent
    for path in list(root.rglob("*.py")) + list(root.rglob("*.yml")):
        # Exclude tests: otherwise this very file would satisfy the lookup for
        # names it merely mentions, defeating the check.
        if any(part in {".git", "__pycache__", ".venv", "venv", "tests"} for part in path.parts):
            continue
        if pattern.search(path.read_text(encoding="utf-8", errors="replace")):
            return True
    return False


def test_every_documented_name_is_actually_read_by_code():
    """A documented-but-unread name is exactly the bug this suite guards against."""
    active = _active_assignments(ENV_EXAMPLE.read_text(encoding="utf-8"))
    orphans = sorted(name for name in active if not _quoted_references(name))
    assert not orphans, f".env.example documents names no code reads: {orphans}"


def test_env_example_placeholder_token_is_not_a_real_secret():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    match = re.search(r"^TELEGRAM_BOT_TOKEN=(.*)$", text, re.M)
    assert match, "TELEGRAM_BOT_TOKEN placeholder missing"
    value = match.group(1).strip()
    assert ":" not in value, "placeholder must not look like a real bot token"


def test_legacy_env_aliases_are_honoured(monkeypatch):
    monkeypatch.delenv("ALP_STAGE_TIMEOUT", raising=False)
    monkeypatch.setenv("STAGE_TIMEOUT_SECONDS", "321")
    assert main._int_env("ALP_STAGE_TIMEOUT", "STAGE_TIMEOUT_SECONDS", 900) == 321

    monkeypatch.delenv("ALP_RUNNING_STUCK_HOURS", raising=False)
    monkeypatch.setenv("WATCHDOG_STUCK_HOURS", "2.5")
    assert main._float_env("ALP_RUNNING_STUCK_HOURS", "WATCHDOG_STUCK_HOURS", 6) == 2.5


def test_prefixed_name_takes_precedence_over_alias(monkeypatch):
    monkeypatch.setenv("ALP_STAGE_TIMEOUT", "42")
    monkeypatch.setenv("STAGE_TIMEOUT_SECONDS", "321")
    assert main._int_env("ALP_STAGE_TIMEOUT", "STAGE_TIMEOUT_SECONDS", 900) == 42


def test_invalid_numeric_setting_fails_loudly(monkeypatch):
    monkeypatch.setenv("ALP_STAGE_TIMEOUT", "abc")
    with pytest.raises(SystemExit) as excinfo:
        main._int_env("ALP_STAGE_TIMEOUT", "STAGE_TIMEOUT_SECONDS", 900)
    assert excinfo.value.code == 2


@pytest.mark.parametrize("attr,value", [
    ("STAGE_TIMEOUT_SECONDS", 0),
    ("STAGE_TIMEOUT_SECONDS", -1),
    ("MAX_RETRIES", -1),
])
def test_validate_settings_rejects_bad_values(monkeypatch, attr, value):
    monkeypatch.setattr(main, attr, value)
    with pytest.raises(SystemExit) as excinfo:
        main.validate_settings("daily")
    assert excinfo.value.code == 2


def test_validate_settings_accepts_defaults(monkeypatch):
    monkeypatch.setattr(main, "STAGE_TIMEOUT_SECONDS", 900)
    monkeypatch.setattr(main, "MAX_RETRIES", 2)
    monkeypatch.setattr(main, "RUNNING_STUCK_HOURS", 6)
    main.validate_settings("daily")  # must not raise
