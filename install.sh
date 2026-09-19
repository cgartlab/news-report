#!/usr/bin/env bash
# Copyright (c) 2026 CGArtLab. CC BY-NC-SA 4.0.
# news-report installer — Linux/macOS
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

info()  { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
error() { echo -e "${RED}✗${NC} $*" >&2; }

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📰 news-report v0.3.0 — Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Check Python
if ! command -v python3 &>/dev/null; then
    error "python3 not found. Install Python 3.10+ first."
    exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PY_VER"

# 2. Check version
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" || {
    error "Python 3.10+ required (found $PY_VER)"
    exit 1
}

# 3. Create venv
if [ -d ".venv" ]; then
    warn "Existing .venv found, reusing"
else
    info "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# 4. Install package
info "Installing news-report..."
pip install -e . 2>&1 | tail -1
info "Installed"

# 5. Copy config
if [ ! -d "config" ]; then
    warn "config/ directory not found — copy from repo"
fi

# 6. Setup .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        warn ".env created from .env.example — edit with your API keys"
        echo "   Required: SENSENOVA_API_KEY (or other LLM key)"
        echo "   Optional: SEARXNG_URL, TG_HISTORY_SCRIPT"
    fi
fi

# 7. Install pre-commit (optional)
if command -v pre-commit &>/dev/null; then
    pre-commit install 2>/dev/null && info "Pre-commit hooks installed" || warn "Pre-commit install failed"
else
    warn "pre-commit not installed — skip hooks (pip install pre-commit && pre-commit install)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "Installation complete!"
echo ""
echo "  Usage:"
echo "    news-report --full         # Run full pipeline"
echo "    news-report --collect      # Collect only"
echo "    news-report --evaluate     # Evaluate only"
echo "    news-report --report       # Generate report only"
echo "    python src/main.py --help  # All options"
echo ""
echo "  First run:"
echo "    1. Edit .env with your API keys"
echo "    2. news-report --collect    # Test collection"
echo "    3. news-report --full       # Full pipeline"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
