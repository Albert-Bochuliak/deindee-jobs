"""Offline parse test for Craigslist — modern + legacy card markup, no network."""
from __future__ import annotations

from pathlib import Path

from app.sources.craigslist import parse_listing

FIXTURE = Path(__file__).parent / "fixtures" / "craigslist_listing.html"


def _jobs():
    return parse_listing(FIXTURE.read_text(encoding="utf-8"))


def test_parse_cards():
    assert len(_jobs()) == 2


def test_modern_card():
    job = _jobs()[0]
    assert job.source == "craigslist"
    assert job.title == "Python developer (Remote)"
    assert job.url.endswith("/7876543210.html")
    assert job.external_id == "7876543210"
    assert job.remote is True  # "Remote" in title
    assert job.location == "new york city"


def test_legacy_card():
    job = _jobs()[1]
    assert job.title == "Backend engineer — Django/AWS"
    assert job.location == "brooklyn"  # "(brooklyn)" parens stripped
    assert job.salary_raw == "$120k-$160k"
    assert job.published_at == "2026-10-25 14:00"
    assert job.external_id == "7871112222"
    assert job.remote is None
    assert job.company is None  # craigslist ads are anonymous


def test_empty_html_returns_empty():
    assert parse_listing("<html><body></body></html>") == []
