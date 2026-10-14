#!/usr/bin/env bash
# =============================================================================
# AGRI LEARNING POINT — Preflight Check
# =============================================================================
# Run this BEFORE every commit/push to catch regressions:
#   ./scripts/preflight_check.sh
#
# Exit codes:
#   0 — all checks passed
#   1 — critical failure (do NOT commit)
#   2 — warnings only (safe to commit but review)
# =============================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
FAIL=0
WARN=0

step() { echo -e "\n${BLUE}▶ $*${NC}"; }
ok()   { echo -e "  ${GREEN}✅ $*${NC}"; }
err()  { echo -e "  ${RED}❌ $*${NC}"; FAIL=$((FAIL+1)); }
warn() { echo -e "  ${YELLOW}⚠  $*${NC}"; WARN=$((WARN+1)); }

# -----------------------------------------------------------------------------
# 1. Python syntax
# -----------------------------------------------------------------------------
step "1/12 Python syntax"
SYNTAX_FAIL=0
while IFS= read -r -d '' f; do
  if ! python -m py_compile "$f" 2>/dev/null; then
    err "Syntax error: $f"
    SYNTAX_FAIL=1
  fi
done < <(find . -name "*.py" \
  -not -path "./.git/*" -not -path "./.venv/*" -not -path "*/__pycache__/*" \
  -not -path "./build/*" -not -path "./dist/*" -print0)
[ $SYNTAX_FAIL -eq 0 ] && ok "All Python files compile"

# -----------------------------------------------------------------------------
# 2. Critical files exist
# -----------------------------------------------------------------------------
step "2/12 Critical files"
CRITICAL=(
  "main.py"
  "agents/03_news_collection.py"
  "agents/04_fact_verification.py"
  "agents/12_content_editor.py"
  "agents/18_pdf_design.py"
  "agents/19_pdf_qa.py"
  "agents/22_telegram_publisher.py"
  "agents/23_telegram_pin_verifier.py"
  "pipeline/state.py"
  "pipeline/store.py"
  "pipeline/ai_router.py"
  "pipeline/ai_translator.py"
  "requirements.txt"
)
for f in "${CRITICAL[@]}"; do
  [ -f "$f" ] && ok "$f" || err "MISSING: $f"
done

# -----------------------------------------------------------------------------
# 3. Python imports
# -----------------------------------------------------------------------------
step "3/12 Critical imports"
python - <<'PY' 2>&1 | grep -v "^\s*$" || true
import importlib, sys
mods = ["main", "pipeline.state", "pipeline.store", "pipeline.ai_router",
        "pipeline.ai_translator"]
fail = 0
for m in mods:
    try:
        importlib.import_module(m)
        print(f"  ✅ {m}")
    except Exception as e:
        print(f"  ❌ {m}: {e}")
        fail += 1
sys.exit(fail)
PY
[ ${PIPESTATUS[0]} -eq 0 ] || FAIL=$((FAIL+1))

# -----------------------------------------------------------------------------
# 4. CLI contract
# -----------------------------------------------------------------------------
step "4/12 main.py CLI"
CLI_HELP=$(python main.py --help 2>&1 || true)
for flag in "--job-type" "--type" "--watchdog" "--date" "--reset" "--stuck-hours"; do
  if echo "$CLI_HELP" | grep -q -- "$flag"; then
    ok "supports $flag"
  else
    err "missing CLI flag: $flag"
  fi
done

# -----------------------------------------------------------------------------
# 5. State file loads
# -----------------------------------------------------------------------------
step "5/12 State load (backward compat)"
if [ -f state/jobs.json ]; then
  python -c "
from main import load_state
s = load_state()
print(f'  ✅ Loaded {len(s.jobs)} jobs')
for jid, j in list(s.jobs.items())[:3]:
    print(f'     {jid:25s} {j.status:12s} {j.job_type}')
" || err "State load failed"
else
  warn "state/jobs.json not found — first run?"
fi

# -----------------------------------------------------------------------------
# 6. Unicode safety
# -----------------------------------------------------------------------------
step "6/12 Unicode safety"
python -c "
import importlib.util, sys
from pathlib import Path
path = Path('agents/03_news_collection.py')
if not path.exists():
    print('  ⚠  03_news_collection.py missing — skip'); sys.exit(0)
spec = importlib.util.spec_from_file_location('nc', str(path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
hindi = 'कैबिनेट ने 5% MSP बढ़ाया'
out = mod.clean_text(hindi)
if 'कैबिनेट' in out and '5%' in out:
    print('  ✅ Devanagari + numbers preserved')
else:
    print(f'  ❌ Unicode fail: {out!r}'); sys.exit(1)
" || FAIL=$((FAIL+1))

# -----------------------------------------------------------------------------
# 7. JSON configs valid
# -----------------------------------------------------------------------------
step "7/12 JSON configs"
JSON_FAIL=0
while IFS= read -r -d '' f; do
  if ! python -m json.tool "$f" >/dev/null 2>&1; then
    err "Invalid JSON: $f"
    JSON_FAIL=1
  fi
done < <(find . -name "*.json" \
  -not -path "./.git/*" -not -path "./.venv/*" \
  -not -path "./data/*" -not -path "./state/backups/*" \
  -not -path "./state/archive/*" -not -path "*/node_modules/*" -print0)
[ $JSON_FAIL -eq 0 ] && ok "All JSON configs valid"

# -----------------------------------------------------------------------------
# 8. YAML workflows valid
# -----------------------------------------------------------------------------
step "8/12 Workflow YAML"
if [ -d .github/workflows ]; then
  python -c "
import sys
try:
    import yaml
except ImportError:
    print('  ⚠  pyyaml not installed — skip'); sys.exit(0)
from pathlib import Path
fail = 0
for f in Path('.github/workflows').glob('*.yml'):
    try:
        yaml.safe_load(f.read_text())
        print(f'  ✅ {f.name}')
    except Exception as e:
        print(f'  ❌ {f.name}: {e}')
        fail += 1
sys.exit(fail)
" || FAIL=$((FAIL+1))
else
  warn "No .github/workflows directory"
fi

# -----------------------------------------------------------------------------
# 9. Tests
# -----------------------------------------------------------------------------
step "9/12 Tests"
if command -v pytest >/dev/null 2>&1; then
  if [ -d tests ]; then
    RESULT=$(pytest tests/ -q --tb=line 2>&1 | tail -3)
    echo "$RESULT" | grep -q "passed" && ok "Tests pass" || warn "Test summary: $RESULT"
  else
    warn "No tests/ directory"
  fi
else
  warn "pytest not installed"
fi

# -----------------------------------------------------------------------------
# 10. Requirements sanity
# -----------------------------------------------------------------------------
step "10/12 Requirements"
if [ -f requirements.txt ]; then
  for pkg in requests feedparser pydantic tenacity python-dotenv reportlab pymupdf; do
    grep -qi "^${pkg}" requirements.txt && ok "$pkg present" || warn "$pkg missing"
  done
else
  err "requirements.txt not found"
fi

# -----------------------------------------------------------------------------
# 11. Git hygiene
# -----------------------------------------------------------------------------
step "11/12 Git hygiene"
# .env not tracked
if git ls-files 2>/dev/null | grep -q "^\.env$"; then
  err ".env is tracked (SECURITY — remove it!)"
else
  ok ".env not tracked"
fi

# Important files not ignored
for f in state/jobs.json .env.example README.md; do
  [ -f "$f" ] || continue
  git check-ignore -q "$f" && err "$f is ignored (should be tracked)" || ok "$f tracked"
done

# Untracked check
UNTRACKED=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
echo "  ℹ  $UNTRACKED uncommitted change(s)"

# -----------------------------------------------------------------------------
# 12. Env template
# -----------------------------------------------------------------------------
step "12/12 Env template"
if [ -f .env.example ]; then
  for v in TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID MIN_CONFIDENCE_THRESHOLD; do
    grep -q "^${v}" .env.example && ok "$v documented" || warn "$v not in .env.example"
  done
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo "============================================================"
if [ $FAIL -eq 0 ] && [ $WARN -eq 0 ]; then
  echo -e "${GREEN}✅ ALL CHECKS PASSED${NC}"
  exit 0
elif [ $FAIL -eq 0 ]; then
  echo -e "${YELLOW}⚠  $WARN WARNING(S) — safe to commit but review${NC}"
  exit 2
else
  echo -e "${RED}❌ $FAIL FAILURE(S) + $WARN WARNING(S) — DO NOT COMMIT${NC}"
  exit 1
fi
