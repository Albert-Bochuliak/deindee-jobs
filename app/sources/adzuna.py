"""Adzuna — official API, enabled only when ADZUNA_APP_ID/ADZUNA_APP_KEY are set.

Note: Adzuna has no Ukraine endpoint; ADZUNA_COUNTRY picks the market (us, gb, pl, de...).
Salaries come as yearly min/max in the market's local currency.
"""
from __future__ import annotations

from typing import Iterable

from app.config import Config
from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher

API_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"

COUNTRY_CURRENCY = {
    "us": "USD", "gb": "GBP", "de": "EUR", "fr": "EUR", "es": "EUR", "it": "EUR",
    "nl": "EUR", "be": "EUR", "at": "EUR", "pl": "PLN", "ca": "CAD", "au": "AUD",
    "br": "BRL", "in": "INR", "mx": "MXN", "nz": "NZD", "sg": "SGD", "za": "ZAR",
    "ch": "CHF",
}


class AdzunaSource:
    name = "adzuna"

    def __init__(self, fetcher: HttpFetcher, config: Config) -> None:
        self._fetcher = fetcher
        self._app_id = config.adzuna_app_id
        self._app_key = config.adzuna_app_key
        self._country = config.adzuna_country

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        # server-side search: what=keywords, where=location, both optional
        params = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "results_per_page": min(query.limit_per_source, 50),  # API caps at 50
            "what": query.keywords or "developer",
            "where": query.location or "",
            "content-type": "application/json",
        }
        response = self._fetcher.get(
            API_URL.format(country=self._country), params=params, source_name=self.name
        )
        currency = COUNTRY_CURRENCY.get(self._country, "USD")
        jobs: list[RawJob] = []
        for item in response.json().get("results", []):
            jobs.append(
                RawJob(
                    source=self.name,
                    url=item.get("redirect_url") or "",
                    title=item.get("title") or "",
                    company=(item.get("company") or {}).get("display_name"),
                    location=(item.get("location") or {}).get("display_name"),
                    salary_raw=self._salary_raw(item, currency),
                    description=item.get("description") or "",
                    published_at=item.get("created"),
                    external_id=str(item.get("id")) if item.get("id") else None,
                )
            )
        return jobs

    @staticmethod
    def _salary_raw(item: dict, currency: str) -> str | None:
        """Adzuna pays are yearly — emit '/year' so parse_salary divides by 12."""
        lo, hi = item.get("salary_min"), item.get("salary_max")
        if lo and hi:
            return f"{lo:.0f}-{hi:.0f} {currency} /year"
        if lo:
            return f"{lo:.0f} {currency} /year"
        return None
