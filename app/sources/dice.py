"""Dice — US tech job board (dice.com).

No usable public endpoint: the site's internal job-search API sits behind
anti-bot (403 for plain clients) and search pages are JS-rendered — hence
PlaywrightFetcher, justified by the Cloudflare wall.

Markup (verified against live rendered page, Oct 2026):
  card:     div[data-testid="job-card"]           (data-id / data-job-guid)
  title:    a[data-testid="job-search-job-detail-link"]  -> href /job-detail/...
  company:  p[data-testid="job-card-company-name"]
  location: first <p> containing '•' — "City, State • <when>"
"""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import quote_plus

from bs4 import BeautifulSoup, Tag

from app.models import RawJob, SearchQuery
from app.sources.playwright_source import PlaywrightFetcher

BASE = "https://www.dice.com"
CARD = 'div[data-testid="job-card"]'
TITLE_LINK = 'a[data-testid="job-search-job-detail-link"]'
COMPANY = 'p[data-testid="job-card-company-name"]'
REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)
SALARY_RE = re.compile(r"\$[\d,]+[kK]?\s*[-–]\s*\$[\d,]+[kK]?")


class DiceSource:
    name = "dice"
    uses_browser = True  # Playwright — pinned to the single-thread executor

    def __init__(self, fetcher: PlaywrightFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        params = {
            "q": query.keywords.strip(),
            "pageSize": min(query.limit_per_source, 100),
        }
        if (query.location or "").strip():
            params["location"] = query.location.strip()
        url = f"{BASE}/jobs?" + "&".join(
            f"{k}={quote_plus(str(v))}" for k, v in params.items() if v
        )
        page = self._fetcher.get(
            url, source_name=self.name, wait_selector=CARD, wait_ms=4000
        )
        return parse_listing(page.text)[: query.limit_per_source]


def parse_listing(html: str) -> list[RawJob]:
    """Pure HTML -> RawJob mapping. Testable offline against a fixture."""
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[RawJob] = []
    for card in soup.select(CARD):
        job = _card_to_job(card)
        if job:
            jobs.append(job)
    return jobs


def _card_to_job(card: Tag) -> RawJob | None:
    link = card.select_one(TITLE_LINK)
    if link is None:
        return None
    href = str(link.get("href") or "")
    title = link.get_text(" ", strip=True)
    if not title or not href:
        return None
    loc, when = _loc_and_when(card)
    return RawJob(
        source="dice",
        url=href if href.startswith("http") else BASE + href,
        title=title,
        company=_text(card, COMPANY),
        location=loc,
        salary_raw=_salary(card),
        description="",
        remote=True if REMOTE_RE.search(card.get_text(" ")) else None,
        published_at=when,
        external_id=card.get("data-id") or card.get("data-job-guid"),
    )


def _text(card: Tag, selector: str) -> str | None:
    el = card.select_one(selector)
    return el.get_text(" ", strip=True) if el else None


def _loc_and_when(card: Tag) -> tuple[str | None, str | None]:
    """'Chantilly, Virginia • Today' -> ('Chantilly, Virginia', 'Today')."""
    for p in card.find_all("p"):
        text = p.get_text(" ", strip=True)
        if "•" in text:
            loc, _, when = text.partition("•")
            return loc.strip() or None, when.strip() or None
    return None, None


def _salary(card: Tag) -> str | None:
    m = SALARY_RE.search(card.get_text(" "))
    return m.group(0) if m else None
