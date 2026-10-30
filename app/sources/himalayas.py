"""Himalayas — public JSON API for remote jobs worldwide.

API: https://himalayas.app/jobs/api — no server-side keyword/location search,
so both are filtered client-side (same pattern as RemoteOkSource).
Location is matched against `locationRestrictions` (country names like
"United States", "Worldwide") plus timezone ranges for region presets.
"""
from __future__ import annotations

from typing import Iterable

from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher
from app.storage.query_builder import matches_keywords

API_URL = "https://himalayas.app/jobs/api"
PAGE_LIMIT = 200

# Region preset -> substrings matched against locationRestrictions entries.
REGION_HINTS = {
    "europe": ("worldwide", "europe", "uk", "united kingdom", "germany", "france",
               "spain", "poland", "netherlands", "ukraine", "emea"),
    "європа": ("worldwide", "europe", "emea"),
    "united states": ("united states", "usa", "us", "worldwide", "north america"),
    "usa": ("united states", "usa", "worldwide", "north america"),
    "сша": ("united states", "usa", "worldwide"),
    "canada": ("canada", "worldwide", "north america"),
    "канада": ("canada", "worldwide"),
    "latin america": ("latin america", "latam", "south america", "worldwide",
                      "brazil", "mexico", "argentina"),
    "south america": ("latin america", "latam", "south america", "worldwide"),
    "asia": ("asia", "apac", "worldwide", "india", "singapore", "japan"),
    "азія": ("asia", "apac", "worldwide"),
    "australia": ("australia", "new zealand", "apac", "worldwide"),
    "new zealand": ("new zealand", "australia", "apac", "worldwide"),
    "україна": ("ukraine", "worldwide", "europe", "emea"),
    "ukraine": ("ukraine", "worldwide", "europe", "emea"),
}


class HimalayasSource:
    name = "himalayas"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        # API takes only `limit` — keyword and location are filtered below
        response = self._fetcher.get(
            API_URL, params={"limit": PAGE_LIMIT}, source_name=self.name
        )
        keywords = query.keywords.lower()
        loc = (query.location or "").strip().lower()
        # preset region -> hint list; unknown location -> match it literally
        hints = REGION_HINTS.get(loc, (loc,) if loc else None)
        jobs: list[RawJob] = []
        for item in response.json().get("jobs", []):
            title = item.get("title") or ""
            haystack = " ".join(
                [title, item.get("excerpt") or "", item.get("description") or "",
                 " ".join(item.get("categories") or []),
                 item.get("companyName") or ""]
            ).lower()
            if not matches_keywords(haystack, keywords):
                continue
            # a job counts when any hint appears in its location restrictions
            restrictions = " ".join(item.get("locationRestrictions") or []).lower()
            if hints and not any(h in restrictions for h in hints):
                continue
            jobs.append(
                RawJob(
                    source=self.name,
                    url=item.get("applicationLink")
                    or f"https://himalayas.app/jobs/{item.get('guid', '')}",
                    title=title,
                    company=item.get("companyName"),
                    location=", ".join(item.get("locationRestrictions") or [])
                    or "Worldwide",
                    salary_raw=self._salary_raw(item),
                    description=item.get("excerpt") or "",
                    remote=True,
                    published_at=item.get("pubDate"),
                    external_id=item.get("guid"),
                )
            )
            if len(jobs) >= query.limit_per_source:
                break
        return jobs

    @staticmethod
    def _salary_raw(item: dict) -> str | None:
        """Emit 'lo-hi CUR/period'; parse_salary handles /yr normalization."""
        lo, hi = item.get("minSalary"), item.get("maxSalary")
        cur = item.get("currency") or "USD"
        period = {"annual": "/yr", "monthly": "/mo", "hourly": "/hr"}.get(
            item.get("salaryPeriod") or "", ""
        )
        if lo and hi:
            return f"{lo}-{hi} {cur}{period}"
        return None
