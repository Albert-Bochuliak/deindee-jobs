"""LinkedIn — public guest jobs API. No auth, no Cloudflare for this endpoint.

GET /jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=..&location=..&start=0
returns HTML fragment with <div class="job-search-card" data-entity-urn="urn:li:jobPosting:<id>">.
Card list has no description/salary — only title, company, location, date, link.
"""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup, Tag

from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher

API_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
CARD = "div.job-search-card"
URN_ID_RE = re.compile(r"jobPosting:(\d+)")   # numeric job id inside data-entity-urn
REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)


class LinkedInSource:
    name = "linkedin"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        # server-side search params; f_WT=2 is LinkedIn's remote-work filter
        params = {
            "keywords": query.keywords,
            "location": query.location or "Ukraine",
            "start": "0",
        }
        if query.remote_only:
            params["f_WT"] = "2"
        response = self._fetcher.get(API_URL, params=params, source_name=self.name)
        return parse_listing(response.text, self.name)[: query.limit_per_source]


def parse_listing(html: str, source: str = "linkedin") -> list[RawJob]:
    """Pure HTML fragment -> RawJob list. Testable offline against a fixture."""
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[RawJob] = []
    for card in soup.select(CARD):
        link = card.select_one("a.base-card__full-link")
        title_el = card.select_one("h3.base-search-card__title")
        if not link or not title_el:
            continue
        url = _clean_url(link.get("href") or "")
        location = _text(card, ".job-search-card__location")
        company = _text(card, ".base-search-card__subtitle a, a.hidden-nested-link")
        posted = card.select_one("time.job-search-card__listdate")
        id_match = URN_ID_RE.search(card.get("data-entity-urn") or "")
        jobs.append(
            RawJob(
                source=source,
                url=url,
                title=title_el.get_text(strip=True),
                company=company,
                location=location,
                salary_raw=None,
                description="",
                remote=True if location and REMOTE_RE.search(location) else None,
                published_at=posted.get("datetime") if posted else None,
                external_id=id_match.group(1) if id_match else None,
            )
        )
    return jobs


def _text(card: Tag, selector: str) -> str | None:
    """First matching element's text, or None — cards miss fields often."""
    el = card.select_one(selector)
    return el.get_text(" ", strip=True) if el else None


def _clean_url(href: str) -> str:
    """Drop LinkedIn tracking params (?position=..&trackingId=..)."""
    parts = urlparse(href)
    return urlunparse((parts.scheme, parts.netloc, parts.path, "", "", ""))
