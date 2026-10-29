"""Freelancehunt — official public JSON:API v2. Projects list works without a token.

Response shape: {"data": [{"id", "type", "attributes": {...}, "links": {...}}]}
items[].links.self.web is the public project URL.
"""
from __future__ import annotations

from typing import Iterable

from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher

API_URL = "https://api.freelancehunt.com/v2/projects"


class FreelancehuntSource:
    name = "freelancehunt"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        # projects list has no search params — filter keywords client-side
        response = self._fetcher.get(API_URL, source_name=self.name)
        keywords = query.keywords.lower()
        jobs: list[RawJob] = []
        for item in response.json().get("data", []):
            attrs = item.get("attributes", {})
            haystack = self._haystack(attrs).lower()
            if keywords and keywords not in haystack:
                continue
            jobs.append(
                RawJob(
                    source=self.name,
                    url=self._web_url(item),
                    title=attrs.get("name") or "",
                    company=self._employer(attrs),
                    location=self._location(attrs),
                    salary_raw=self._budget(attrs),
                    description=self._description(attrs),
                    remote=attrs.get("is_remote_job"),
                    published_at=attrs.get("published_at"),
                    external_id=str(item.get("id")) if item.get("id") else None,
                )
            )
            if len(jobs) >= query.limit_per_source:
                break
        return jobs

    @staticmethod
    def _haystack(attrs: dict) -> str:
        """name + description + skills + tags as one blob for keyword match."""
        skills = " ".join(s.get("name", "") for s in attrs.get("skills") or [])
        tags = " ".join(t.get("name", "") for t in attrs.get("tags") or [])
        return " ".join([attrs.get("name") or "", attrs.get("description") or "", skills, tags])

    @staticmethod
    def _web_url(item: dict) -> str:
        """Public project page — JSON:API gives it via links.self.web."""
        return ((item.get("links") or {}).get("self") or {}).get("web") or ""

    @staticmethod
    def _employer(attrs: dict) -> str | None:
        """Real name if present, else the account login."""
        emp = attrs.get("employer") or {}
        name = f"{emp.get('first_name') or ''} {emp.get('last_name') or ''}".strip()
        return name or emp.get("login")

    @staticmethod
    def _location(attrs: dict) -> str | None:
        """Location arrives either as {name: ...} dict or a plain string."""
        loc = attrs.get("location")
        if isinstance(loc, dict):
            return loc.get("name")
        return loc

    @staticmethod
    def _budget(attrs: dict) -> str | None:
        """Budget is {amount, currency} dict or a raw value -> 'amt CUR'."""
        budget = attrs.get("budget")
        if not budget:
            return None
        if isinstance(budget, dict):
            amount = budget.get("amount")
            currency = budget.get("currency") or "UAH"
            return f"{amount} {currency}" if amount else None
        return str(budget)

    @staticmethod
    def _description(attrs: dict) -> str:
        """Append skills to the description so keyword rules can match them."""
        skills = ", ".join(s.get("name", "") for s in attrs.get("skills") or [])
        base = attrs.get("description") or ""
        return f"{base}\nНавички: {skills}" if skills else base
