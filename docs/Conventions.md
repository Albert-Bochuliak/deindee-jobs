# Conventions

Style rules observed in this codebase. Follow them — don't import habits
from other projects.

## Python

- `from __future__ import annotations`; `X | None` unions (3.10+ syntax OK)
- Dataclasses for models (`app/models.py`) and config
- **Pure functions + lookup tables** for logic that's testable without IO
  (`query_builder.py`, `locations.py`, `services/relevance.py`); IO stays in
  `sqlite_repo.py`,
  `server.py`, `pipeline.py`
- Minimal `.env` loader in `config.py` — no python-dotenv dependency
- Docstrings explain *why*, one line at module top describing responsibility
- Params always bound (`?` placeholders) — never f-string user input into SQL
  (lookup-table keys are the exception)

## Tests

- `tests/fixtures/` holds saved HTML for parser tests — don't fetch live
- Filter/query tests assert on `(sql, params)` pairs, not a real DB

## Frontend

- React + TS, Tailwind classes inline; `lucide-react` for icons
- Shared primitives in `components/ui/` — reuse before creating new ones
- Filter state persists via `utils/storage.ts` (localStorage)

## Workflow for AI assistants

- `.windsurf/skills/` — domain rules (scraping, scam-detection, frontend,
  backend). Read the matching skill BEFORE implementing.
- `.windsurf/workflows/` — checklists (`/add-source`, `/add-scam-rule`)
- This vault — read [[Pitfalls]] and [[Decisions]] before editing the
  areas they cover; append new entries when behavior changes.

Related: [[Architecture]]
