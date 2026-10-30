# deindee-jobs — Project Vault

Job aggregator: Python backend scrapes ~18 job boards, normalizes, scores for
scam, dedups into an in-memory SQLite run-repo (per-run, RAM-only). React
dashboard on top.

This vault exists to preserve context between sessions (human + AI).
Update the notes when behavior or decisions change.

## Map

- [[Architecture]] — data flow, layers, file responsibilities
- [[Decisions]] — ADR-style log of why things are the way they are
- [[Pitfalls]] — bugs we already hit; check BEFORE editing related code
- [[Sources]] — per-source notes: method, keys, quirks
- [[Runbook]] — how to run, ports, test commands
- [[Conventions]] — code style rules this repo follows

## Quick facts

- Backend: Python 3.11+, FastAPI, httpx, feedparser, bs4, playwright
- Frontend: React + TS + Tailwind + Vite (`frontend/`)
- DB: job results in `sqlite3 ":memory:"` (per-run); `jobs.db` file only
  stores settings/blacklist (auto-created, gitignored)
- API port **8001**, Vite dev **5173** (proxy `/api` -> 8001)
- Tests: `pytest` from repo root
- CLI: `python run_scrape.py --keywords "python" --remote --limit 50`
