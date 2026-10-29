---
name: scraping
description: Rules for writing job-board scrapers and source integrations in this project. Source protocol, anti-bot handling, rate limits, deduplication, API-first strategy. Use when adding a new job platform or fixing an existing source.
---

# Scraping Skill

## Source priority — always in this order

1. **Official API** (Jooble, Adzuna, Remotive, Arbeitnow) — use it even if fields are limited.
2. **RSS/JSON endpoints** (DOU RSS, RemoteOK JSON) — cheapest reliable option.
3. **HTML scraping** (`httpx` + `BeautifulSoup`) — only when 1–2 unavailable.
4. **Playwright** — last resort, only for JS-rendered/anti-bot sites (LinkedIn, Indeed). Never default to it.

## Source protocol

Every source implements:

```python
class Source(Protocol):
    name: str
    def fetch(self, query: SearchQuery) -> Iterable[RawJob]: ...
```

- `fetch()` yields `RawJob` — raw scraped data, unnormalized.
- Normalization to `Job` happens in `parsing/`, never inside a source.
- One source = one file in `app/sources/`. Register it in `app/sources/registry.py` — no edits elsewhere.

## Anti-bot & etiquette

- Rate limit: min 2s between requests per source; configurable per source.
- `User-Agent` rotation + realistic headers. Retries with exponential backoff (max 3).
- Honor `robots.txt` where feasible; never scrape behind login.
- On HTTP 403/429 — back off and mark source as degraded, don't hammer it.
- Timeouts on every request: 10s connect, 30s read.
- Playwright instances: one browser context per run, always closed in `finally`.

## Error handling

- A failing source MUST NOT crash the pipeline — wrap errors into `SourceError`, log with `source.name` + URL, continue with remaining sources.
- Partial results are valid: yield what was parsed, log what failed.

## Deduplication

- Primary key: normalized canonical URL (strip tracking params: `utm_*`, `fbclid`, etc.).
- Secondary: `sha256(normalized_title + company + location)` for cross-platform dupes.
- Dedup runs once, in `services/` — not inside each source.

## What a source NEVER does

- Never writes to storage directly.
- Never normalizes salary/dates/text — that's `parsing/`.
- Never filters scam — that's `filters/`.
- Never hardcodes secrets — API keys come from config/env.

## Testing

- Each source ships with a saved HTML/JSON fixture and a parse test against it — tests must not hit the network.
