"""Single place for all configuration. Values come from env, with safe defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass


# Credentials editable via /api/settings — stored in the `settings` DB table
# (DB wins over .env fallback). field -> Config attribute the key maps to.
# secret=True -> value masked in GET responses.
SECRET_KEYS: dict[str, dict] = {
    "JOOBLE_API_KEY": {"label": "Jooble API key", "hint": "jooble.org/api/about", "secret": True, "field": "jooble_api_key"},
    "ADZUNA_APP_ID": {"label": "Adzuna App ID", "hint": "developer.adzuna.com", "secret": True, "field": "adzuna_app_id"},
    "ADZUNA_APP_KEY": {"label": "Adzuna App Key", "hint": "developer.adzuna.com", "secret": True, "field": "adzuna_app_key"},
    "ADZUNA_COUNTRY": {"label": "Adzuna market", "hint": "us, gb, pl, de...", "secret": False, "field": "adzuna_country"},
    "USAJOBS_API_KEY": {"label": "USAJOBS API key", "hint": "developer.usajobs.gov", "secret": True, "field": "usajobs_api_key"},
    "USAJOBS_EMAIL": {"label": "USAJOBS email", "hint": "email used in the key request", "secret": True, "field": "usajobs_email"},
}


def _load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader — no external dependency."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Config:
    db_path: str
    user_agent: str
    rate_limit_seconds: float
    request_timeout: float
    jooble_api_key: str | None
    dou_feed_url: str
    workua_feed_url: str
    adzuna_app_id: str | None
    adzuna_app_key: str | None
    adzuna_country: str
    usajobs_api_key: str | None
    usajobs_email: str | None
    djinni_jobs_url: str
    playwright_headless: bool

    # Scam thresholds
    scam_suspicious_at: int = 30
    scam_scam_at: int = 60


def load_config(env_path: str = ".env") -> Config:
    _load_dotenv(env_path)
    return Config(
        db_path=os.getenv("DB_PATH", "jobs.db"),
        user_agent=os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JobScraper/1.0",
        ),
        rate_limit_seconds=float(os.getenv("RATE_LIMIT_SECONDS", "2")),
        request_timeout=float(os.getenv("REQUEST_TIMEOUT", "30")),
        jooble_api_key=os.getenv("JOOBLE_API_KEY") or None,
        dou_feed_url=os.getenv(
            "DOU_FEED_URL", "https://jobs.dou.ua/vacancies/feeds/?search={kw}"
        ),
        workua_feed_url=os.getenv(
            "WORKUA_FEED_URL", "https://www.work.ua/jobs-{kw}/?rss=1"
        ),
        adzuna_app_id=os.getenv("ADZUNA_APP_ID") or None,
        usajobs_api_key=os.getenv("USAJOBS_API_KEY") or None,
        usajobs_email=os.getenv("USAJOBS_EMAIL") or None,
        adzuna_app_key=os.getenv("ADZUNA_APP_KEY") or None,
        adzuna_country=os.getenv("ADZUNA_COUNTRY", "us"),
        djinni_jobs_url=os.getenv(
            "DJINNI_JOBS_URL", "https://djinni.co/jobs/?keywords={kw}"
        ),
        playwright_headless=os.getenv("PLAYWRIGHT_HEADLESS", "true").lower()
        != "false",
    )
