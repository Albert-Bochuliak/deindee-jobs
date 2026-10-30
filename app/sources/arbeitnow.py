"""Arbeitnow — free job board JSON API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher
from app.storage.query_builder import matches_keywords

API_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowSource:
    name = "arbeitnow"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        # no server-side search — the API returns the full board;
        # keywords and remote_only are filtered client-side below
        response = self._fetcher.get(API_URL, source_name=self.name)
        keywords = query.keywords.lower()
        jobs: list[RawJob] = []
        for item in response.json().get("data", []):
            haystack = " ".join(
                [
                    item.get("title") or "",
                    item.get("description") or "",
                    " ".join(item.get("tags") or []),
                ]
            ).lower()
            if not matches_keywords(haystack, keywords):
                continue
            remote = bool(item.get("remote"))
            if query.remote_only and not remote:
                continue
            jobs.append(
                RawJob(
                    source=self.name,
                    url=item.get("url") or "",
                    title=item.get("title") or "",
                    company=item.get("company_name"),
                    location=item.get("location"),
                    description=item.get("description") or "",
                    remote=remote,
                    published_at=self._epoch_to_iso(item.get("created_at")),
                    external_id=item.get("slug"),
                )
            )
            if len(jobs) >= query.limit_per_source:
                break
        return jobs

    @staticmethod
    def _epoch_to_iso(epoch: object) -> str | None:
        """created_at comes as a unix epoch; ISO string or None on bad input."""
        try:
            return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            return None
