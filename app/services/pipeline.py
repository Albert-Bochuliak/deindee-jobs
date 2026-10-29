"""Orchestration: sources -> normalize -> dedup -> score -> save. No HTTP/parsing logic here."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, replace

from app.models import JobRepository, SearchQuery, Source
from app.parsing.normalize import GLOBAL_LOC_MARKERS, Normalizer
from app.services.dedup import Deduplicator
from app.services.scoring import FilterPipeline

logger = logging.getLogger(__name__)


def location_matches(job_loc: str | None, wanted: str) -> bool:
    """Keep a job when its location fits the requested country/place.

    `wanted` may be a comma-separated list — any part matches. Empty
    locations and global markers (Remote, Worldwide…) pass; a concrete
    different place ("Spain" when wanted "Canada") is filtered out.
    """
    parts = [w.strip().lower() for w in wanted.split(",") if w.strip()]
    if not parts:
        return True
    if not job_loc or not job_loc.strip():
        return True
    loc = job_loc.strip().lower()
    if any(w in loc for w in parts):
        return True
    return loc in GLOBAL_LOC_MARKERS


@dataclass
class SourceReport:
    fetched: int = 0
    new: int = 0
    duplicates: int = 0
    filtered: int = 0
    error: str | None = None


@dataclass
class RunReport:
    per_source: dict[str, SourceReport] = field(default_factory=dict)

    @property
    def total_new(self) -> int:
        return sum(r.new for r in self.per_source.values())


class ScraperService:
    def __init__(
        self,
        sources: list[Source],
        normalizer: Normalizer,
        pipeline: FilterPipeline,
        repository: JobRepository,
    ) -> None:
        self._sources = sources
        self._normalizer = normalizer
        self._pipeline = pipeline
        self._repository = repository

    @property
    def source_names(self) -> list[str]:
        return [s.name for s in self._sources]

    def run(self, query: SearchQuery, progress: dict | None = None) -> RunReport:
        report = RunReport()
        dedup = Deduplicator()
        # HTTP fetches are IO-bound — run them in parallel and process each
        # completed task immediately so new jobs reach the DB (and the UI)
        # without waiting for the slowest source. Comma-separated locations
        # expand into one task per source×location.
        locs = [l.strip() for l in query.location.split(",") if l.strip()] or [""]
        tasks = [(s, replace(query, location=loc)) for s in self._sources for loc in locs]
        with ThreadPoolExecutor(max_workers=min(16, len(tasks))) as ex:
            futures = {ex.submit(_safe_fetch, s, q): s for s, q in tasks}
            for fut in as_completed(futures):
                source = futures[fut]
                src_report = report.per_source.setdefault(source.name, SourceReport())
                raw_jobs, err = fut.result()
                if err is not None:
                    if not src_report.fetched and not src_report.error:
                        logger.error("Source %s failed: %s", source.name, err)
                        src_report.error = err
                    continue
                src_report.fetched += len(raw_jobs)
                for raw in raw_jobs:
                    job = self._normalizer.normalize(raw)
                    if not location_matches(job.location, query.location):
                        src_report.filtered += 1
                        continue
                    if dedup.seen(job):
                        src_report.duplicates += 1
                        continue
                    self._pipeline.score(job)
                    if self._repository.save(job):
                        src_report.new += 1
                        if progress is not None:
                            progress["new"] += 1
                    else:
                        src_report.duplicates += 1
                logger.info(
                    "[%s] fetched=%d new=%d dupes=%d filtered=%d",
                    source.name, src_report.fetched, src_report.new,
                    src_report.duplicates, src_report.filtered,
                )
        return report


def _safe_fetch(source: Source, query: SearchQuery) -> tuple[list | None, str | None]:
    """Fetch one source; returns (raw_jobs, error_message)."""
    try:
        return list(source.fetch(query)), None
    except Exception as exc:  # SourceError + unexpected — never kill the run
        return None, str(exc)
