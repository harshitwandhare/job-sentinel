"""Local HTTP API over the job-sentinel core — the backend the web UI consumes."""

from job_sentinel.api.app import app, create_app

__all__ = ["app", "create_app"]
