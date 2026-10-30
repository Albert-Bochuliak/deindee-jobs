@echo off
rem Launch backend (:8001) + frontend (:5173) in separate console windows.
rem Run from repo root. Close a window to stop that process.
cd /d "%~dp0"

start "jobs-api" cmd /k "if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat & uvicorn app.api.server:app --reload --reload-dir app --reload-delay 1 --port 8001"
start "jobs-ui" cmd /k "cd frontend && npm run dev"

echo Open http://localhost:5173 once both windows are up.
