"""Orchestration: sources -> normalize -> dedup -> score -> save. No HTTP/parsing logic here."""
from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, replace

from app.models import JobRepository, SearchQuery, Source
from app.parsing.normalize import GLOBAL_LOC_MARKERS, Normalizer
from app.services.dedup import Deduplicator
from app.services.relevance import score_relevance
from app.services.scoring import FilterPipeline
from app.storage.locations import COUNTRY_ALIASES, region_country

logger = logging.getLogger(__name__)


def location_matches(job_loc: str | None, wanted: str) -> bool:
    """Keep a job when its location fits the requested country/place.

    `wanted` may be a comma-separated list — any part matches. Empty
    locations and global markers (Remote, Worldwide…) pass; a concrete
    different place ("Spain" when wanted "Canada") is filtered out.
    """
    parts = [
        COUNTRY_ALIASES.get(w.strip().lower(), w.strip().lower())
        for w in wanted.split(",")
        if w.strip()
    ]
    if not parts:
        return True
    if not job_loc or not job_loc.strip():
        return True
    loc = job_loc.strip().lower()
    if any(w in loc for w in parts):
        return True
    if loc in GLOBAL_LOC_MARKERS:
        return True
    country = region_country(job_loc)
    return bool(country and any(w in country for w in parts))


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
    stopped: bool = False  # user aborted via /api/scrape/stop

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
        # Process-lifetime single-worker pool for browser sources. It must NOT
        # be recreated per run: the shared Chromium is greenlet-bound to the
        # worker thread that launched it — a per-run pool retires that thread
        # and every later run dies with "cannot switch to a different thread
        # (which happens to have exited)". The thread only spawns on first
        # submit, so this costs nothing until a browser source runs.
        self._pw_executor = ThreadPoolExecutor(max_workers=1)

    def close(self) -> None:
        """Shut the shared Chromium down and retire the browser pool.

        fetcher.close() MUST run on the pool's worker thread — it owns the
        greenlet-bound browser; calling it here would hit "cannot switch
        to a different thread" again. Queued tasks run before shutdown.
        """
        closed: set[int] = set()
        for source in self._sources:
            if not getattr(source, "uses_browser", False):
                continue
            fetcher = getattr(source, "_fetcher", None)
            if fetcher is not None and id(fetcher) not in closed:
                closed.add(id(fetcher))
                self._pw_executor.submit(fetcher.close)
        self._pw_executor.shutdown(wait=True)

    @property
    def source_names(self) -> list[str]:
        return [s.name for s in self._sources]

    def run(
        self,
        query: SearchQuery,
        progress: dict | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> RunReport:
        report = RunReport()
        dedup = Deduplicator()
        # HTTP fetches are IO-bound — run them in parallel and process each
        # completed task immediately so new jobs reach the DB (and the UI)
        # without waiting for the slowest source. Comma-separated locations
        # expand into one task per source×location.
        locs = [l.strip() for l in query.location.split(",") if l.strip()] or [""]
        tasks = [(s, replace(query, location=loc)) for s in self._sources for loc in locs]
        # Playwright's sync API is greenlet-bound: the shared browser must be
        # driven from ONE thread or it dies with "Cannot switch to a different
        # thread". Browser sources therefore run serially on a dedicated
        # single-worker pool; plain-HTTP sources use the parallel one.
        browsers = [(s, q) for s, q in tasks if getattr(s, "uses_browser", False)]
        http = [(s, q) for s, q in tasks if not getattr(s, "uses_browser", False)]
        # HTTP pool is per-run (stateless fetchers); the browser pool is
        # self._pw_executor — shared, never shut down, owns the Chromium thread.
        # Not a `with` block: shutdown(wait=...) must depend on `stopped`.
        ex = ThreadPoolExecutor(max_workers=max(1, min(16, len(http))))
        try:
            futures = {ex.submit(_safe_fetch, s, q): s for s, q in http}
            futures.update(
                {self._pw_executor.submit(_safe_fetch, s, q): s for s, q in browsers}
            )
            for fut in as_completed(futures):
                # cooperative stop: bail at the next completed fetch —
                # cancel() kills queued tasks; in-flight ones finish and
                # are simply discarded (the loop is over)
                if should_stop is not None and should_stop():
                    report.stopped = True
                    for pending in futures:
                        pending.cancel()
                    break
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
                    job.relevance = score_relevance(job, query.keywords)
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
        finally:
            # stopped: don't drain in-flight fetches — run() returns now,
            # status.running flips, the Stop button unblocks. Stray threads
            # finish silently; their results are discarded by the dead loop.
            ex.shutdown(wait=not report.stopped, cancel_futures=True)
        return report


def _safe_fetch(source: Source, query: SearchQuery) -> tuple[list | None, str | None]:
    """Fetch one source; returns (raw_jobs, error_message)."""
    try:
        return list(source.fetch(query)), None
    except Exception as exc:  # SourceError + unexpected — never kill the run
        return None, str(exc)
