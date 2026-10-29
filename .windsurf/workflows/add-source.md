---
description: Checklist for adding a new job-platform source, following the scraping skill
---

# Add a new job source

Follow these steps in order. The scraping skill rules apply throughout — read `.windsurf/skills/scraping/SKILL.md` first.

## 1. Research the platform

- [ ] Check for an official API (preferred). If exists — get docs, note required API key → goes to env config, never hardcoded.
- [ ] If no API — check for RSS/JSON endpoints (view page source, DevTools Network tab).
- [ ] If neither — plan HTML scraping with `httpx` + `BeautifulSoup`.
- [ ] Playwright ONLY if the page is JS-rendered or behind anti-bot. Justify in a comment why.
- [ ] Check `robots.txt` and note rate-limit needs.

## 2. Create the source file

- [ ] New file: `app/sources/<platform>.py` (snake_case platform name).
- [ ] Class implements the `Source` protocol: `name: str` class attribute + `fetch(self, query: SearchQuery) -> Iterable[RawJob]`.
- [ ] `fetch()` yields `RawJob` objects only — NO normalization, NO salary parsing, NO scam logic, NO storage writes.
- [ ] Set a per-source `RATE_LIMIT_SECONDS` constant (min 2s default).
- [ ] All requests have timeouts (10s connect / 30s read), `User-Agent` headers, and retry with exponential backoff (max 3).
- [ ] Errors wrapped into `SourceError` — never leak source-specific exceptions, never crash the pipeline.
- [ ] No hardcoded URLs/tokens — base URL and keys come from `config.py` / env.

## 3. Register the source

- [ ] Add the class to `app/sources/registry.py` — this must be the ONLY file outside `app/sources/` that knows about the new source.

## 4. Tests & fixtures

- [ ] Save a real response sample to `tests/fixtures/sources/<platform>.(html|json)`.
- [ ] Write a parse test against the fixture — MUST NOT hit the network.
- [ ] Test edge cases: empty results page, missing salary field, missing company name.

## 5. Verify end-to-end

// turbo
- [ ] Run the test suite: `pytest tests/ -k <platform>`
- [ ] Run a manual fetch with a small query and confirm jobs appear in storage without crashes.
- [ ] Confirm dedup works — run twice, second run must not duplicate records.

## Forbidden during this workflow

- Editing other sources' code (Open/Closed — new source must not require it).
- Adding normalization logic inside the source.
- Committing API keys or credentials.
