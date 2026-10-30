"""Launch backend (uvicorn :8001) + frontend (vite :5173) in one console.

Usage:  python start.py     — Ctrl+C stops both processes.
Alternative: .\start.bat    — same thing in two separate windows.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def main() -> None:
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.api.server:app",
         "--reload", "--reload-dir", "app", "--reload-delay", "1",
         "--port", "8001"],
        cwd=ROOT,
    )
    # npm is a .cmd shim on Windows — needs the extension or shell=True
    npm = "npm.cmd" if os.name == "nt" else "npm"
    ui = subprocess.Popen([npm, "run", "dev"], cwd=ROOT / "frontend")

    print("API -> http://localhost:8001  UI -> http://localhost:5173")
    print("Ctrl+C stops both.")
    try:
        api.wait()
        ui.wait()
    except KeyboardInterrupt:
        api.terminate()
        ui.terminate()


if __name__ == "__main__":
    main()
