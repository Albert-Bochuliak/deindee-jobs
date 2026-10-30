"""Job Bank (Canada) — server-rendered HTML search, no key needed for scraping.

Official API exists (jobbank.api.gc.ca) but requires free registration; this
source uses the plain-HTML search page instead — markup verified live Oct 2026:

  GET /jobsearch/jobsearch?searchstring=<kw>&locationstring=<city>
  card:      article (id="article-<postingId>")
  link:      a.resultJobItem -> /jobsearch/jobposting/<id>;jsessionid=..?source=..
  title:     h3.title span.noctitle
  telework:  h3 span.telework -> "On site" | "Hybrid" | "Remote"
  meta:      li.date | li.business (company) | li.location | li.salary
"""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher

BASE = "https://www.jobbank.gc.ca"
SEARCH_URL = f"{BASE}/jobsearch/jobsearch"
CARD = "article"
POSTING_RE = re.compile(r"/jobsearch/jobposting/(\d+)")
REMOTE_RE = re.compile(r"remote|telework|hybrid", re.IGNORECASE)


class JobBankSource:
    name = "jobbank"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        # server-side keyword + location search
        params = {"searchstring": query.keywords}
        if query.location:
            params["locationstring"] = query.location
        response = self._fetcher.get(
            SEARCH_URL, params=params, source_name=self.name
        )
        jobs = parse_listing(response.text)
        if query.remote_only:
            jobs = [j for j in jobs if j.remote]
        return jobs[: query.limit_per_source]


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
    link = card.select_one("a.resultJobItem")
    title_el = card.select_one("span.noctitle")
    if link is None or title_el is None:
        return None
    href = str(link.get("href") or "")
    # drop ;jsessionid and ?source=searchresults -> canonical posting URL
    url = urljoin(BASE, href.split(";")[0].split("?")[0])
    m = POSTING_RE.search(href)
    telework = card.select_one("span.telework")
    return RawJob(
        source="jobbank",
        url=url,
        title=title_el.get_text(strip=True),
        company=_li_text(card, "business"),
        location=_li_text(card, "location"),
        salary_raw=_li_text(card, "salary"),
        description="",
        remote=True if telework and REMOTE_RE.search(telework.get_text()) else None,
        published_at=_li_text(card, "date"),
        external_id=m.group(1) if m else (card.get("id") or None),
    )


def _li_text(card: Tag, cls: str) -> str | None:
    """Text of li.<cls> inside the card, minus icon/label noise."""
    el = card.select_one(f"li.{cls}")
    if el is None:
        return None
    # icon spans carry no visible text we want; strip wb-inv screen-reader bits
    for junk in el.select("span.wb-inv, span.fa, span.fas"):
        junk.decompose()
    text = el.get_text(" ", strip=True)
    # li.salary renders "Salary $49.00 hourly" — drop the literal label
    return re.sub(r"^Salary\s+", "", text) or None
