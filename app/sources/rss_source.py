"""Generic RSS-feed source. DOU and Work.ua reuse it with different URL templates."""
from __future__ import annotations

import logging
from typing import Iterable
from urllib.parse import quote_plus

import feedparser

from app.models import RawJob, SearchQuery, SourceError
from app.sources.http_source import HttpFetcher

logger = logging.getLogger(__name__)


class RssSource:
    """Fetches a feed URL built from a template containing {kw} for keywords."""

    name = "rss"

    def __init__(self, fetcher: HttpFetcher, feed_url_template: str, name: str) -> None:
        self._fetcher = fetcher
        self._template = feed_url_template
        self.name = name

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        url = self._template.format(kw=quote_plus(query.keywords))
        response = self._fetcher.get(url, source_name=self.name)
        feed = feedparser.parse(response.content)
        # bozo = parse error; only fatal when it produced zero entries too
        if feed.bozo and not feed.entries:
            raise SourceError(f"[{self.name}] failed to parse feed {url}: {feed.bozo_exception}")
        jobs: list[RawJob] = []
        for entry in feed.entries[: query.limit_per_source]:
            jobs.append(
                RawJob(
                    source=self.name,
                    url=entry.get("link") or "",
                    title=entry.get("title") or "",
                    company=self._company(entry),
                    description=entry.get("summary") or "",
                    published_at=entry.get("published") or entry.get("updated"),
                    external_id=entry.get("id"),
                )
            )
        return jobs

    @staticmethod
    def _company(entry: dict) -> str | None:
        # DOU feeds expose author as company sometimes; keep whatever exists.
        author = entry.get("author")
        return author if author and "@" not in author else None


def build_rss_sources(fetcher: HttpFetcher, dou_url: str, workua_url: str) -> list[RssSource]:
    """Two RSS feeds share this class — DOU and Work.ua with own templates."""
    return [
        RssSource(fetcher, dou_url, name="dou"),
        RssSource(fetcher, workua_url, name="workua"),
    ]
