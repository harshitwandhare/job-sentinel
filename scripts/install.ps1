#Requires -Version 5.1
# scripts/install.ps1 — one-command local setup for Job Sentinel (Windows PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File scripts\install.ps1
# Safe to run multiple times; never overwrites an existing .env.

$ErrorActionPreference = "Stop"

# ── Resolve repo root from script location ────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# ── Colour helpers ────────────────────────────────────────────────────────────
function Write-Step  { param([string]$Msg) Write-Host "`n── $Msg" -ForegroundColor Cyan }
function Write-Info  { param([string]$Msg) Write-Host "==> $Msg" -ForegroundColor Green }
function Write-Warn  { param([string]$Msg) Write-Host "[warn] $Msg" -ForegroundColor Yellow }
function Write-Err   { param([string]$Msg) Write-Host "[error] $Msg" -ForegroundColor Red }

# ── 1. Python >= 3.11 check ──────────────────────────────────────────────────
Write-Step "Checking Python version"
$PythonExe = $null
foreach ($candidate in @("python3.13", "python3.12", "python3.11", "python3", "python")) {
    $found = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($found) {
        $verStr = & $found.Source -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($verStr -match '^(\d+)\.(\d+)$') {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
                $PythonExe = $found.Source
                break
            }
        }
    }
}

if (-not $PythonExe) {
    Write-Err "Python 3.11 or newer is required but was not found on PATH."
    Write-Err "Install Python 3.11+ from https://python.org/downloads/ and re-run."
    exit 1
}
$pyVer = & $PythonExe --version 2>&1
Write-Info "Found: $pyVer"

# ── 2. Create / reuse .venv ──────────────────────────────────────────────────
Write-Step "Setting up virtual environment"
$VenvDir = Join-Path $RepoRoot ".venv"
if (Test-Path $VenvDir) {
    Write-Info ".venv already exists — reusing it"
} else {
    Write-Info "Creating .venv"
    & $PythonExe -m venv $VenvDir
}
$VenvPy  = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

# ── 3. Upgrade pip ───────────────────────────────────────────────────────────
Write-Step "Upgrading pip"
& $VenvPy -m pip install --quiet --upgrade pip

# ── 4. Install project with web extras ───────────────────────────────────────
Write-Step "Installing job-sentinel[web]"
& $VenvPip install --quiet -e ".[web]"
Write-Info "Core install complete"

# ── 5. Playwright Chromium ───────────────────────────────────────────────────
Write-Step "Installing Playwright Chromium"
& $VenvPy -m playwright install chromium
Write-Info "Chromium browser installed"

# ── 6. .env setup ────────────────────────────────────────────────────────────
Write-Step "Environment file"
$EnvFile    = Join-Path $RepoRoot ".env"
$EnvExample = Join-Path $RepoRoot ".env.example"
if (Test-Path $EnvFile) {
    Write-Info ".env already exists — not overwriting"
} else {
    Copy-Item $EnvExample $EnvFile
    Write-Warn ".env created from .env.example — fill in your credentials before running."
}

# ── 7. Node / web UI ─────────────────────────────────────────────────────────
Write-Step "Web UI (Node.js)"
$npm = Get-Command "npm" -ErrorAction SilentlyContinue
if ($npm) {
    $npmVer = & npm --version 2>&1
    Write-Info "npm found: $npmVer — installing web dependencies"
    & npm --prefix (Join-Path $RepoRoot "web") install
    Write-Info "web/ dependencies installed"
} else {
    Write-Warn "npm not found — skipping web UI install."
    Write-Warn "Install Node.js 18+ from https://nodejs.org, then run:"
    Write-Warn "  npm --prefix web install"
    Write-Warn "(The CLI and API work without Node.)"
}

# ── 8. Next-steps banner ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║             Job Sentinel — setup complete!                   ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Edit " -NoNewline; Write-Host ".env" -ForegroundColor Yellow -NoNewline; Write-Host " with your portal credentials and Telegram tokens."
Write-Host ""
Write-Host "  2. Log in to your job portal (opens a browser window):"
Write-Host "       job-sentinel login" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. Start the full stack (API + web UI):"
Write-Host "       job-sentinel web" -ForegroundColor Cyan
Write-Host "     -> API:    http://127.0.0.1:8000"
Write-Host "     -> Web UI: http://localhost:3000"
Write-Host ""
Write-Host "  Optional extras (install separately when needed):" -ForegroundColor White
Write-Host "    pip install -e `".[sources]`"   # python-jobspy scraper backend"
Write-Host "    pip install -e `".[apify]`"     # Apify cloud-actor integration"
Write-Host ""
Write-Host "  BYO-LLM keys: see " -NoNewline; Write-Host "docs/llm-providers.md" -ForegroundColor Yellow -NoNewline; Write-Host " for Ollama, OpenAI-compat, etc."
Write-Host ""
