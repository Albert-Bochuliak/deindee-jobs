"""Offline test for Kijiji mapping — fetch() with a stubbed fetcher, no network."""
from __future__ import annotations

from pathlib import Path

from app.models import SearchQuery
from app.sources.kijiji import KijijiSource, parse_listings

FIXTURE = Path(__file__).parent / "fixtures" / "kijiji_search.html"


class _StubResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _StubFetcher:
    """Mimics HttpFetcher.get — records the call, returns fixture HTML."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.calls: list[dict] = []

    def get(self, url, params=None, source_name="?", headers=None):
        self.calls.append({"url": url, "params": params})
        return _StubResponse(self._text)


def _source():
    return KijijiSource(_StubFetcher(FIXTURE.read_text(encoding="utf-8")))


def test_keyword_and_location_in_url():
    src = _source()
    src.fetch(SearchQuery(keywords="wordpress dev", location="Ontario"))
    assert src._fetcher.calls[0]["url"] == (
        "https://www.kijiji.ca/b-jobs/canada/wordpress%20dev/k0c45l9004"
    )


def test_default_location_is_canada():
    src = _source()
    src.fetch(SearchQuery(keywords="wordpress"))
    assert src._fetcher.calls[0]["url"].endswith("/k0c45l0")


def test_maps_apollo_listings_to_rawjobs():
    jobs = _source().fetch(SearchQuery())
    # fixture has 3 listings; the empty-title one must be skipped
    assert len(jobs) == 2
    first = next(j for j in jobs if j.external_id == "1744878644")
    assert first.source == "kijiji"
    assert first.title == "WordPress Developer (Remote)"
    assert first.company == "Acme Web Studio"
    assert first.location == "Toronto, Ontario"  # attrs [province, city] flipped
    assert first.remote is True  # 'Remote' in title
    assert first.published_at == "2026-10-27T15:30:51.000Z"  # sortingDate wins
    assert first.url == (
        "https://www.kijiji.ca/v-it-jobs/city-of-toronto/"
        "wordpress-developer-remote/1744878644"
    )


def test_fallbacks_when_attributes_missing():
    second = next(
        j for j in _source().fetch(SearchQuery()) if j.external_id == "1744712491"
    )
    assert second.company is None  # no 'company' attribute
    assert second.location == "London, Ontario"
    assert second.published_at == "2026-10-12T14:31:23.000Z"  # activationDate
    assert second.remote is None


def test_remote_only_filters():
    jobs = _source().fetch(SearchQuery(remote_only=True))
    assert [j.title for j in jobs] == ["WordPress Developer (Remote)"]


def test_limit_per_source():
    assert len(_source().fetch(SearchQuery(limit_per_source=1))) == 1


def test_empty_when_no_next_data():
    assert parse_listings("<html><body>no script</body></html>") == []
