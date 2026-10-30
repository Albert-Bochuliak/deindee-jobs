"""Craigslist — Playwright-rendered scraping of search/jjj (jobs section).

No API; the old ?format=rss endpoint is dead (410 since ~2020) and plain
HTTP returns either a JS-required shell or a 403 "Your request has been
blocked" for datacenter IPs — hence PlaywrightFetcher, with the shared
rate limit kept conservative (craigslist IP-bans aggressively).

Sites are per-city subdomains (no nationwide search): CITY_SLUGS maps
location presets, default is newyork.

Markup — two generations handled:
  modern: li.cl-search-result a.posting-title span.label
  legacy: li.result-row a.result-title + span.result-hood
"""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import quote_plus

from bs4 import BeautifulSoup, Tag

from app.models import RawJob, SearchQuery
from app.sources.playwright_source import PlaywrightFetcher

CARDS = "li.cl-search-result, div.cl-search-result, li.result-row"
REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}\b|"
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b",
    re.IGNORECASE,
)

# query.location -> craigslist city subdomain (jobs are US-local only).
CITY_SLUGS = {
    "new york": "newyork", "nyc": "newyork",
    "san francisco": "sfbay", "sf": "sfbay", "bay area": "sfbay",
    "los angeles": "losangeles", "la": "losangeles",
    "chicago": "chicago", "seattle": "seattle", "boston": "boston",
    "austin": "austin", "denver": "denver", "portland": "portland",
    "washington": "washingtondc", "dc": "washingtondc",
    "miami": "miami", "atlanta": "atlanta", "dallas": "dallas",
    "united states": "newyork", "usa": "newyork", "us": "newyork",
    "remote": "newyork", "сша": "newyork",
}
DEFAULT_SUB = "newyork"


class CraigslistSource:
    name = "craigslist"
    uses_browser = True  # Playwright — pinned to the single-thread executor

    def __init__(self, fetcher: PlaywrightFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        sub = CITY_SLUGS.get((query.location or "").strip().lower(), DEFAULT_SUB)
        kw = quote_plus(query.keywords.strip())
        url = f"https://{sub}.craigslist.org/search/jjj" + (f"?query={kw}" if kw else "")
        page = self._fetcher.get(
            url, source_name=self.name, wait_selector=CARDS, wait_ms=3000
        )
        return parse_listing(page.text)[: query.limit_per_source]


def parse_listing(html: str) -> list[RawJob]:
    """Pure HTML -> RawJob mapping. Testable offline against a fixture."""
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[RawJob] = []
    for card in soup.select(CARDS):
        job = _card_to_job(card)
        if job:
            jobs.append(job)
    return jobs


def _card_to_job(card: Tag) -> RawJob | None:
    link = (
        card.select_one("a.posting-title")
        or card.select_one("a.result-title")
        or card.select_one("a[href]")
    )
    if link is None:
        return None
    href = str(link.get("href") or "")
    title = _title(card, link)
    if not title or not href:
        return None
    card_text = card.get_text(" ")
    return RawJob(
        source="craigslist",
        url=href if href.startswith("http") else f"https:{href}",
        title=title,
        company=None,  # craigslist ads are anonymous — employer is inside the post
        location=_location(card),
        salary_raw=_salary(card),
        description="",
        remote=True if REMOTE_RE.search(card_text) else None,
        published_at=_date(card),
        external_id=_pid(card, href),
    )


def _title(card: Tag, link: Tag) -> str:
    """Title text: span.label (modern) or the anchor text itself (legacy)."""
    el = card.select_one("span.label") or card.select_one(
        ".posting-title-label"
    )
    text = el.get_text(strip=True) if el else link.get_text(" ", strip=True)
    return text


def _location(card: Tag) -> str | None:
    el = card.select_one("span.result-hood") or card.select_one(
        ".meta .location"
    ) or card.select_one(".meta")
    if el is None:
        return None
    # "(brooklyn)" -> "brooklyn"; meta joins 'location·date' — keep first chunk
    text = el.get_text(" ", strip=True).strip("()")
    return text.split("·")[0].strip() or None


def _salary(card: Tag) -> str | None:
    """List cards rarely show pay; grab '$xxk-$yyk' when present."""
    m = re.search(r"\$\s*\d[\d,.]*\s*[kK]?\s*[-–]\s*\$?\s*\d[\d,.]*\s*[kK]?",
                  card.get_text(" "))
    return m.group(0).strip() if m else None


def _date(card: Tag) -> str | None:
    el = (
        card.select_one(".cl-postingdate")
        or card.select_one(".result-date")
        or card.select_one("time")
    )
    if el is not None:
        return el.get("datetime") or el.get_text(strip=True) or None
    m = DATE_RE.search(card.get_text(" "))
    return m.group(0) if m else None


def _pid(card: Tag, href: str) -> str | None:
    pid = card.get("data-pid")
    if pid:
        return str(pid)
    m = re.search(r"/(\d{8,})\.html", href)
    return m.group(1) if m else None
