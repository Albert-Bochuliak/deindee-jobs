"""FastAPI entrypoint. Run: uvicorn app.api.server:app --reload --port 8000"""
from __future__ import annotations

import hmac
import logging
import os
import secrets
import threading
import time
from dataclasses import asdict, replace

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import SECRET_KEYS, load_config
from contextlib import asynccontextmanager

from app.filters.registry import build_rules
from app.models import SearchQuery
from app.parsing.normalize import Normalizer
from app.services.pipeline import ScraperService
from app.services.scoring import FilterPipeline
from app.sources.registry import build_sources
from app.storage.sqlite_repo import SqliteJobRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

config = load_config()
repository = SqliteJobRepository(config.db_path)
# Live job results are per-run and RAM-only (:memory: SQLite) — a mass
# product must not grow jobs.db on every scrape. The file repo stays for
# settings/blacklist (persistent admin data). Same class => all the
# query_builder filters work unchanged, just on ephemeral data.
jobs_repository = SqliteJobRepository(":memory:")


def _effective_config():
    """env config + DB settings overlay — a saved row always wins, even empty."""
    cfg = load_config()
    saved = repository.all_settings()
    overrides = {
        meta["field"]: (saved[k] or None)
        for k, meta in SECRET_KEYS.items()
        if k in saved
    }
    return replace(cfg, **overrides) if overrides else cfg


def _build_scraper(cfg) -> ScraperService:
    """Construct the service from a config snapshot — re-run after settings change."""
    return ScraperService(
        sources=build_sources(cfg),
        normalizer=Normalizer(),
        pipeline=FilterPipeline(build_rules(), cfg),
        repository=jobs_repository,
    )


config = _effective_config()
scraper = _build_scraper(config)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield
    # reload/exit must retire the shared Chromium on its owning thread —
    # skipping this leaks a browser+worker per reload. Skipped when a
    # scrape holds the lock: close() would block behind in-flight fetches.
    if _scrape_lock.acquire(blocking=False):
        try:
            scraper.close()
        finally:
            _scrape_lock.release()


app = FastAPI(title="Job Scraper API", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_scrape_lock = threading.Lock()
_stop_event = threading.Event()
_last_report: dict | None = None
_scrape_status = {"running": False, "new": 0, "stopped": False}


class ScrapeRequest(BaseModel):
    keywords: str = ""
    location: str = ""
    remote_only: bool = False
    limit_per_source: int = 50


class SettingsUpdate(BaseModel):
    values: dict[str, str]


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    current: str
    new: str


# --- admin auth: in-memory sessions behind an HttpOnly cookie ------------
ADMIN_COOKIE = "admin_session"
SESSION_TTL_S = 8 * 3600
_sessions: dict[str, float] = {}  # token -> expiry epoch


def _require_admin(request: Request) -> None:
    token = request.cookies.get(ADMIN_COOKIE) or ""
    exp = _sessions.get(token, 0.0)
    if exp < time.time():
        _sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="admin auth required")


def _admin_creds() -> tuple[str, str]:
    """Admin login/password — DB row wins, .env is only bootstrap fallback."""
    load_config()  # re-reads .env in case it changed since boot
    user = (
        repository.get_setting("ADMIN_USER")
        or os.getenv("ADMIN_USER")
        or "admin"
    )
    pw = (
        repository.get_setting("ADMIN_PASSWORD")
        or os.getenv("ADMIN_PASSWORD")
        or ""
    )
    return user, pw


@app.post("/api/admin/login")
def admin_login(req: LoginRequest, response: Response) -> dict:
    expected_user, expected_pass = _admin_creds()
    if not expected_pass:
        raise HTTPException(
            status_code=403,
            detail="admin disabled — set ADMIN_PASSWORD in .env",
        )
    ok = hmac.compare_digest(
        req.username, expected_user
    ) and hmac.compare_digest(req.password, expected_pass)
    if not ok:
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = secrets.token_urlsafe(32)
    _sessions[token] = time.time() + SESSION_TTL_S
    # NOTE: secure=True once the site is served over HTTPS
    response.set_cookie(
        ADMIN_COOKIE, token, httponly=True, samesite="lax",
        max_age=SESSION_TTL_S,
    )
    return {"status": "ok"}


@app.post("/api/admin/logout")
def admin_logout(request: Request, response: Response) -> dict:
    _sessions.pop(request.cookies.get(ADMIN_COOKIE) or "", None)
    response.delete_cookie(ADMIN_COOKIE)
    return {"status": "ok"}


@app.post("/api/admin/password")
def admin_change_password(request: Request, req: PasswordChange) -> dict:
    """Change the admin password — stored in the settings table (survives
    .env edits; .env stays a bootstrap fallback)."""
    _require_admin(request)
    _user, expected = _admin_creds()
    if not hmac.compare_digest(req.current, expected):
        # 400 not 401 — a wrong CURRENT password must not log the admin out
        raise HTTPException(status_code=400, detail="поточний пароль невірний")
    if len(req.new) < 8:
        raise HTTPException(status_code=400, detail="мінімум 8 символів")
    repository.set_setting("ADMIN_PASSWORD", req.new)
    # drop every other session — a changed password should kick stolen ones
    keep = request.cookies.get(ADMIN_COOKIE)
    for t in [t for t in _sessions if t != keep]:
        _sessions.pop(t, None)
    logger.info("admin password changed")
    return {"status": "ok"}


def _mask(value: str) -> str:
    """Show only the tail — enough to recognize the key, not to leak it."""
    return "•••" + value[-4:] if len(value) > 4 else "•••"


def _source_state(cfg) -> dict[str, bool]:
    """Which key-gated sources are enabled — mirrors registry.py conditions."""
    return {
        "jooble": bool(cfg.jooble_api_key),
        "adzuna": bool(cfg.adzuna_app_id and cfg.adzuna_app_key),
        "usajobs": bool(cfg.usajobs_api_key and cfg.usajobs_email),
    }


def _settings_payload() -> dict:
    cfg = _effective_config()
    saved = repository.all_settings()
    keys = []
    for name, meta in SECRET_KEYS.items():
        if name in saved:
            raw, origin = saved[name], "db"
        else:
            raw, origin = os.getenv(name) or "", "env"
        keys.append(
            {
                "name": name,
                "label": meta["label"],
                "hint": meta["hint"],
                "secret": meta["secret"],
                "set": bool(raw),
                "origin": origin,
                "value": raw or None,  # admin-gated — the form shows the saved key
                "masked": _mask(raw) if (meta["secret"] and raw) else (raw or None),
            }
        )
    return {"keys": keys, "sources": _source_state(cfg)}


@app.get("/api/settings")
def get_settings(request: Request) -> dict:
    """Credential status — masked values only, never the raw secrets."""
    _require_admin(request)
    return _settings_payload()


@app.post("/api/settings")
def save_settings(request: Request, req: SettingsUpdate) -> dict:
    """Persist credentials to the settings table and rebuild sources."""
    _require_admin(request)
    global config, scraper
    updates = {k: v.strip() for k, v in req.values.items()}
    unknown = set(updates) - SECRET_KEYS.keys()
    if unknown:
        raise HTTPException(
            status_code=400, detail=f"unknown settings keys: {sorted(unknown)}"
        )
    for k, v in updates.items():
        repository.set_setting(k, v)  # empty value = explicit clear, overrides env
    config = _effective_config()
    old = scraper
    scraper = _build_scraper(config)
    if _scrape_lock.acquire(blocking=False):
        try:
            old.close()  # retire the replaced pool+Chromium, don't leak it
        finally:
            _scrape_lock.release()
    else:
        logger.warning("settings rebuilt mid-scrape — old scraper kept until exit")
    logger.info("settings updated: %s", sorted(updates))
    return _settings_payload()


@app.get("/api/jobs")
def list_jobs(
    q: str | None = None,
    source: str | None = None,
    max_scam: int | None = Query(default=None, ge=0, le=100),
    scam_level: str | None = Query(default=None, pattern="^(safe|suspicious|scam)$"),
    remote_only: bool = False,
    min_salary: float | None = Query(default=None, ge=0),
    currency: str | None = Query(default=None, pattern="^(USD|EUR|UAH|GBP)$"),
    level: str | None = Query(default=None, pattern="^(junior|middle|senior)$"),
    years: str | None = Query(default=None, pattern="^(0-1|1-3|3-5|5-10|10\\+)$"),
    lang: str | None = Query(
        default=None, pattern="^(en|uk|pl|de|fr|es|it|pt|nl|cs)$"
    ),
    workplace: str | None = Query(
        default=None,
        pattern="^(remote|hybrid|office)(,(remote|hybrid|office))*$",
    ),
    countries: str | None = None,
    sort: str = Query(default="score", pattern="^(score|newest)$"),
    limit: int = Query(default=50, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    jobs = jobs_repository.list_jobs(
        query=q, source=source, max_scam=max_scam, scam_level=scam_level,
        remote_only=remote_only, min_salary=min_salary, currency=currency,
        level=level, years=years, lang=lang,
        workplace=workplace, countries=countries, sort=sort,
        limit=limit, offset=offset,
    )
    return [asdict(j) for j in jobs]


@app.get("/api/sources")
def list_sources() -> dict:
    return {"configured": scraper.source_names, "with_data": jobs_repository.list_sources()}


@app.get("/api/locations")
def list_locations() -> list[str]:
    return jobs_repository.list_countries()


@app.get("/api/stats")
def stats(
    q: str | None = None,
    source: str | None = None,
    remote_only: bool = False,
    min_salary: float | None = Query(default=None, ge=0),
    currency: str | None = Query(default=None, pattern="^(USD|EUR|UAH|GBP)$"),
    level: str | None = Query(default=None, pattern="^(junior|middle|senior)$"),
    years: str | None = Query(default=None, pattern="^(0-1|1-3|3-5|5-10|10\\+)$"),
    lang: str | None = Query(
        default=None, pattern="^(en|uk|pl|de|fr|es|it|pt|nl|cs)$"
    ),
    workplace: str | None = Query(
        default=None,
        pattern="^(remote|hybrid|office)(,(remote|hybrid|office))*$",
    ),
    countries: str | None = None,
    scam_level: str | None = Query(
        default=None, pattern="^(safe|suspicious|scam)$"
    ),
    max_scam: int | None = Query(default=None, ge=0, le=100),
) -> dict:
    return jobs_repository.stats(
        query=q, source=source, remote_only=remote_only,
        min_salary=min_salary, currency=currency,
        level=level, years=years, lang=lang, workplace=workplace,
        countries=countries, scam_level=scam_level, max_scam=max_scam,
    )


@app.get("/api/last-report")
def last_report() -> dict | None:
    return _last_report


@app.get("/api/scrape/status")
def scrape_status() -> dict:
    """Progress of the background scrape; `new` grows as jobs are saved."""
    return _scrape_status


@app.post("/api/scrape/stop")
def scrape_stop() -> dict:
    """Cooperative stop: the run halts at the next completed fetch; jobs
    already saved stay visible. In-flight fetches finish and are dropped."""
    if not _scrape_status["running"]:
        return {"status": "not_running"}
    _stop_event.set()
    return {"status": "stopping"}


@app.post("/api/scrape")
def scrape(req: ScrapeRequest) -> dict:
    """Start the scrape in a background thread; poll /api/scrape/status for progress."""
    global _last_report
    if not _scrape_lock.acquire(blocking=False):
        return {"status": "already_running"}

    def worker() -> None:
        global _last_report
        _stop_event.clear()
        _scrape_status["running"] = True
        _scrape_status["new"] = 0
        _scrape_status["stopped"] = False
        try:
            # live repo is per-run: wipe everything, the previous run's
            # cards must disappear the moment a new scrape starts
            removed = jobs_repository.clear_jobs()
            if removed:
                logger.info("cleared %d live job(s) for the new run", removed)
            query = SearchQuery(
                keywords=req.keywords,
                location=req.location,
                remote_only=req.remote_only,
                limit_per_source=req.limit_per_source,
            )
            report = scraper.run(
                query, progress=_scrape_status, should_stop=_stop_event.is_set
            )
            _last_report = {
                name: asdict(r) for name, r in report.per_source.items()
            } | {"total_new": report.total_new}
        except Exception:
            logger.exception("scrape run failed")
        finally:
            _scrape_status["running"] = False
            _scrape_status["stopped"] = _stop_event.is_set()
            _scrape_lock.release()

    threading.Thread(target=worker, daemon=True).start()
    return {"status": "started"}
