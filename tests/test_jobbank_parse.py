"""Offline parse test for Job Bank — runs against the saved fixture, no network."""
from __future__ import annotations

from pathlib import Path

from app.sources.jobbank import parse_listing

FIXTURE = Path(__file__).parent / "fixtures" / "jobbank_listing.html"


def _jobs():
    return parse_listing(FIXTURE.read_text(encoding="utf-8"))


def test_parse_cards():
    assert len(_jobs()) == 3


def test_first_job_fields():
    job = _jobs()[0]
    assert job.source == "jobbank"
    assert job.title == "Web developer"
    # ;jsessionid and tracking params stripped -> canonical URL
    assert job.url == "https://www.jobbank.gc.ca/jobsearch/jobposting/50535683"
    assert job.company == "Quantum World Technologies Inc."
    assert job.location == "Stoney Creek (ON)"
    assert job.salary_raw == "$49.00 hourly"
    assert job.published_at == "October 19, 2026"
    assert job.external_id == "50535683"
    assert job.remote is None  # "On site" is not remote


def test_remote_telework_flag():
    assert _jobs()[1].remote is True  # "Hybrid" counts as remote-capable
    remote_job = _jobs()[2]
    assert remote_job.remote is True
    assert remote_job.company is None  # card has no business li — must not crash
    assert remote_job.salary_raw is None


def test_empty_html_returns_empty():
    assert parse_listing("<html><body></body></html>") == []
