"""Remotive — public JSON API for remote jobs."""
from __future__ import annotations

from typing import Iterable

from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher

API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveSource:
    name = "remotive"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        # server-side keyword search via ?search=; all jobs are remote
        params: dict = {"limit": query.limit_per_source}
        if query.keywords:
            params["search"] = query.keywords
        response = self._fetcher.get(API_URL, params=params, source_name=self.name)
        jobs = []
        for item in response.json().get("jobs", []):
            jobs.append(
                RawJob(
                    source=self.name,
                    url=item.get("url") or "",
                    title=item.get("title") or "",
                    company=item.get("company_name"),
                    location=item.get("candidate_required_location") or "Remote",
                    salary_raw=item.get("salary") or None,
                    description=item.get("description") or "",
                    remote=True,
                    published_at=item.get("publication_date"),
                    external_id=str(item.get("id")) if item.get("id") else None,
                )
            )
        return jobs
