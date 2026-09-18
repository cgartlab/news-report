# Copyright (c) 2026 CGArtLab. CC BY-NC-SA 4.0.
# news-report installer — Windows PowerShell
param(
    [switch]$NoVenv
)

$ErrorActionPreference = "Stop"

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📰 news-report v0.3.0 — Installer" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "✗ python not found. Install Python 3.10+ first." -ForegroundColor Red
    exit 1
}
$pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "✓ Python $pyVer" -ForegroundColor Green

# 2. Create venv
if (-not $NoVenv) {
    if (Test-Path ".venv") {
        Write-Host "⚠ Existing .venv found, reusing" -ForegroundColor Yellow
    } else {
        Write-Host "✓ Creating virtual environment..." -ForegroundColor Green
        python -m venv .venv
    }
    & ".venv\Scripts\Activate.ps1"
}

# 3. Install package
Write-Host "✓ Installing news-report..." -ForegroundColor Green
pip install -e . 2>&1 | Select-Object -Last 1
Write-Host "✓ Installed" -ForegroundColor Green

# 4. Setup .env
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item .env.example .env
        Write-Host "⚠ .env created from .env.example — edit with your API keys" -ForegroundColor Yellow
        Write-Host "   Required: SENSENOVA_API_KEY"
        Write-Host "   Optional: SEARXNG_URL, TG_HISTORY_SCRIPT"
    }
}

# 5. Install pre-commit (optional)
$precommit = Get-Command pre-commit -ErrorAction SilentlyContinue
if ($precommit) {
    pre-commit install 2>$null
    Write-Host "✓ Pre-commit hooks installed" -ForegroundColor Green
} else {
    Write-Host "⚠ pre-commit not installed — skip (pip install pre-commit && pre-commit install)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "✓ Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Usage:"
Write-Host "    news-report --full         # Run full pipeline"
Write-Host "    news-report --collect      # Collect only"
Write-Host "    news-report --evaluate     # Evaluate only"
Write-Host "    news-report --report       # Generate report only"
Write-Host ""
Write-Host "  First run:"
Write-Host "    1. Edit .env with your API keys"
Write-Host "    2. news-report --collect    # Test collection"
Write-Host "    3. news-report --full       # Full pipeline"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
