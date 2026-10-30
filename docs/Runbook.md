# Runbook

## Run the app (two processes)

```powershell
# API — must be port 8001 (vite proxy target)
# --reload-dir app: only backend code restarts the API (docs/tests/UI edits don't)
uvicorn app.api.server:app --reload --reload-dir app --reload-delay 1 --port 8001

# Frontend — port 5173
cd frontend; npm run dev
```

Open http://localhost:5173.

## CLI scrape (no UI)

```powershell
python run_scrape.py --keywords "python" --remote --limit 50
```

## Tests

```powershell
pytest                      # full suite, from repo root
pytest tests/test_location_matches.py -v
```

## Setup from scratch

```powershell
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium   # only for LinkedIn/Robota.ua
copy .env.example .env        # fill API keys (optional)
cd frontend; npm install
```

## Endpoints

| Method | Path                 | Purpose                          |
| ------ | -------------------- | -------------------------------- |
| GET    | `/api/jobs`          | paginated list, all filters      |
| GET    | `/api/stats`         | aggregates for current filters   |
| GET    | `/api/sources`       | configured + populated sources   |
| GET    | `/api/locations`     | distinct countries in DB         |
| GET/POST | `/api/settings`    | API-key management (masked GET)  |
| POST   | `/api/scrape`        | start background scrape          |
| POST   | `/api/scrape/stop`   | cooperative stop (keeps saved)   |
| GET    | `/api/scrape/status` | `{running, new, stopped}` progress |
| GET    | `/api/last-report`   | per-source results of last run   |

## Troubleshooting
 
- **Empty job list with a country filter** -> [[Pitfalls#Locations]]
- **Source not running** -> check keys in `settings` table AND `.env`;
  playwright sources need the browser installed
- **CORS errors** -> frontend must go through the vite proxy; API on 8001
