"""RemoteOK — public JSON API."""
from __future__ import annotations

from typing import Iterable

from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher

API_URL = "https://remoteok.com/api"


class RemoteOkSource:
    name = "remoteok"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        # no server-side search — full feed, keywords filtered below
        response = self._fetcher.get(API_URL, source_name=self.name)
        data = response.json()
        # First element is API metadata, not a job.
        items = [item for item in data if isinstance(item, dict) and "position" in item]
        keywords = query.keywords.lower()
        jobs: list[RawJob] = []
        for item in items:
            title = item.get("position") or ""
            haystack = " ".join(
                [title, item.get("description") or "", " ".join(item.get("tags") or [])]
            ).lower()
            if keywords and keywords not in haystack:
                continue
            jobs.append(
                RawJob(
                    source=self.name,
                    url=item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id')}",
                    title=title,
                    company=item.get("company"),
                    location=item.get("location") or "Remote",
                    salary_raw=self._salary_raw(item),
                    description=item.get("description") or "",
                    remote=True,
                    published_at=item.get("date"),
                    external_id=str(item.get("id")) if item.get("id") else None,
                )
            )
            if len(jobs) >= query.limit_per_source:
                break
        return jobs

    @staticmethod
    def _salary_raw(item: dict) -> str | None:
        """RemoteOK reports USD annual range -> 'lo-hi USD'."""
        lo, hi = item.get("salary_min"), item.get("salary_max")
        if lo and hi:
            return f"{lo}-{hi} USD"
        return None
