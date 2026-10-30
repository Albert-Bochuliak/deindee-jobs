# deindee-jobs

> Project knowledge base (Obsidian vault): **`docs/`** — start at
> `docs/Home.md`. Read `docs/Pitfalls.md` before editing related code.

DeIndee Jobs Scraper — full-stack job aggregator. A Python backend scrapes
vacancies from ~15 job boards and APIs, normalizes them, scores each listing
for scam signals, deduplicates and stores results in an in-memory SQLite
run-repo (per-run, RAM-only — jobs.db keeps just settings/blacklist). A React
dashboard lets you browse, filter and trigger scraping runs.

## Features

- **18 sources** — Djinni, DOU/Work.ua RSS, Robota.ua, OLX, Freelancehunt,
  LinkedIn, RemoteOK, Remotive, Arbeitnow, Jobicy, Himalayas, Job Bank (CA),
  Craigslist, Adzuna, Jooble, USAJOBS.
- **Anti-scam scoring** — every job gets a 0–100 scam score (`safe` /
  `suspicious` / `scam`) from a rule pipeline (payment demands, messenger-only
  contact, suspicious company/content signals).
- **Rich filtering** — keyword search, source, salary + currency, level
  (junior/middle/senior), years of experience, language, workplace type,
  countries, remote-only, scam threshold.
- **Background scraping** — `POST /api/scrape` runs asynchronously; the UI
  polls `/api/scrape/status` for live progress.
- **Deduplication** — cross-source duplicate detection before insert.

## Requirements

- **Python** 3.11+ (3.10 should work — `X | None` syntax is used)
- **Node.js** 18+ and npm
- Optional: **Playwright browsers** for JS-heavy sources (LinkedIn, Robota.ua)

## Setup

### Backend (Python)

```bash
# from repo root
python -m venv .venv
.venv\Scripts\activate          # Windows (use `source .venv/bin/activate` on Linux/macOS)
pip install -r requirements.txt

# optional, only needed for playwright-based sources
playwright install chromium

# configure environment
copy .env.example .env          # then fill in API keys you want to use
```

Python dependencies (`requirements.txt`):

| Package            | Purpose                                   |
| ------------------ | ----------------------------------------- |
| `fastapi`          | REST API                                  |
| `uvicorn[standard]`| ASGI server                               |
| `httpx`            | async HTTP client for scrapers            |
| `feedparser`       | RSS sources (DOU, Work.ua)                |
| `beautifulsoup4`   | HTML parsing                              |
| `playwright` + `playwright-stealth` | headless browser sources |
| `pytest`           | test suite                                |

API-key sources are enabled only when their env vars are set (`JOOBLE_API_KEY`,
`ADZUNA_APP_ID`/`ADZUNA_APP_KEY`, `USAJOBS_API_KEY`/`USAJOBS_EMAIL`).
Everything else works keyless.

### Frontend (Node)

```bash
cd frontend
npm install
```

Node dependencies (installed automatically by `npm install`):

- **Runtime** — `react`, `react-dom`, `lucide-react` (icons)
- **Dev** — `vite` + `@vitejs/plugin-react`, `typescript`, `tailwindcss`,
  `postcss`, `autoprefixer`, `@types/react`, `@types/react-dom`

## Running

You need **two** processes — or launch both at once:

```bash
python start.py      # one console, Ctrl+C stops both
.\start.bat          # or: opens API + frontend in two windows
```

### 1. API server — port 8001

```bash
# from repo root, venv activated
uvicorn app.api.server:app --reload --reload-dir app --reload-delay 1 --port 8001
```

> Port **8001** is required — `frontend/vite.config.ts` proxies `/api` there.
> `--reload-dir app` keeps docs/tests/frontend edits from restarting the API
> (a restart wipes live results and can orphan the shared Chromium).
>
> If `uvicorn` isn't found on Windows (Scripts/ not on PATH), use
> `python -m uvicorn app.api.server:app --reload --reload-dir app --reload-delay 1 --port 8001`.

### 2. Frontend dev server — port 5173

```bash
cd frontend
npm run dev
```

Open http://localhost:5173 — the dashboard talks to the API through the Vite
proxy, so no CORS issues.

### CLI scraping (no UI)

```bash
python run_scrape.py --keywords "python" --remote --limit 50
```

### Tests

```bash
pytest
```

## API endpoints

| Method | Path                 | Description                                  |
| ------ | -------------------- | -------------------------------------------- |
| GET    | `/api/jobs`          | paginated job list with all filters          |
| GET    | `/api/stats`         | aggregate stats for the current filter set   |
| GET    | `/api/sources`       | configured sources + sources with data       |
| GET    | `/api/locations`     | distinct countries present in the DB         |
| POST   | `/api/scrape`        | start a background scrape run                |
| GET    | `/api/scrape/status` | `{running, new}` live progress               |
| GET    | `/api/last-report`   | per-source results of the last run           |

## Project structure

```
scrapper.loc/
├── run_scrape.py            # CLI entry point
├── requirements.txt         # Python deps
├── .env.example             # config template (copy to .env)
├── jobs.db                  # SQLite settings/blacklist only — job rows live in :memory: (gitignored, auto-created)
│
├── app/
│   ├── config.py            # env loading, Config dataclass
│   ├── models.py            # Job, SearchQuery, ScrapeReport dataclasses
│   │
│   ├── api/
│   │   └── server.py        # FastAPI app — all /api/* endpoints
│   │
│   ├── sources/             # one module per job board + shared plumbing
│   │   ├── registry.py      # build_sources(config) — enables available sources
│   │   ├── http_source.py   # base class for httpx-based scrapers
│   │   ├── playwright_source.py  # base class for browser-based scrapers
│   │   ├── rss_source.py    # shared RSS feed parsing (feedparser)
│   │   ├── djinni.py, workua.py, robota.py, olx.py, linkedin.py,
│   │   │   jobbank.py, craigslist.py, ...
│   │   └── adzuna.py, jooble.py, usajobs.py  # API-key sources
│   │
│   ├── parsing/
│   │   └── normalize.py     # raw source payload -> unified Job
│   │
│   ├── filters/             # anti-scam rule engine
│   │   ├── registry.py      # build_rules()
│   │   ├── payment_demand.py
│   │   ├── messenger_contact.py
│   │   ├── company_signals.py
│   │   └── content_signals.py
│   │
│   ├── services/
│   │   ├── pipeline.py      # ScraperService — orchestrates a scrape run
│   │   ├── scoring.py       # FilterPipeline — runs rules, assigns score/level
│   │   └── dedup.py         # cross-source deduplication
│   │
│   └── storage/
│       ├── schema.py        # SQLite DDL
│       ├── sqlite_repo.py   # SqliteJobRepository — all DB access
│       ├── query_builder.py # dynamic WHERE for the filter params
│       └── locations.py     # country/city normalization
│
├── frontend/
│   ├── vite.config.ts       # dev server on :5173, /api proxy -> :8001
│   ├── tailwind.config.js, postcss.config.js, tsconfig*.json
│   └── src/
│       ├── main.tsx, App.tsx
│       ├── api/client.ts    # fetch wrappers for /api/*
│       ├── hooks/           # useJobs, useScrape, useDebounce
│       ├── types/job.ts     # Job interface matching backend model
│       ├── utils/storage.ts # persisted UI filter state (localStorage)
│       └── components/
│           ├── ScrapeBar.tsx, StatsBar.tsx
│           ├── jobs/        # JobList, JobCard, JobFilters, Pagination
│           └── ui/          # Badge, ScoreBadge, CheckboxDropdown,
│                            # ClearableInput, Skeleton
│
└── tests/
    ├── fixtures/            # saved HTML listings for parser tests
    └── test_*.py            # parser, filter and salary-parsing tests
```

## Data flow

```
sources/*  --raw-->  parsing/normalize  --Job-->  filters + scoring
      -->  services/dedup  -->  sqlite_repo(":memory:") — live, per-run
                                          |
                              FastAPI /api/*  <--  React UI
```

1. `build_sources(config)` instantiates every source whose prerequisites are
   met (API keys, playwright availability).
2. Each source fetches listings; `Normalizer` maps them to the `Job` model.
3. `FilterPipeline` runs all anti-scam rules → `scam_score`, `scam_level`.
4. `dedup` drops cross-source duplicates; `relevance.py` ranks each job
   against the run keywords; new rows go to in-memory SQLite (wiped on
   each run — direct keyword hits always sort first).
5. The dashboard queries `/api/jobs` with filters translated by
   `query_builder.py` into SQL.
