"""Work.ua — Playwright-rendered HTML scraping of the public jobs list.

Work.ua returns 403 to plain HTTP (anti-bot), so requests go through
PlaywrightFetcher (headless Chromium + stealth). Page markup is classic
server-rendered HTML, so parsing itself is plain BeautifulSoup.

Markup (verified against live rendered page, Oct 2026):
  card:        div.card.job-link   (also .card-hover. wordwrap)
  title link:  h2 a[href^="/jobs/<id>/"]
  salary row:  div.text-indent containing span.glyphicon-hryvnia-fill -> span.strong-600
  company row: div.text-indent containing span.glyphicon-company     -> span.strong-600
  location row:div.text-indent containing span.glyphicon-map-marker  -> own text
  requirements:div.text-indent containing span.glyphicon-list        -> "Досвід…"
  description: p.ellipsis
"""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup, Tag

from app.models import RawJob, SearchQuery
from app.sources.playwright_source import PlaywrightFetcher

BASE = "https://www.work.ua"
CARD = "div.card.job-link"
JOB_URL_RE = re.compile(r"/jobs/(\d+)/")
REMOTE_RE = re.compile(r"віддален|remote|дистанц", re.IGNORECASE)

# City name (uk/en, lowercase) -> work.ua URL slug.
CITY_SLUGS = {
    "київ": "kyiv", "kyiv": "kyiv", "kiev": "kyiv",
    "львів": "lviv", "lviv": "lviv",
    "харків": "kharkiv", "kharkiv": "kharkiv",
    "одеса": "odesa", "odesa": "odesa", "odessa": "odesa",
    "дніпро": "dnipro", "dnipro": "dnipro", "днепр": "dnipro",
    "запоріжжя": "zaporizhzhya", "вінниця": "vinnitsya",
    "черкаси": "cherkassy", "полтава": "poltava",
    "чернігів": "chernigov", "суми": "sumy",
    "ужгород": "uzhgorod", "рівне": "rovno", "тернопіль": "ternopil",
    "івано-франківськ": "ivano-frankovsk", "луцьк": "lutsk",
    "хмельницький": "khmelnytskyy", "чернівці": "chernivtsy",
    "миколаїв": "nikolaev", "кривий ріг": "kryvyy-rig",
    "ukraine": "", "україна": "", "remote": "",
}


class WorkUaSource:
    name = "workua"

    def __init__(self, fetcher: PlaywrightFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        url = self._search_url(query)
        page = self._fetcher.get(
            url, source_name=self.name, wait_selector=CARD, wait_ms=3000
        )
        return parse_listing(page.text)[: query.limit_per_source]

    @staticmethod
    def _search_url(query: SearchQuery) -> str:
        """/jobs-<city>-<kw>/ — city omitted for Ukraine-wide / unknown."""
        kw = quote_plus(query.keywords.strip())
        loc = (query.location or "").strip().lower()
        city = CITY_SLUGS.get(loc, "")
        if city:
            # /jobs-kyiv-python/
            return f"{BASE}/jobs-{city}-{kw}/" if kw else f"{BASE}/jobs-{city}/"
        return f"{BASE}/jobs-{kw}/" if kw else f"{BASE}/jobs/"


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
    """One div.card -> RawJob; None when the job link is missing."""
    link = card.select_one("h2 a[href^='/jobs/']")
    if link is None:
        return None
    title = link.get_text(strip=True)
    href = str(link.get("href") or "")
    if not title or not href:
        return None
    url = urljoin(BASE, href)
    m = JOB_URL_RE.search(url)
    card_text = card.get_text(" ")
    return RawJob(
        source="workua",
        url=url,
        title=title,
        company=_company(card),
        location=_row_value(card, "glyphicon-map-marker"),
        salary_raw=_salary(card),
        description=_description(card),
        remote=True if REMOTE_RE.search(card_text) else None,
        external_id=m.group(1) if m else None,
    )


def _row_value(card: Tag, glyph: str) -> str | None:
    """Text of a div.text-indent that starts with a specific glyphicon."""
    for row in card.select("div.text-indent"):
        if row.select_one(f"span.{glyph}"):
            text = row.get_text(" ", strip=True)
            return text or None
    return None


def _company(card: Tag) -> str | None:
    """Company = span.strong-600 inside the glyphicon-company row."""
    for row in card.select("div.text-indent"):
        if row.select_one("span.glyphicon-company"):
            el = row.select_one("span.strong-600")
            if el and el.get_text(strip=True):
                return el.get_text(strip=True)
    return _row_value(card, "glyphicon-company")


def _salary(card: Tag) -> str | None:
    """Salary = hryvnia-icon row's strong text (or the whole row)."""
    for row in card.select("div.text-indent"):
        if row.select_one("span.glyphicon-hryvnia-fill"):
            el = row.select_one("span.strong-600")
            return el.get_text(strip=True) if el else row.get_text(strip=True)
    return None


def _description(card: Tag) -> str:
    """Snippet paragraph + requirements row joined into one text."""
    parts: list[str] = []
    el = card.select_one("p.ellipsis")
    if el:
        parts.append(el.get_text(" ", strip=True))
    req = _row_value(card, "glyphicon-list")
    if req:
        parts.append(req)
    return " ".join(parts)
