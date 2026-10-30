"""OLX.ua — Playwright-rendered scraping of the jobs section (olx.ua/rabota).

OLX is a JS-rendered SPA; plain HTTP returns a shell without cards, so
requests go through PlaywrightFetcher.

Markup (verified against live rendered page, Oct 2026):
  card:      div[data-cy="l-card"]  (id attr = numeric ad id)
  title/a:   a[data-testid="card-title-link"]  -> /uk/obyavlenie/...-IDxxxx.html
  company:   <p> sibling right after the title link ("composse ai")
  salary:    <p> matching money regex ("50 000 - 60 000 грн.")
  location:  last location-ish <p> in the card meta row ("Київ, Шевченківський")

Emotion css-* classes are unstable — selectors prefer data-* attributes and
structural fallbacks.
"""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup, Tag

from app.models import RawJob, SearchQuery
from app.sources.playwright_source import PlaywrightFetcher

BASE = "https://www.olx.ua"
CARD = "div[data-cy='l-card']"
TITLE_LINK = "a[data-testid='card-title-link']"
MONEY_RE = re.compile(r"\d[\d\s]*(?:[-–]\s*\d[\d\s]*)?\s*(?:грн|\$|USD|EUR|€)", re.IGNORECASE)
REMOTE_RE = re.compile(r"віддален|remote|дистанційн", re.IGNORECASE)
DATE_RE = re.compile(
    r"\d{2}:\d{2}|сьогодні|вчора|\d{2}\s\w+\.?\s?р\.|\d{2}\s\w+\s\d{4}",
    re.IGNORECASE,
)


class OlxSource:
    name = "olx"
    uses_browser = True  # Playwright — pinned to the single-thread executor

    def __init__(self, fetcher: PlaywrightFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        url = self._search_url(query)
        # wait for at least one card — SPA renders them via XHR after load
        page = self._fetcher.get(
            url, source_name=self.name, wait_selector=CARD, wait_ms=4000
        )
        return parse_listing(page.text)[: query.limit_per_source]

    @staticmethod
    def _search_url(query: SearchQuery) -> str:
        # /uk/rabota/q-<kw>/?search%5Bdescription%5D=1 searches body too
        kw = query.keywords.strip()
        slug = quote(kw.replace(" ", "-").lower()) if kw else "all"
        url = f"{BASE}/uk/rabota/q-{slug}/"
        if query.location and query.location.lower() not in ("ukraine", "україна"):
            url += f"?search%5Bfilter_enum_city%5D%5B0%5D={quote(query.location.strip().lower())}"
        return url


# Freelance "I offer a service" ads, not employer vacancies — filter them out.
SERVICE_AD_RE = re.compile(
    r"розробк(а|у)|доробк|верстк|створенн|доработк|верстка|создани[ея]|"
    r"ленд[иіi]нг|landing\s*page|під\s*ключ|под\s*ключ|на\s*годину|"
    r"поддержк|підтримк|програм[іи]ст\s+на\s+годину|сайтів|сайт\s+під|магазин[уиі]?",
    re.IGNORECASE,
)
# If the title ALSO asks for a specialist, it's a demand ad — keep it.
JOB_MARKER_RE = re.compile(
    r"потріб(ен|на|но)|требуется|нужен|шукаєм|ищем|розробник|девелопер|developer|"
    r"інженер|engineer|спеціаліст|specialist|аналітик|тестувальник|qa\b|адміністратор|"
    r"маркетолог|менеджер|дизайнер|вакансі|vacancy|запрошуємо|hire",
    re.IGNORECASE,
)


def _is_service_ad(title: str) -> bool:
    """True when the OLX title reads like a service offer, not a vacancy."""
    return bool(SERVICE_AD_RE.search(title)) and not JOB_MARKER_RE.search(title)


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
    title = link.get_text(strip=True)
    href = str(link.get("href") or "")
    if not title or not href:
        return None
    url = urljoin(BASE, href.split("?")[0])
    card_text = card.get_text(" ")
    return RawJob(
        source="olx",
        url=url,
        title=title,
        company=_company(card, link),
        location=_location(card),
        salary_raw=_salary(card),
        description="",
        remote=True if REMOTE_RE.search(card_text) else None,
        external_id=card.get("id") or _ad_id(href),
    )


def _ad_id(href: str) -> str | None:
    """Fallback ad id from the -IDxxxx.html slug tail."""
    m = re.search(r"-([A-Za-z0-9]{6,})\.html", href)
    return m.group(1) if m else None


# salary-ish strings — used to reject price/date <p>s as company names
NOT_COMPANY_RE = re.compile(r"грн|договірн|зп|зарплат", re.IGNORECASE)


def _company(card: Tag, link: Tag) -> str | None:
    # <div><a title-link/><p>company</p></div> — sibling p after the link.
    # Price/date-looking p values are not company names.
    sib = link.find_next_sibling("p")
    if sib is not None and _looks_like_meta(sib.get_text()):
        sib = None
    if sib and sib.get_text(strip=True):
        return sib.get_text(strip=True)
    for p in link.parent.find_next_siblings("p") if link.parent else []:
        text = p.get_text(strip=True)
        if text and not _looks_like_meta(text):
            return text
    return None


def _looks_like_meta(text: str) -> bool:
    """True for <p> content that's a date, price, or salary marker."""
    return bool(
        DATE_RE.search(text)
        or MONEY_RE.search(text)
        or NOT_COMPANY_RE.search(text)
    )


def _salary(card: Tag) -> str | None:
    m = MONEY_RE.search(card.get_text(" "))
    return m.group(0).strip() if m else None


def _location(card: Tag) -> str | None:
    # City text lives inside span.css-pnkc9g next to the pin <svg>.
    el = card.select_one("span.css-pnkc9g")
    if el and el.get_text(strip=True):
        return el.get_text(strip=True)
    # Fallback: last short <p> that is neither money, remote tag nor a date.
    cands = [
        p.get_text(" ", strip=True)
        for p in card.select("p")
        if 2 < len(p.get_text(strip=True)) < 60
        and not MONEY_RE.search(p.get_text())
        and not REMOTE_RE.search(p.get_text())
        and not DATE_RE.search(p.get_text())
    ]
    return cands[-1] if cands else None
