"""Offline test for USAJOBS mapping — fetch() with a stubbed fetcher, no network."""
from __future__ import annotations

import json
from pathlib import Path

from app.models import SearchQuery
from app.sources.usajobs import UsaJobsSource

FIXTURE = Path(__file__).parent / "fixtures" / "usajobs_search.json"


class _StubResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _StubFetcher:
    """Mimics HttpFetcher.get — records the call, returns fixture JSON."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls: list[dict] = []

    def get(self, url, params=None, source_name="?", headers=None):
        self.calls.append(
            {"url": url, "params": params, "headers": headers}
        )
        return _StubResponse(self._payload)


def _source():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return UsaJobsSource(_StubFetcher(payload), api_key="k", email="me@x.com")


def test_headers_carry_auth():
    src = _source()
    src.fetch(SearchQuery(keywords="python"))
    headers = src._fetcher.calls[0]["headers"]
    assert headers == {"Authorization-Key": "k", "User-Agent": "me@x.com"}


def test_maps_items_to_rawjobs():
    jobs = _source().fetch(SearchQuery(keywords="python"))
    assert len(jobs) == 2
    first = jobs[0]
    assert first.source == "usajobs"
    assert first.title == "IT Specialist (APPSW)"
    assert first.company == "Department of Example Affairs"
    assert first.location == "Washington, District of Columbia"
    assert first.salary_raw == "95000-140000 USD/yr"
    assert first.remote is True  # RemoteIndicator
    assert first.external_id == "8123456001"
    # description joins JobSummary + QualificationSummary + MajorDuties —
    # the API's Keyword search hits fields beyond JobSummary
    assert "Python" in first.description
    assert "WordPress CMS" in first.description
    assert "Build accessible UI components." in first.description
    assert first.url == "https://www.usajobs.gov/Application/ApplyNow/8123456001"


def test_fallback_url_and_hourly_salary():
    second = _source().fetch(SearchQuery())[1]
    assert second.url == "https://www.usajobs.gov/job/8123456002"  # ApplyURI empty -> PositionURI
    assert second.salary_raw == "80-95 USD/hr"
    assert second.remote is None


def test_remote_only_filters():
    jobs = _source().fetch(SearchQuery(remote_only=True))
    assert [j.title for j in jobs] == ["IT Specialist (APPSW)"]


def test_limit_per_source():
    assert len(_source().fetch(SearchQuery(limit_per_source=1))) == 1
