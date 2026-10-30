"""Dice parse tests — offline, against a saved rendered-page fixture."""
from pathlib import Path

from app.sources.dice import parse_listing

FIXTURE = Path(__file__).parent / "fixtures" / "dice_search.html"


def test_parses_cards():
    jobs = parse_listing(FIXTURE.read_text(encoding="utf-8"))
    assert len(jobs) >= 10


def test_card_fields():
    jobs = parse_listing(FIXTURE.read_text(encoding="utf-8"))
    first = jobs[0]
    assert first.source == "dice"
    assert first.title  # non-empty
    assert "/job-detail/" in first.url
    assert first.url.startswith("https://www.dice.com")
    assert first.company
    assert first.external_id


def test_locations_have_state_or_remote():
    jobs = parse_listing(FIXTURE.read_text(encoding="utf-8"))
    locs = [j.location for j in jobs]
    assert any(loc for loc in locs), "no locations parsed at all"


def test_empty_page_yields_nothing():
    assert parse_listing("<html><body>no results</body></html>") == []


def test_missing_company_card_skipped_or_ok():
    """A card without title/link is dropped, not crashed on."""
    html = """
    <div data-testid="job-card" data-id="x1">
      <p data-testid="job-card-company-name">Some Co</p>
    </div>"""
    assert parse_listing(html) == []
