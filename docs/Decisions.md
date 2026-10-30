# Decisions

ADR-style log. Newest first. When you change behavior, add an entry —
don't silently edit old ones.

## 2026-10 — Live results in `:memory:` SQLite, not jobs.db

Scrape output is ephemeral per-run data — persisting it made jobs.db
grow unboundedly and forced `delete_matching` hacks to hide stale rows.
`jobs_repository = SqliteJobRepository(":memory:")` serves `/api/jobs`,
`/api/stats`, `/api/sources`, `/api/locations` and the scraper's save();
the file repo keeps only settings/blacklist. Same class → all
`query_builder` filters work unchanged. Each scrape starts with
`clear_jobs()`; the UI clears instantly and streams new cards via the
existing silent-reload polling. Per-user isolation for a real multi-user
deployment = one :memory: repo per session — out of scope for now.

Related fix: `useJobs.reload` is ref-stable (`filtersRef`) — the poll
loop previously held a stale useCallback with `q=""`, so filter q was
silently dropped for the entire run (e.g. "c++" showed everything).
`applyQuery` (keywords -> q filter on run start) was removed: the
per-run repo already IS the answer set, and `LIKE '%c#%'` hid legit
board matches (74 scraped -> 0 shown for "c#"). `clear()` also resets
the stale q so a new run never inherits the old keyword.

Follow-up: boards answer loosely (a "c#" run returns aircraft
mechanics), so the list can't rely on scam_score order alone.
`services/relevance.py` scores each job per run — word-level matches
weighted title > company > description (mirrors build_where's fields,
comma terms = OR) — stored in the `relevance` column; `list_jobs`
orders `relevance DESC` before every sort mode so direct hits always
lead and fuzzy board matches trail behind.

## 2026-10 — Kijiji parses `__APOLLO_STATE__`, not HTML cards

Kijiji Jobs (`c45`) has no public API and RSS (`rss-srp-*`) 403s. SSR
search pages embed full listing objects in
`script#__NEXT_DATA__ .props.pageProps.__APOLLO_STATE__` as
`StandardListing:<adId>` — richer than the visible cards (company,
location, dates) and stable vs. markup churn. Employer comes from the
`company` attribute; location from `location=[province, city]` flipped
to `"City, Province"` so `region_country` maps it to CA. Remote is
detected by regex on title+description (no remote attribute exists).

Also re-verified: Craigslist `format=rss` is still dead (403 for
non-browser clients) — CraigslistSource correctly stays on Playwright.

## 2026-10 — USAJOBS stores full searchable description

`UsaJobsSource` description is now `JobSummary` + `QualificationSummary`
+ `MajorDuties` (`_description()`), not `JobSummary` alone. Cause: the
API's `Keyword` param matches the whole announcement (verified live —
"wordpress" hit only `QualificationSummary` on a "UX Engineer" posting).
Storing only the summary made such rows (a) invisible under the
`q=wordpress` filter and (b) undeletable by `delete_matching`, so each
re-scrape re-counted them as duplicates and they never updated
(`save()` is INSERT-only). Regression coverage:
`tests/test_usajobs_parse.py` asserts all three fields land in
`description`.

## 2026-10 — Playwright sources run on a single-worker pool

Playwright's sync API is greenlet-bound: the shared browser dies with
"Cannot switch to a different thread" if driven from multiple workers.
`pipeline.py` splits tasks by `getattr(source, "uses_browser", False)`:
browser sources (workua, olx, robota, dice, craigslist) go to a dedicated
`ThreadPoolExecutor(max_workers=1)` — serial, but isolated; HTTP sources
keep the parallel pool. Any source taking `PlaywrightFetcher` MUST set
`uses_browser = True` or it silently joins the parallel pool and crashes.

Amendment: the browser pool is created once in `ScraperService.__init__`
(`self._pw_executor`) and never shut down. A per-run pool retires its
worker thread at the end of the run — but that thread OWNS the shared
Chromium (launched lazily on first fetch). Every later run then dies
with "cannot switch to a different thread (which happens to have
exited)" — all browser sources fail, only HTTP ones (USAJOBS etc.)
return results. Keeping the worker alive for the process lifetime keeps
the browser usable across runs.

## 2026-10 — Stale results deleted before each scrape

`server.py` calls `repository.delete_matching(req.keywords)` before
starting a run — otherwise previous runs' rows for the same query keep
showing up next to fresh ones. `delete_matching` mirrors the q-filter
semantics of `build_where` (comma=OR between terms, space=AND of words
across title/description/company) so it removes exactly what the user
would see under that search. It must be kept in sync if the query
grammar ever changes.

## 2026-10 — Location filtering via region suffix tables

Country filter `build_where(countries=...)` emits `%country%` **plus**
`%, <state>` patterns from `locations.country_regions()` (US states + CA
provinces). Reason: USAJOBS/Jobicy save city-level rows like
`"Quantico, Virginia"` — without suffixes they're invisible under a
"United States" filter. Regression test:
`tests/test_location_matches.py::test_countries_sql_includes_state_suffixes`.

`locations.region_country()` is the forward direction (last comma segment
-> country); `country_regions()` is the reverse used by SQL.

## Config precedence: settings table > .env

API keys editable via `/api/settings` are persisted in the `settings` DB
table. `config.SECRET_KEYS` maps env var name -> `Config` field.
DB value wins; `.env` is only the fallback. Don't read `os.getenv`
directly in sources — go through `Config`.

## `query_builder.py` is pure

`build_where()` returns `(sql, params)` and owns ALL filter keyword
lookup tables (`LEVEL_PATTERNS`, `YEAR_RANGES`, `LANG_PATTERNS`,
`HYBRID_PATTERNS`) — they exist only to feed the builder. Keep it
side-effect free: testable without a DB.

## Scam scoring thresholds live in Config

`scam_suspicious_at=30`, `scam_scam_at=60`. `query_builder` duplicates the
30/60 boundary for `scam_level` filtering — if thresholds become
configurable per-request, update both places.

## Dice source: Playwright justified by Cloudflare

dice.com's internal search API 403s plain clients and the page is
JS-rendered, so `DiceSource` uses `PlaywrightFetcher` with
`wait_selector='div[data-testid="job-card"]'`. Markup is data-testid
based (job-card / job-search-job-detail-link / job-card-company-name);
location+date come from the `<p>` containing '•'
("City, State • Today"). Search URL: `/jobs?q=&location=&pageSize=`.
Parser (`parse_listing`) is pure — testable offline.

## Ports are fixed

API must run on **8001** — `frontend/vite.config.ts` proxies `/api` there.
Frontend dev on 5173.

Related: [[Architecture]], [[Pitfalls]]
