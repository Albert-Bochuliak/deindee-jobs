# Architecture

## Data flow

```
sources/*  --raw-->  parsing/normalize  --Job-->  filters + scoring
     -->  services/dedup  -->  sqlite_repo(:memory:) — live, per-run
                                        |
                            FastAPI /api/*  <--  React UI

jobs.db on disk only holds settings/blacklist (persistent admin data);
job rows are RAM-only and wiped on each scrape start.
```

1. `build_sources(config)` instantiates every source whose prerequisites are
   met (API keys present, playwright available).
2. Each source yields raw listings; `Normalizer` maps them to `Job`.
3. `FilterPipeline` runs anti-scam rules -> `scam_score` (0-100), `scam_level`
   (safe <30 / suspicious 30-60 / scam >60, thresholds in `Config`).
4. `dedup` drops cross-source duplicates; new rows -> in-memory SQLite
   (`jobs_repository` in server.py).
5. UI calls `/api/jobs`; `query_builder.build_where()` translates filter
   params into SQL.

## Layer rules

- `app/sources/` — one module per board. Base classes: `http_source.py`
  (httpx), `playwright_source.py` (browser), `rss_source.py` (feedparser).
- `app/parsing/normalize.py` — raw payload -> `Job`; owns `GLOBAL_LOC_MARKERS`.
- `app/filters/` — scam rules; `registry.build_rules()`; see
  `.windsurf/skills/scam-detection/` before adding rules.
- `app/services/` — `pipeline.py` (scrape orchestration), `scoring.py`,
  `dedup.py`.
- `app/storage/` — `schema.py` (DDL), `sqlite_repo.py` (all DB access),
  `query_builder.py` (pure WHERE builder + keyword lookup tables),
  `locations.py` (country/city lookup tables + `extract_countries`).
- `app/api/server.py` — all endpoints; `/api/settings` edits API keys stored
  in the `settings` table.
- `app/config.py` — `Config` dataclass; **DB settings win over .env**
  (`SECRET_KEYS` map env name -> Config field).

## Frontend

- `frontend/src/api/client.ts` — fetch wrappers
- `hooks/` — `useJobs`, `useScrape`, `useDebounce`
- `utils/storage.ts` — persisted filter state (localStorage)
- `components/jobs/` — JobList, JobCard, JobFilters, Pagination

Related: [[Decisions]], [[Pitfalls]], [[Sources]]
