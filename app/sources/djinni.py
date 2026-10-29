"""Djinni — HTML scraping of the public jobs list. No official public API exists.

Markup (verified against live page, Oct 2026):
  container:  div.job-item[id="job-item-<id>"]
  title link: a.job_item__header-link  (note underscore!) -> /jobs/<id>-<slug>/
  title text: h2.job-item__position inside the link
  company:    span.font-weight-500
  meta row:   div.fw-medium — location span.location-text, "Тільки віддалено" for remote,
              salary on list page is only a "$$$$" relative indicator — regex fallback.
  description: div#job-description-<id> with .js-original-text / .js-truncated-text

Selectors keep fallbacks — if a run yields 0 items, save the live page and re-check here.
"""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup, Tag

from app.config import Config
from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher

BASE = "https://djinni.co"
JOB_URL_RE = re.compile(r"/jobs/(\d+)-")   # numeric id in /jobs/<id>-<slug>/
TITLE_LINKS = "a.job_item__header-link, a.job-item__title-link"  # old+new markup
MONEY_RE = re.compile(r"[$€£]\s?\d[\d\s,]*|\d[\d\s,]*\s?(?:USD|EUR|грн|UAH)", re.IGNORECASE)
REMOTE_RE = re.compile(r"віддалено|remote", re.IGNORECASE)


class DjinniSource:
    name = "djinni"

    def __init__(self, fetcher: HttpFetcher, config: Config) -> None:
        self._fetcher = fetcher
        self._url_template = config.djinni_jobs_url

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        # keywords go into the URL template ({kw} placeholder)
        url = self._url_template.format(kw=quote_plus(query.keywords))
        response = self._fetcher.get(url, source_name=self.name)
        return parse_listing(response.text)[: query.limit_per_source]


def parse_listing(html: str) -> list[RawJob]:
    """Pure HTML -> RawJob mapping. Testable offline against a fixture."""
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[RawJob] = []
    for link in soup.select(TITLE_LINKS):
        container = link.find_parent("div", class_="job-item") or link.find_parent("li")
        if container is None:
            continue
        job = _item_to_job(link, container)
        if job:
            jobs.append(job)
    return jobs


def _item_to_job(link: Tag, container: Tag) -> RawJob | None:
    """One card (title link + its container) -> RawJob; None when unparseable."""
    href = link.get("href")
    if not href:
        return None
    # title lives in a dedicated span in new markup; fall back to link text
    title_el = link.select_one(".job-item__position")
    title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
    if not title:
        return None
    url = urljoin(BASE, str(href))
    m = JOB_URL_RE.search(url)
    return RawJob(
        source="djinni",
        url=url,
        title=title,
        company=_company(container),
        location=_location(container),
        salary_raw=_salary(container),
        description=_description(container),
        remote=True if REMOTE_RE.search(container.get_text(" ")) else None,
        external_id=m.group(1) if m else None,
    )


def _company(container: Tag) -> str | None:
    """Try three selectors in order — markup differs between layouts."""
    el = container.select_one("span.font-weight-500")
    if el and el.get_text(strip=True):
        return el.get_text(strip=True)
    details = container.select_one(".list-jobs__details__info")
    if details:
        a = details.find("a")
        if a and a.get_text(strip=True):
            return a.get_text(strip=True)
    a = container.find("a", href=re.compile(r"/companies/"))
    return a.get_text(strip=True) if a else None


def _location(container: Tag) -> str | None:
    el = container.select_one(".location-text")
    return el.get_text(" ", strip=True) if el else None


def _salary(container: Tag) -> str | None:
    """Explicit salary element first; otherwise regex any money-looking text."""
    el = container.select_one(".public-salary-item")
    if el:
        return el.get_text(strip=True)
    m = MONEY_RE.search(container.get_text(" "))
    return m.group(0).strip() if m else None


def _description(container: Tag) -> str:
    el = (
        container.select_one(".js-original-text")
        or container.select_one(".js-truncated-text")
        or container.select_one(".list-jobs__description")
    )
    return el.get_text(" ", strip=True) if el else ""
