"""Normalization: RawJob -> Job. Single source of truth for text/salary/url cleanup."""
from __future__ import annotations

import hashlib
import html
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.models import Job, RawJob

# Query params dropped from URLs so tracking variants dedupe to one job.
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "ref"}
TAG_RE = re.compile(r"<[^>]+>")        # any HTML tag
SPACE_RE = re.compile(r"\s+")          # runs of whitespace incl. NBSP
# Range salary: "$2 000 - $3 500", "3000-5000 USD", "2 000 до 3 000 грн".
# Groups: cur/cur2 — symbol before each bound, cur3 — trailing currency.
SALARY_RANGE_RE = re.compile(
    r"(?P<cur>\$|€|£|usd|uah|eur|грн|дол|\$)?\s*"
    r"(?P<lo>\d[\d\s,]*)\s*(?:[-–—]|to|до)\s*(?P<cur2>\$|€|£|usd|uah|eur|грн|дол)?\s*(?P<hi>\d[\d\s,]*)"
    r"\s*(?P<cur3>usd|uah|eur|\$|€|грн|дол\.?|долларов)?",
    re.IGNORECASE,
)
# Markers of yearly (not monthly) pay — amounts are divided by 12.
YEARLY_RE = re.compile(
    r"/\s*(?:year|yr|annum)\b|per\s+(?:year|annum)\b|\bannually\b|\bp\.?\s*a\.\b"
    r"|\b(?:рік|року|год)\b",
    re.IGNORECASE,
)
# Single figure: "$4000" or "4000 USD". Groups: cur+amt prefix form,
# amt2+cur4 postfix form.
SALARY_SINGLE_RE = re.compile(
    r"(?P<cur>\$|€|£|usd|uah|eur|грн|дол)\s*(?P<amt>\d[\d\s,]*)|(?P<amt2>\d[\d\s,]*)\s*(?P<cur4>usd|uah|eur|грн|дол\.?)",
    re.IGNORECASE,
)
# Raw currency token -> ISO code.
CURRENCY_MAP = {
    "$": "USD", "usd": "USD", "дол": "USD", "долларов": "USD",
    "€": "EUR", "eur": "EUR",
    "£": "GBP",
    "uah": "UAH", "грн": "UAH",
}


class Normalizer:
    """Converts RawJob into a normalized, dedup-keyed Job."""

    def normalize(self, raw: RawJob) -> Job:
        # every text field is cleaned the same way; optional fields stay None
        url = canonicalize_url(raw.url)
        title = clean_text(raw.title)
        company = clean_text(raw.company) if raw.company else None
        location = clean_text(raw.location) if raw.location else None
        description = strip_html(raw.description)
        lo, hi, currency = parse_salary(raw.salary_raw)
        return Job(
            id=make_id(url, title, company, location),
            source=raw.source,
            url=url,
            title=title,
            company=company,
            location=location,
            salary_min=lo,
            salary_max=hi,
            currency=currency,
            remote=detect_remote(raw),
            description=description,
            published_at=raw.published_at,
            external_id=raw.external_id,
        )


def canonicalize_url(url: str) -> str:
    """Deterministic URL: lowercase scheme/host, no tracking params, no
    fragment, no trailing slash — so the same listing dedupes by id."""
    if not url:
        return url
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if k.lower() not in TRACKING_PARAMS
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") or parts.path,
         urlencode(query), "")
    )


def clean_text(text: str | None) -> str:
    """Unescape entities and collapse whitespace; "" for missing input."""
    if not text:
        return ""
    return SPACE_RE.sub(" ", html.unescape(text)).strip()


def strip_html(text: str) -> str:
    """Remove tags (kept as spaces so words don't glue), then clean_text."""
    if not text:
        return ""
    no_tags = TAG_RE.sub(" ", text)
    return clean_text(no_tags)


def parse_salary(raw: str | None) -> tuple[float | None, float | None, str | None]:
    """Parse raw salary text -> (min, max, currency), monthly figures.

    Ranges are normalized to lo<=hi; yearly amounts are divided by 12.
    Unparsable/negotiable strings return all-None.
    """
    if not raw:
        return None, None, None
    text = raw.strip()
    # "dohodu" — PL marker for negotiable pay ("… do dohodu"), not a number
    if not text or "dohodu" in text.lower():
        return None, None, None
    m = SALARY_RANGE_RE.search(text)
    if m:
        lo = _num(m.group("lo"))
        hi = _num(m.group("hi"))
        # prefer trailing currency, then infix, then leading
        cur = _cur(m.group("cur3") or m.group("cur2") or m.group("cur"))
        if lo and hi:
            lo, hi = min(lo, hi), max(lo, hi)  # sources write "5000-3000" too
            if YEARLY_RE.search(text):
                lo, hi = round(lo / 12), round(hi / 12)
            return (lo, hi, cur)
    yearly = bool(YEARLY_RE.search(text))
    m = SALARY_SINGLE_RE.search(text)
    if m:
        amt = _num(m.group("amt") or m.group("amt2"))
        cur = _cur(m.group("cur") or m.group("cur4"))
        if amt:
            lo = hi = amt
            if yearly:
                lo = hi = round(amt / 12)
            return (lo, hi, cur)
    return None, None, None


# Locations that don't tie a job to one country.
GLOBAL_LOC_MARKERS = (
    "remote", "worldwide", "anywhere", "global", "віддалено",
    "удаленно", "дистанційно",
)


def detect_remote(raw: RawJob) -> bool:
    """Source flag wins; otherwise keyword-match title/location/description head."""
    if raw.remote is not None:
        return raw.remote
    # first 500 chars of description — remote is usually stated upfront
    haystack = f"{raw.title} {raw.location or ''} {raw.description[:500]}".lower()
    return any(kw in haystack for kw in ("remote", "віддален", "удаленн", "віддалена"))


def make_id(url: str, title: str, company: str | None, location: str | None) -> str:
    """Stable dedup key: "u_" + url hash, or "h_" + title|company|location
    hash for sources that don't provide a URL."""
    if url:
        return "u_" + hashlib.sha256(url.encode()).hexdigest()[:24]
    basis = "|".join(
        [_norm(title), _norm(company or ""), _norm(location or "")]
    )
    return "h_" + hashlib.sha256(basis.encode()).hexdigest()[:24]


def content_hash(job: Job) -> str:
    basis = "|".join([_norm(job.title), _norm(job.company or ""), _norm(job.location or "")])
    return hashlib.sha256(basis.encode()).hexdigest()


def _num(text: str | None) -> float | None:
    """Turn '2 500,50' into 2500.5 — strips spaces/commas, keeps digits/dots."""
    if not text:
        return None
    digits = re.sub(r"[^\d.]", "", text.replace(" ", "").replace(",", ""))
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def _cur(text: str | None) -> str | None:
    """Currency token -> ISO code via CURRENCY_MAP (None when unknown)."""
    if not text:
        return None
    return CURRENCY_MAP.get(text.lower().rstrip("."))


def _norm(text: str) -> str:
    """Lowercased, whitespace-collapsed text for hash bases."""
    return SPACE_RE.sub(" ", text.lower()).strip()
