"""Robota.ua — Playwright-rendered scraping of the Angular SPA.

The whole site is behind Cloudflare (403 for plain HTTP) and the vacancy
list is client-rendered, so requests go through PlaywrightFetcher.

URL format (verified live, Oct 2026): /zapros/<kw>/<region-slug>
  e.g. https://robota.ua/zapros/python/ukraine  — no trailing slash works.

Markup (verified against live rendered DOM):
  card:     a.card[href*='/vacancy']  (href = /company<id>/vacancy<id>)
  title:    h2.santa-typo-h3
  meta row: div.santa-mb-10.santa-flex.santa-items-center right after title —
            its spans hold [company, city, "(віддалено)"]
  labels:   status chips e.g. "Віддалена робота", "Гаряча"
  description: long <p>/<div> text after the benefits chips
"""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup, Tag

from app.models import RawJob, SearchQuery
from app.sources.playwright_source import PlaywrightFetcher

BASE = "https://robota.ua"
CARD = "a.card[href*='/vacancy']"
TITLE = "h2.santa-typo-h3"
META_ROW = "div.santa-mb-10.santa-flex.santa-items-center"
VACANCY_ID_RE = re.compile(r"/vacancy(\d+)")
MONEY_RE = re.compile(r"\d[\d\s]*(?:[-–]\s*\d[\d\s]*)?\s*(?:грн|\$|USD|EUR|€)", re.IGNORECASE)
REMOTE_RE = re.compile(r"віддален|remote|дистанційн", re.IGNORECASE)
# status chips that can sit inside the meta row — not company/location
BADGE_SUBSTRINGS = ("гаряч", "відгукн", "відзнак", "відповіли")

CITY_SLUGS = {
    "київ": "kiev", "kyiv": "kiev", "kiev": "kiev",
    "львів": "lviv", "lviv": "lviv",
    "харків": "kharkov", "kharkiv": "kharkov",
    "одеса": "odessa", "odesa": "odessa", "odessa": "odessa",
    "дніпро": "dnepr", "dnipro": "dnepr", "днепр": "dnepr",
    "запоріжжя": "zaporozhye", "вінниця": "vinnitsa",
    "ukraine": "ukraine", "україна": "ukraine", "remote": "ukraine",
}


class RobotaUaSource:
    name = "robota"
    uses_browser = True  # Playwright — pinned to the single-thread executor

    def __init__(self, fetcher: PlaywrightFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        url = self._search_url(query)
        # Angular renders cards late — 6s settle time, card wait_selector
        page = self._fetcher.get(
            url, source_name=self.name, wait_selector=CARD, wait_ms=6000
        )
        return parse_listing(page.text)[: query.limit_per_source]

    @staticmethod
    def _search_url(query: SearchQuery) -> str:
        """/zapros/<kw>/<region-slug>; unknown locations fall back to Ukraine."""
        kw = quote(query.keywords.strip() or "all")
        loc = (query.location or "").strip().lower()
        region = CITY_SLUGS.get(loc, "ukraine")
        return f"{BASE}/zapros/{kw}/{region}"


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
    """One a.card element -> RawJob; None when title/link missing."""
    title_el = card.select_one(TITLE)
    href = str(card.get("href") or "")
    if title_el is None or not href:
        return None
    title = title_el.get_text(strip=True)
    if not title:
        return None
    url = urljoin(BASE, href)
    m = VACANCY_ID_RE.search(url)
    card_text = card.get_text(" ")
    company, location = _meta(card)
    return RawJob(
        source="robota",
        url=url,
        title=title,
        company=company,
        location=location,
        salary_raw=_salary(card),
        description=_description(card, title),
        remote=True if REMOTE_RE.search(card_text) else None,
        external_id=m.group(1) if m else None,
    )


def _meta(card: Tag) -> tuple[str | None, str | None]:
    """First span in the meta row = company; the rest = location bits."""
    for row in card.select(META_ROW):
        texts = [s.get_text(strip=True) for s in row.select("span")]
        texts = [
            t for t in texts
            if t and not any(b in t.lower() for b in BADGE_SUBSTRINGS)
        ]
        if texts:
            loc_bits = list(dict.fromkeys(texts[1:]))  # dedupe, keep order
            loc = " ".join(loc_bits) or None
            if loc:
                # "(віддалено) (віддалено) Київ" -> "(віддалено) Київ"
                loc = re.sub(r"(\(віддалено\)\s*)+", "(віддалено) ", loc).strip()
            return texts[0], loc
    return None, None


def _salary(card: Tag) -> str | None:
    m = MONEY_RE.search(card.get_text(" "))
    return m.group(0).strip() if m else None


def _description(card: Tag, title: str) -> str:
    # The snippet is the longest plain text block after title/meta/benefits.
    texts = [
        el.get_text(" ", strip=True)
        for el in card.select("p, div.santa-typo-secondary")
        if len(el.get_text(strip=True)) > 60 and title not in el.get_text()
    ]
    return max(texts, key=len) if texts else ""
