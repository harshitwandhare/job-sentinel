# Job Sentinel — always-on bot image.
#
# Based on the official Playwright Python image so Chromium and all its system
# libraries are already present and version-matched. The résumé LaTeX engine
# (Tectonic) is intentionally NOT installed here — résumé building is a host-side
# CLI workflow; this image is the monitoring/alerting service.
FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching), then the package.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

# Mount points for durable state (see docker-compose.yml volumes).
RUN mkdir -p /app/data /app/logs

# Runs the scraper + Telegram bot until stopped. Override with e.g.
#   docker compose run --rm job-sentinel scrape
ENTRYPOINT ["job-sentinel"]
CMD ["run"]
