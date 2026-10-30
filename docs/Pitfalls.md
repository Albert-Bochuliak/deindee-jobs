# Pitfalls

Bugs and traps already hit. Check the relevant entry BEFORE touching that
area — these are the mistakes an LLM (or tired human) repeats.

## Locations

- **Country filter must include state/province suffixes.** Rows saved as
  `"City, Virginia"` never match `location LIKE '%United States%'`. Always
  go through `country_regions()` — never hand-write a single LIKE for
  countries. (See [[Decisions#2026-10 — Location filtering via region suffix tables]])
- **`location_matches()` semantics:** empty wanted location matches
  everything; `"Remote"` wanted also matches everything. Don't "fix" this
  — it's intentional (`tests/test_location_matches.py`).
- **Last comma segment is the country** in `extract_countries()`, but
  `NON_COUNTRIES` (US states, Kyiv districts, "emea"/"latam") and strings
  with digits/`+();` are rejected. Adding a country name? Check both
  `KNOWN_COUNTRIES` and `NON_COUNTRIES` for conflicts — `"europe"` is in
  both on purpose (kept in KNOWN, filtered via GLOBAL_LOC_MARKERS usage).

## SQL / filters

- **Nullable columns need `COALESCE` in LIKE.** `_any_like` wraps every
  column as `COALESCE(col, '') LIKE ?` — NULL never matches LIKE. Keep the
  pattern when adding columns.
- **Multi-word keyword term = AND of words; comma = OR of terms.**
  `"wordpress php"` requires both words somewhere; `"wordpress, php"` is
  OR. Don't flatten this logic.
- **`salary_min` may be NULL** — min-salary filter uses
  `COALESCE(salary_min, salary_max)`.
- **`scam_level` boundaries are inclusive-exclusive:** safe <30,
  suspicious 30-60 (both ends), scam >60. Off-by-one here is a silent
  misclassification.
- **Entity-escaped markup survives strip order.** `strip_html` must
  `html.unescape` BEFORE `TAG_RE` — arbeitnow ships `&lt;p&gt;&lt;span
  data-contrast=…&gt;` in JSON; unescaping after stripping turned it into
  literal `<p>` text rendered in cards. The unescape loop (≤3 passes)
  also covers double-escaped `&amp;lt;`.

## Sources

- **Playwright sync API is greenlet-bound — one thread only.** Driving
  the shared browser from several workers kills it with "Cannot switch
  to a different thread". Pipeline pins `uses_browser = True` sources
  (workua, olx, robota, dice, craigslist) to a single-worker executor.
  Forgetting the flag on a new PlaywrightFetcher source = intermittent
  crashes under parallel load. (See [[Decisions#2026-10 — Playwright sources run on a single-worker pool]])
- **The browser pool must outlive the run — it owns the Chromium
  thread.** A per-run `with ThreadPoolExecutor(1)` retires its worker
  when the run ends, orphaning the lazily-launched browser: run 2+
  shows "(which happens to have exited)" and ALL browser sources fail
  (search "works" but only USAJOBS-grade noise returns). `self._pw_executor`
  in `ScraperService.__init__` keeps the owner thread alive forever.
- **LinkedIn uses plain HTTP**, not the browser — only the five
  `uses_browser` sources need `playwright install chromium`. They're
  skipped/fail silently if the browser isn't installed.
- **`delete_matching` still mirrors `build_where`'s q-filter** but the
  API no longer calls it — live runs use `clear_jobs()` on the `:memory:`
  repo instead. It survives for file-backed CLI usage; if the keyword
  grammar changes in `query_builder`, update it too.
- **Dice markup is data-testid based**; location/date live in the `<p>`
  containing '•'. Its API 403s non-browser clients — don't "optimize"
  it to HttpFetcher.
- **API-key sources no-op without keys** (Jooble, Adzuna, USAJOBS).
  Keys may live in the `settings` table, not `.env` — check both when
  "source isn't running".
- **USAJOBS `Keyword` matches the whole announcement**, but we only used
  to store `JobSummary`. Rows whose keyword hit `QualificationSummary` /
  `MajorDuties` were invisible under the q-filter AND undeletable by
  `delete_matching` — permanent "ghost" duplicates. `_description()` must
  keep joining all three fields; don't trim it back. (See
  [[Decisions#2026-10 — USAJOBS stores full searchable description]])
- **Kijiji has no API and its RSS endpoints 403** — listings come from
  `__NEXT_DATA__.__APOLLO_STATE__` (SSR page, works with plain httpx).
  URL path segments are decorative; category is `c45` in `k0c45l<id>` and
  `l<id>` is the real location filter — `LOCATION_IDS` verified against
  page titles (Vancouver=80003, NOT the intuitive 1700297 which is
  Skeena-Bulkley). Job ads have no wage field → salary_raw stays None.
- **Rate limiting is global** (`RATE_LIMIT_SECONDS`, default 2s). Don't
  add per-source sleeps on top; tune the config.

## Storage / live mode

- **New-column indexes go after the migration, not in SCHEMA.**
  `CREATE INDEX idx_jobs_relevance` inside SCHEMA crashed startup on
  legacy jobs.db — the `relevance` column doesn't exist until the
  `ALTER TABLE` runs. Any future column: ALTER first, index second.
- **`:memory:` repo is per-process AND per-run.** API restart = empty
  list (expected, not data loss); each scrape starts with
  `clear_jobs()`. jobs.db on disk only holds settings/blacklist —
  don't look for scraped rows there.
- **Mid-run the list shows fuzzy sources first.** `relevance` ordering
  can only rank what has already landed — USAJOBS mechanics lead until
  Dice finishes. Don't "fix" mid-run order; it self-corrects.
- **Poll loops need a ref-stable reload.** `useJobs.reload` reads
  `filtersRef.current` — a plain `useCallback([debouncedFilters])`
  gave the scrape poll a stale `q=""` closure and silently dropped
  the keyword filter for the whole run.
- **Abbreviation keywords need token matching, not substring.**
  `LIKE '%hr%'` / `word in text` matched "hr" inside `$12/hr`, `per hr`,
  `13 hr` — a "HR" search returned transcription-rate jobs. `word_pattern()`
  in `query_builder` gives ≤3-char words `\w`-boundaries and hr its own
  hour-context blacklist (`/hr`, `per hr`, `N hr`); `col REGEXP ?` runs it
  via a `regexp()` UDF registered in `SqliteJobRepository.__init__`, and
  `relevance.score_relevance` uses the same patterns. Longer words keep
  substring semantics on purpose (python3 == python). Feed-only sources
  (remoteok, jobicy, himalayas, freelancehunt, arbeitnow — no server
  search) had the same `kw in haystack` bug: 'hr' passed 'three',
  'through', '$45/hr' — they now call `matches_keywords()` from
  query_builder (comma=OR, space=AND). New feed sources must use it too.
- **Scrape polling must append, not re-sort.** `reload({append})` merges
  by `job.id` into the END of the list — a plain `setJobs(freshList)`
  every 1.5s re-sorted by relevance and made the whole grid flicker.
  Canonical sort applies ONCE after the run (final non-append reload).
- **`--reload` without `--reload-dir` watches the whole repo** — an
  edit to docs/tests/frontend restarts the API mid-scrape: live
  `:memory:` results wipe, the run dies. Launchers pin
  `--reload-dir app --reload-delay 1`; keep them.
- **Killed `start.py` leaves spawn workers holding :8001.** uvicorn
  `--reload` children are `multiprocessing.spawn` python.exe procs — their
  CommandLine contains no "uvicorn"/"start.py", so a cmdline-filtered kill
  misses them and they keep the listen socket + OLD code (stale API without
  new endpoints/fields). Kill by port owner
  (`Get-NetTCPConnection -LocalPort 8001 -State Listen`) or every python
  `spawn_main` child, not by name match. Symptom: `/api/scrape/status`
  responds but lacks freshly added keys.
- **`--reload` fires on every save — including broken mid-refactor states.**
  A `try:` added in one save and its `finally:` in the next leaves a
  SyntaxError file in between; WatchFiles reloads it, the worker dies on
  import, API goes ERR_CONNECTION_REFUSED until a good save lands. The
  reloader respawns on the next fix — but any transient bad save = outage.
  Keep multi-part edits to one write, or expect a brief dead window.
- **Replaced/reloaded scrapers must be `close()`d.** The shared
  Chromium is orphaned on every uvicorn reload and every
  `save_settings` rebuild — the lifespan hook and the settings
  endpoint call `scraper.close()` (skipped if a scrape holds the
  lock; close would block behind in-flight fetches). fetcher.close()
  runs ON the pool worker via submit — never call it from the
  handler thread.

## Process

- **`_dbg_jobicy.py` and `_tmp_dice_inspect.py` are throwaway debug
  scripts** — not part of the app; don't import from them.
- Run `pytest` from repo root after touching `query_builder`,
  `locations`, or `normalize` — most regressions surface there.

Related: [[Decisions]], [[Sources]]
