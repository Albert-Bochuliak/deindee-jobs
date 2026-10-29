"""FastAPI entrypoint. Run: uvicorn app.api.server:app --reload --port 8000"""
from __future__ import annotations

import logging
import threading
from dataclasses import asdict

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import load_config
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
scraper = ScraperService(
    sources=build_sources(config),
    normalizer=Normalizer(),
    pipeline=FilterPipeline(build_rules(), config),
    repository=repository,
)

app = FastAPI(title="Job Scraper API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_scrape_lock = threading.Lock()
_last_report: dict | None = None
_scrape_status = {"running": False, "new": 0}


class ScrapeRequest(BaseModel):
    keywords: str = ""
    location: str = ""
    remote_only: bool = False
    limit_per_source: int = 50


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
    years: str | None = Query(default=None, pattern="^(0-1|1-3|3-5|5-10|10\+)$"),
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
    jobs = repository.list_jobs(
        query=q, source=source, max_scam=max_scam, scam_level=scam_level,
        remote_only=remote_only, min_salary=min_salary, currency=currency,
        level=level, years=years, lang=lang,
        workplace=workplace, countries=countries, sort=sort,
        limit=limit, offset=offset,
    )
    return [asdict(j) for j in jobs]


@app.get("/api/sources")
def list_sources() -> dict:
    return {"configured": scraper.source_names, "with_data": repository.list_sources()}


@app.get("/api/locations")
def list_locations() -> list[str]:
    return repository.list_countries()


@app.get("/api/stats")
def stats(
    q: str | None = None,
    source: str | None = None,
    remote_only: bool = False,
    min_salary: float | None = Query(default=None, ge=0),
    currency: str | None = Query(default=None, pattern="^(USD|EUR|UAH|GBP)$"),
    level: str | None = Query(default=None, pattern="^(junior|middle|senior)$"),
    years: str | None = Query(default=None, pattern="^(0-1|1-3|3-5|5-10|10\+)$"),
    lang: str | None = Query(
        default=None, pattern="^(en|uk|pl|de|fr|es|it|pt|nl|cs)$"
    ),
    workplace: str | None = Query(
        default=None,
        pattern="^(remote|hybrid|office)(,(remote|hybrid|office))*$",
    ),
    countries: str | None = None,
) -> dict:
    return repository.stats(
        query=q, source=source, remote_only=remote_only,
        min_salary=min_salary, currency=currency,
        level=level, years=years, lang=lang, workplace=workplace,
        countries=countries,
    )


@app.get("/api/last-report")
def last_report() -> dict | None:
    return _last_report


@app.get("/api/scrape/status")
def scrape_status() -> dict:
    """Progress of the background scrape; `new` grows as jobs are saved."""
    return _scrape_status


@app.post("/api/scrape")
def scrape(req: ScrapeRequest) -> dict:
    """Start the scrape in a background thread; poll /api/scrape/status for progress."""
    global _last_report
    if not _scrape_lock.acquire(blocking=False):
        return {"status": "already_running"}

    def worker() -> None:
        global _last_report
        _scrape_status["running"] = True
        _scrape_status["new"] = 0
        try:
            query = SearchQuery(
                keywords=req.keywords,
                location=req.location,
                remote_only=req.remote_only,
                limit_per_source=req.limit_per_source,
            )
            report = scraper.run(query, progress=_scrape_status)
            _last_report = {
                name: asdict(r) for name, r in report.per_source.items()
            } | {"total_new": report.total_new}
        except Exception:
            logger.exception("scrape run failed")
        finally:
            _scrape_status["running"] = False
            _scrape_lock.release()

    threading.Thread(target=worker, daemon=True).start()
    return {"status": "started"}
