"""Offline parse test for Djinni source — runs against the saved fixture, no network."""
from __future__ import annotations

from pathlib import Path

from app.sources.djinni import parse_listing

FIXTURE = Path(__file__).parent / "fixtures" / "djinni_listing.html"


def test_parse_listing_extracts_jobs():
    jobs = parse_listing(FIXTURE.read_text(encoding="utf-8"))
    assert len(jobs) == 2

    first = jobs[0]
    assert first.source == "djinni"
    assert first.title == "Senior AI Engineer"
    assert first.url == "https://djinni.co/jobs/855710-senior-ai-engineer/"
    assert first.company == "Atlas Technica"
    assert first.external_id == "855710"
    assert first.remote is True
    assert "FastAPI" in first.description

    second = jobs[1]
    assert second.title == "Data Analyst"
    assert second.company is None  # fixture has no company link — must not crash
    assert second.remote is None


def test_parse_listing_empty_html():
    assert parse_listing("<html><body></body></html>") == []
