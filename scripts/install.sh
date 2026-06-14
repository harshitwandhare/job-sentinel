#!/usr/bin/env bash
# scripts/install.sh — one-command local setup for Job Sentinel (macOS / Linux)
# Usage: bash scripts/install.sh
# Safe to run multiple times; never overwrites an existing .env.
set -euo pipefail

# ── Resolve repo root from script location ────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# ── Colour helpers ────────────────────────────────────────────────────────────
bold=$'\033[1m'
green=$'\033[0;32m'
yellow=$'\033[0;33m'
red=$'\033[0;31m'
reset=$'\033[0m'

info()    { printf "%s==>%s %s\n"  "${bold}${green}"  "${reset}" "$*"; }
warn()    { printf "%s[warn]%s %s\n" "${bold}${yellow}" "${reset}" "$*"; }
error()   { printf "%s[error]%s %s\n" "${bold}${red}"  "${reset}" "$*" >&2; }
step()    { printf "\n%s──────────────────────────────────────────────────%s\n" "${bold}" "${reset}"; info "$*"; }

# ── 1. Python ≥ 3.11 check ───────────────────────────────────────────────────
step "Checking Python version"
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "${candidate}" &>/dev/null; then
        version_str=$("${candidate}" -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null || true)
        major="${version_str%%.*}"
        minor="${version_str##*.}"
        if [[ "${major}" -gt 3 ]] || { [[ "${major}" -eq 3 ]] && [[ "${minor}" -ge 11 ]]; }; then
            PYTHON="${candidate}"
            break
        fi
    fi
done

if [[ -z "${PYTHON}" ]]; then
    error "Python 3.11 or newer is required but was not found on PATH."
    error "Install Python 3.11+ from https://python.org/downloads/ and re-run."
    exit 1
fi
info "Found: $(${PYTHON} --version)"

# ── 2. Create / reuse .venv ───────────────────────────────────────────────────
step "Setting up virtual environment"
VENV="${REPO_ROOT}/.venv"
if [[ -d "${VENV}" ]]; then
    info ".venv already exists — reusing it"
else
    info "Creating .venv with ${PYTHON}"
    "${PYTHON}" -m venv "${VENV}"
fi
PY="${VENV}/bin/python"
PIP="${VENV}/bin/pip"

# ── 3. Upgrade pip ───────────────────────────────────────────────────────────
step "Upgrading pip"
"${PY}" -m pip install --quiet --upgrade pip

# ── 4. Install project with web extras ───────────────────────────────────────
step "Installing job-sentinel[web]"
"${PIP}" install --quiet -e ".[web]"
info "Core install complete"

# ── 5. Playwright Chromium ───────────────────────────────────────────────────
step "Installing Playwright Chromium"
"${PY}" -m playwright install chromium
info "Chromium browser installed"

# ── 6. .env setup ────────────────────────────────────────────────────────────
step "Environment file"
if [[ -f "${REPO_ROOT}/.env" ]]; then
    info ".env already exists — not overwriting"
else
    cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
    warn ".env created from .env.example — fill in your credentials before running."
fi

# ── 7. Node / web UI ─────────────────────────────────────────────────────────
step "Web UI (Node.js)"
if command -v npm &>/dev/null; then
    info "npm found: $(npm --version) — installing web dependencies"
    # `npm ci` installs the exact locked versions from package-lock.json
    # (reproducible + pinned) rather than re-resolving like `npm install`.
    npm --prefix "${REPO_ROOT}/web" ci
    info "web/ dependencies installed"
else
    warn "npm not found — skipping web UI install."
    warn "Install Node.js 18+ from https://nodejs.org, then run:"
    warn "  npm --prefix web ci"
    warn "(The CLI and API work without Node.)"
fi

# ── 8. Next-steps banner ─────────────────────────────────────────────────────
printf "\n%s╔══════════════════════════════════════════════════════════════╗%s\n" "${bold}${green}" "${reset}"
printf "%s║             Job Sentinel — setup complete!                   ║%s\n" "${bold}${green}" "${reset}"
printf "%s╚══════════════════════════════════════════════════════════════╝%s\n\n" "${bold}${green}" "${reset}"

printf "  ${bold}Next steps:${reset}\n\n"
printf "  1. Edit ${bold}.env${reset} with your portal credentials and Telegram tokens.\n\n"
printf "  2. Log in to your job portal (opens a browser window):\n"
printf "     ${bold}job-sentinel login${reset}\n\n"
printf "  3. Start the full stack (API + web UI):\n"
printf "     ${bold}job-sentinel web${reset}\n"
printf "     → API:    http://127.0.0.1:8000\n"
printf "     → Web UI: http://localhost:3000\n\n"
printf "  ${bold}Optional extras${reset} (install separately when needed):\n"
printf "    pip install -e \".[sources]\"   # python-jobspy scraper backend\n"
printf "    pip install -e \".[apify]\"     # Apify cloud-actor integration\n\n"
printf "  ${bold}BYO-LLM keys${reset}: see ${bold}docs/llm-providers.md${reset} for Ollama, OpenAI-compat, etc.\n\n"
