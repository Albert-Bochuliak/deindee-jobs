"""Jobicy — public JSON API for remote jobs worldwide.

API: https://jobicy.com/api/v2/remote-jobs
- `geo` accepts slugs: europe, usa, latam, apac, emea, africa — server-side region filter.
- `tag` needs a taxonomy slug, so keywords are filtered client-side instead.
Locations not covered by geo slugs (Canada, Australia, cities...) are matched
against the `jobGeo` field client-side.
"""
from __future__ import annotations

from typing import Iterable

from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher

API_URL = "https://jobicy.com/api/v2/remote-jobs"

# query.location value -> jobicy `geo` filter slug (server-side).
GEO_SLUGS = {
    "europe": "europe",
    "європа": "europe",
    "united states": "usa",
    "usa": "usa",
    "us": "usa",
    "сша": "usa",
    "latin america": "latam",
    "south america": "latam",
    "латинська америка": "latam",
    "asia": "apac",
    "азія": "apac",
    "apac": "apac",
    "emea": "emea",
    "africa": "africa",
    "африка": "africa",
}


class JobicySource:
    name = "jobicy"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        params: dict = {"count": 100}  # API default is small; ask for max
        loc = (query.location or "").strip().lower()
        geo_slug = GEO_SLUGS.get(loc)
        if geo_slug:
            # region has a server-side filter — narrow the payload up front
            params["geo"] = geo_slug
        # Keyword search exists only via taxonomy tags (slug). If the tag
        # yields nothing, retry without it and match keywords client-side.
        tag = "-".join(query.keywords.lower().split())
        if tag:
            params["tag"] = tag
        response = self._fetcher.get(API_URL, params=params, source_name=self.name)
        items = response.json().get("jobs", [])
        if tag and not items:  # tag slug guessed wrong — fall back to plain list
            del params["tag"]
            tag = ""
            response = self._fetcher.get(API_URL, params=params, source_name=self.name)
            items = response.json().get("jobs", [])
        keywords = query.keywords.lower()
        jobs: list[RawJob] = []
        for item in items:
            title = item.get("jobTitle") or ""
            geo = item.get("jobGeo") or "Remote"
            excerpt = item.get("jobExcerpt") or ""
            haystack = " ".join(
                [title, excerpt, " ".join(item.get("jobIndustry") or []),
                 item.get("companyName") or ""]
            ).lower()
            if not tag and keywords and not all(
                k in haystack for k in keywords.split()
            ):
                continue
            # locations without a geo slug (Canada, cities…) match jobGeo text
            if loc and not geo_slug and loc not in geo.lower():
                continue
            jobs.append(
                RawJob(
                    source=self.name,
                    url=item.get("url") or "",
                    title=title,
                    company=item.get("companyName"),
                    location=geo,
                    salary_raw=self._salary_raw(item),
                    description=excerpt,
                    remote=True,
                    published_at=item.get("pubDate"),
                    external_id=str(item.get("id")) if item.get("id") else None,
                )
            )
            if len(jobs) >= query.limit_per_source:
                break
        return jobs

    @staticmethod
    def _salary_raw(item: dict) -> str | None:
        """Annual range -> 'lo-hi CUR/yr' for parse_salary normalization."""
        lo = item.get("annualSalaryMin")
        hi = item.get("annualSalaryMax")
        cur = item.get("salaryCurrency") or "USD"
        if lo and hi:
            return f"{lo}-{hi} {cur}/yr"
        return None
