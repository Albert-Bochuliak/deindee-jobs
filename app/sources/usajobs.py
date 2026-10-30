"""USAJOBS — official US government jobs REST API (developer.usajobs.gov).

GET https://data.usajobs.gov/api/search — enabled only when both
USAJOBS_API_KEY and USAJOBS_EMAIL are set (the email doubles as the
required User-Agent header). US-only board: LocationName is passed through,
non-US locations simply return few/no results.

Response: SearchResult.SearchResultItems[].MatchedObjectDescriptor.
"""
from __future__ import annotations

from typing import Iterable

from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher

API_URL = "https://data.usajobs.gov/api/search"
REMOTE_RE_WORDS = ("remote", "anywhere")


class UsaJobsSource:
    name = "usajobs"

    def __init__(self, fetcher: HttpFetcher, api_key: str, email: str) -> None:
        self._fetcher = fetcher
        # USAJOBS quirk: User-Agent must be the applicant's email address
        self._headers = {"Authorization-Key": api_key, "User-Agent": email}

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        params = {
            "Keyword": query.keywords,
            "ResultsPerPage": min(query.limit_per_source, 500),  # API cap
        }
        if query.location:
            params["LocationName"] = query.location
        response = self._fetcher.get(
            API_URL, params=params, source_name=self.name, headers=self._headers
        )
        items = (
            response.json()
            .get("SearchResult", {})
            .get("SearchResultItems", [])
        )
        jobs: list[RawJob] = []
        for item in items:
            d = item.get("MatchedObjectDescriptor") or {}
            loc_display = d.get("PositionLocationDisplay") or ""
            remote = self._is_remote(d, loc_display)
            if query.remote_only and not remote:
                continue
            apply_uri = d.get("ApplyURI") or []
            jobs.append(
                RawJob(
                    source=self.name,
                    url=(apply_uri[0] if apply_uri else None)
                    or d.get("PositionURI")
                    or "",
                    title=d.get("PositionTitle") or "",
                    company=d.get("OrganizationName") or d.get("DepartmentName"),
                    location=loc_display or None,
                    salary_raw=self._salary_raw(d),
                    description=self._description(d),
                    remote=True if remote else None,
                    published_at=d.get("PublicationStartDate"),
                    external_id=str(item.get("MatchedObjectId"))
                    if item.get("MatchedObjectId")
                    else d.get("PositionID"),
                )
            )
            if len(jobs) >= query.limit_per_source:
                break
        return jobs

    @staticmethod
    def _description(d: dict) -> str:
        """JobSummary + QualificationSummary + MajorDuties.

        The API's Keyword search matches the whole announcement (skills
        live in QualificationSummary / MajorDuties, not the summary).
        Storing only JobSummary produced rows that never match the local
        q-filter and that delete_matching can't clear — invisible and
        re-counted as duplicates on every re-scrape.
        """
        details = d.get("UserArea", {}).get("Details") or {}
        parts = [
            details.get("JobSummary") or "",
            d.get("QualificationSummary") or "",
        ]
        duties = details.get("MajorDuties") or []
        if isinstance(duties, str):
            duties = [duties]
        parts.extend(t for t in duties if isinstance(t, str))
        return "\n\n".join(s for s in (p.strip() for p in parts) if s)

    @staticmethod
    def _is_remote(d: dict, loc_display: str) -> bool:
        """UserArea.Details.RemoteIndicator, else 'remote'/'anywhere' in location."""
        details = d.get("UserArea", {}).get("Details") or {}
        if details.get("RemoteIndicator"):
            return True
        loc = loc_display.lower()
        return any(w in loc for w in REMOTE_RE_WORDS)

    @staticmethod
    def _salary_raw(d: dict) -> str | None:
        """'lo-hi USD/yr' — parse_salary normalizes annual to monthly."""
        rem = (d.get("PositionRemuneration") or [{}])[0]
        lo, hi = rem.get("MinimumRange"), rem.get("MaximumRange")
        period = {
            "Per Year": "/yr",
            "Per Month": "/mo",
            "Per Hour": "/hr",
            "Bi-Weekly": "/yr",  # x26 ≈ yearly, close enough for a filter hint
        }.get(rem.get("RateIntervalCode") or "", "")
        if lo and hi:
            return f"{lo}-{hi} USD{period}"
        if lo:
            return f"{lo} USD{period}"
        return None
