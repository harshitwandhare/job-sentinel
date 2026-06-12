# Job Sentinel — always-on bot image.
#
# Based on the official Playwright Python image so Chromium and all its system
# libraries are already present and version-matched. The résumé LaTeX engine
# (Tectonic) is intentionally NOT installed here — résumé building is a host-side
# CLI workflow; this image is the monitoring/alerting service.
# Pinned by digest (supply-chain reproducibility); the tag comment is the
# human-readable version. Update both together.
FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy@sha256:aaa8048c7a7c414fab6ad809469eb35f13bbf5093038113eef851b3c4814ad77

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install from the committed lockfile for reproducible builds — the same
# resolved versions CI tests against, not a fresh resolution at build time.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN pip install --no-cache-dir uv==0.11.21 && uv sync --locked --no-dev --no-editable
ENV PATH="/app/.venv/bin:$PATH"

# Mount points for durable state (see docker-compose.yml volumes).
RUN mkdir -p /app/data /app/logs

# Runs the scraper + Telegram bot until stopped. Override with e.g.
#   docker compose run --rm job-sentinel scrape
ENTRYPOINT ["job-sentinel"]
CMD ["run"]
