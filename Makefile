# =============================================================================
# AGRI LEARNING POINT — Developer Makefile
# =============================================================================
.PHONY: help install install-dev test test-quick lint format clean run-daily run-weekly run-monthly watchdog preflight migrate docs check

PYTHON ?= python3.11
VENV   ?= .venv
BIN    := $(VENV)/bin

help:  ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip setuptools wheel

install: $(VENV)/bin/activate  ## Install production deps
	$(BIN)/pip install -r requirements.txt

install-dev: install  ## Install dev deps too
	$(BIN)/pip install -r requirements-dev.txt 2>/dev/null || \
		$(BIN)/pip install pytest pytest-cov ruff black mypy bandit
	$(BIN)/pre-commit install 2>/dev/null || true

# -----------------------------------------------------------------------------
# Quality
# -----------------------------------------------------------------------------
test:  ## Run test suite
	$(BIN)/pytest tests/ -v

test-quick:  ## Run fast tests only
	$(BIN)/pytest tests/ -q -m "not slow" --no-header

test-cov:  ## Tests with coverage report
	$(BIN)/pytest tests/ --cov=agents --cov=pipeline --cov-report=term-missing

lint:  ## Lint with ruff
	$(BIN)/ruff check . --select=E,F,W

format:  ## Auto-format with ruff
	$(BIN)/ruff format .
	$(BIN)/ruff check . --fix

check: lint test  ## Lint + test

preflight:  ## Full preflight validation
	./scripts/preflight_check.sh

# -----------------------------------------------------------------------------
# Run pipeline
# -----------------------------------------------------------------------------
run-daily:  ## Run daily pipeline
	$(BIN)/python main.py --job-type daily

run-weekly:  ## Run weekly pipeline
	$(BIN)/python main.py --job-type weekly

run-monthly:  ## Run monthly pipeline
	$(BIN)/python main.py --job-type monthly

watchdog:  ## Run watchdog (stuck-job detector)
	$(BIN)/python main.py --watchdog

migrate:  ## Clean state/jobs.json
	$(BIN)/python maintenance/migrate_state.py --dry-run
	@echo "Run with --reset-failed-final to apply"

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------
clean:  ## Remove Python caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info

clean-data:  ## Remove generated data (careful!)
	rm -rf data/raw data/verified data/dedup data/scored data/selected data/content data/mcq output

clean-all: clean clean-data  ## Everything clean

# -----------------------------------------------------------------------------
# Info
# -----------------------------------------------------------------------------
status:  ## Show pipeline status
	@$(BIN)/python -c "from main import load_state; s=load_state(); \
from collections import Counter; \
c=Counter(j.status for j in s.jobs.values()); \
print(f'Total: {len(s.jobs)} jobs'); \
print(dict(c))"
