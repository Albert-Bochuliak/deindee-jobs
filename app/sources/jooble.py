"""Jooble — official API, enabled only when JOOBLE_API_KEY is set."""
from __future__ import annotations

from typing import Iterable

from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher

API_URL_TEMPLATE = "https://jooble.org/api/{key}"


class JoobleSource:
    name = "jooble"

    def __init__(self, fetcher: HttpFetcher, api_key: str) -> None:
        self._fetcher = fetcher
        # key is part of the URL path, not a header — Jooble quirk
        self._url = API_URL_TEMPLATE.format(key=api_key)

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        # server-side search via POST {keywords, location}
        payload = {
            "keywords": query.keywords or "developer",
            "location": query.location or "",
        }
        response = self._fetcher.post(self._url, json=payload, source_name=self.name)
        jobs: list[RawJob] = []
        for item in response.json().get("jobs", [])[: query.limit_per_source]:
            jobs.append(
                RawJob(
                    source=self.name,
                    url=item.get("link") or "",
                    title=item.get("title") or "",
                    company=item.get("company") or None,
                    location=item.get("location"),
                    salary_raw=item.get("salary") or None,
                    description=item.get("snippet") or "",
                    published_at=item.get("updated"),
                    external_id=str(item.get("id")) if item.get("id") else None,
                )
            )
        return jobs
