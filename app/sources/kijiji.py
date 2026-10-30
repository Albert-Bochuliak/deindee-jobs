"""Kijiji Jobs — listing JSON embedded in the SSR search page (verified Oct 2026).

No public API and the RSS endpoints (rss-srp-*) 403. Pages are server-rendered
Next.js and embed the full GraphQL result set:
  script#__NEXT_DATA__ -> props.pageProps.__APOLLO_STATE__["StandardListing:<adId>"]
Each listing carries title/description/url/location/dates plus attributes
(company, location=[province, city], jobtype, jobofferedby).

Search URL: /b-jobs/<slug>/<kw>/k0c45l<locId> — c45 = Jobs category, the slug
is decorative, l<locId> is the real location filter. Canada-only board:
LOCATION_IDS maps query.location -> locId, default 0 = whole country.
"""
from __future__ import annotations

import json
import re
from typing import Iterable
from urllib.parse import quote

from bs4 import BeautifulSoup

from app.models import RawJob, SearchQuery
from app.sources.http_source import HttpFetcher

BASE = "https://www.kijiji.ca"
REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)

# query.location -> kijiji locationId (l<id>). Verified via page titles Oct 2026.
LOCATION_IDS = {
    "canada": 0, "ontario": 9004, "british columbia": 9007, "bc": 9007,
    "alberta": 9003, "manitoba": 9006, "quebec": 9001, "québec": 9001,
    "toronto": 1700273, "montreal": 1700281, "montréal": 1700281,
    "ottawa": 1700184, "calgary": 1700199, "edmonton": 1700203,
    "vancouver": 80003, "winnipeg": 1700192, "quebec city": 1700124,
}
DEFAULT_LOC_ID = 0


class KijijiSource:
    name = "kijiji"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, query: SearchQuery) -> Iterable[RawJob]:
        loc_id = LOCATION_IDS.get(
            (query.location or "").strip().lower(), DEFAULT_LOC_ID
        )
        kw = quote(query.keywords.strip(), safe="")
        url = (
            f"{BASE}/b-jobs/canada/{kw}/k0c45l{loc_id}"
            if kw
            else f"{BASE}/b-jobs/canada/k0c45l{loc_id}"
        )
        response = self._fetcher.get(url, source_name=self.name)
        jobs = parse_listings(response.text)
        if query.remote_only:
            jobs = [j for j in jobs if j.remote]
        return jobs[: query.limit_per_source]


def parse_listings(html: str) -> list[RawJob]:
    """Pure __NEXT_DATA__ -> RawJob mapping. Testable offline against a fixture."""
    tag = BeautifulSoup(html, "html.parser").select_one("script#__NEXT_DATA__")
    if tag is None or not tag.string:
        return []
    state = (
        json.loads(tag.string)
        .get("props", {})
        .get("pageProps", {})
        .get("__APOLLO_STATE__", {})
    )
    jobs: list[RawJob] = []
    for key, listing in state.items():
        if not key.startswith("StandardListing:") or not isinstance(listing, dict):
            continue
        job = _listing_to_job(listing)
        if job:
            jobs.append(job)
    return jobs


def _listing_to_job(v: dict) -> RawJob | None:
    title = (v.get("title") or "").strip()
    url = v.get("url") or ""
    if not title or not url:
        return None
    attrs = {
        a["canonicalName"]: a.get("canonicalValues") or []
        for a in (v.get("attributes") or {}).get("all") or []
        if a.get("canonicalName")
    }
    text = f"{title} {v.get('description') or ''}"
    return RawJob(
        source="kijiji",
        url=url,
        title=title,
        company=_first(attrs.get("company")),
        location=_location(v, attrs),
        salary_raw=None,  # job ads don't carry a wage field
        description=v.get("description") or "",
        remote=True if REMOTE_RE.search(text) else None,
        published_at=v.get("sortingDate") or v.get("activationDate"),
        external_id=str(v.get("id")) if v.get("id") else None,
    )


def _location(v: dict, attrs: dict) -> str | None:
    """attributes.location is [province, city] -> 'City, Province' (region_country
    maps CA provinces). Fallback: location.name / address."""
    loc_vals = attrs.get("location") or []
    if len(loc_vals) >= 2:
        return f"{loc_vals[1]}, {loc_vals[0]}"
    loc = v.get("location") or {}
    return loc.get("name") or loc.get("address") or None


def _first(values: list | None) -> str | None:
    return values[0] if values else None
