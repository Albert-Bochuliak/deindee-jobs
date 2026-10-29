"""SQLite implementation of JobRepository. Swap for Postgres later — call sites unchanged."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone

from app.models import Job
from app.storage.locations import extract_countries
from app.storage.query_builder import build_where
from app.storage.schema import SCHEMA

class SqliteJobRepository:
    def __init__(self, db_path: str) -> None:
        # shared across FastAPI handler + scrape-worker threads: one connection
        # needs a lock — a commit() must never run while another thread's
        # SELECT cursor is mid-fetch (would raise OperationalError -> 500)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # -- locked query helpers -----------------------------------------------
    # Reads never touch _conn directly — one place owns the lock.
    # save() keeps its own lock because execute+commit must stay atomic.

    def _query(self, sql: str, params: list | tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def _query_one(self, sql: str, params: list | tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute(sql, params).fetchone()

    def save(self, job: Job) -> bool:
        """Insert if new. Returns True when inserted, False when dedup hit."""
        try:
            with self._lock:
                self._conn.execute(
                    """INSERT INTO jobs
                       (id, source, url, title, company, location, salary_min, salary_max,
                        currency, remote, description, published_at, scraped_at,
                        external_id, content_hash, scam_score, scam_reasons)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        job.id, job.source, job.url, job.title, job.company, job.location,
                        job.salary_min, job.salary_max, job.currency, int(job.remote),
                        job.description, job.published_at,
                        datetime.now(tz=timezone.utc).isoformat(), job.external_id,
                        job.id[2:] if job.id.startswith("h_") else None,
                        job.scam_score, json.dumps(job.scam_reasons, ensure_ascii=False),
                    ),
                )
                self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def list_jobs(
        self,
        query: str | None = None,
        source: str | None = None,
        max_scam: int | None = None,
        scam_level: str | None = None,
        remote_only: bool = False,
        min_salary: float | None = None,
        currency: str | None = None,
        level: str | None = None,
        years: str | None = None,
        lang: str | None = None,
        workplace: str | None = None,
        countries: str | None = None,
        sort: str = "score",
        limit: int = 50,
        offset: int = 0,
    ) -> list[Job]:
        sql, params = build_where(
            query=query, source=source, max_scam=max_scam, scam_level=scam_level,
            remote_only=remote_only, min_salary=min_salary, currency=currency,
            level=level, years=years, lang=lang, workplace=workplace,
            countries=countries,
        )
        order = (
            "published_at DESC, scraped_at DESC"
            if sort == "newest"
            else "scam_score ASC, scraped_at DESC"
        )
        sql += f" ORDER BY {order} LIMIT ? OFFSET ?"
        params += [limit, offset]
        return [self._row_to_job(r) for r in self._query(sql, params)]

    def stats(
        self,
        query: str | None = None,
        source: str | None = None,
        remote_only: bool = False,
        min_salary: float | None = None,
        currency: str | None = None,
        level: str | None = None,
        years: str | None = None,
        lang: str | None = None,
        workplace: str | None = None,
        countries: str | None = None,
    ) -> dict:
        # Same filters as list_jobs, minus the scam-related ones —
        # the cells themselves are the scam distribution.
        sql, params = build_where(
            query=query, source=source, remote_only=remote_only,
            min_salary=min_salary, currency=currency, level=level,
            years=years, lang=lang, workplace=workplace,
            countries=countries,
        )
        inner = sql.replace("SELECT *", "SELECT scam_score, source")
        row = self._query_one(
            f"""SELECT COUNT(*) AS total,
                       SUM(CASE WHEN scam_score < 30 THEN 1 ELSE 0 END) AS safe,
                       SUM(CASE WHEN scam_score BETWEEN 30 AND 60 THEN 1 ELSE 0 END) AS suspicious,
                       SUM(CASE WHEN scam_score > 60 THEN 1 ELSE 0 END) AS scam
                FROM ({inner})""",
            params,
        )
        # per-source counts ignore the source filter so all chips stay visible
        sql_ns, params_ns = build_where(
            query=query, remote_only=remote_only,
            min_salary=min_salary, currency=currency, level=level,
            years=years, lang=lang, workplace=workplace,
            countries=countries,
        )
        inner_ns = sql_ns.replace("SELECT *", "SELECT source")
        rows = self._query(
            f"SELECT source, COUNT(*) AS n FROM ({inner_ns}) GROUP BY source",
            params_ns,
        )
        by_source = {r["source"]: r["n"] for r in rows}
        return {
            "total": row["total"],
            "safe": row["safe"] or 0,
            "suspicious": row["suspicious"] or 0,
            "scam": row["scam"] or 0,
            "by_source": by_source,
        }

    def list_sources(self) -> list[str]:
        return [r["source"] for r in self._query("SELECT DISTINCT source FROM jobs")]

    def list_countries(self) -> list[str]:
        """Distinct country names from job locations — logic in locations.py."""
        rows = self._query(
            "SELECT DISTINCT location FROM jobs"
            " WHERE location IS NOT NULL AND location != ''"
        )
        return extract_countries(row["location"] for row in rows)

    def blacklist(self) -> set[str]:
        return {r["company"] for r in self._query("SELECT company FROM blacklist")}

    @staticmethod
    def _row_to_job(r: sqlite3.Row) -> Job:
        return Job(
            id=r["id"], source=r["source"], url=r["url"], title=r["title"],
            company=r["company"], location=r["location"],
            salary_min=r["salary_min"], salary_max=r["salary_max"], currency=r["currency"],
            remote=bool(r["remote"]), description=r["description"] or "",
            published_at=r["published_at"], external_id=r["external_id"],
            scam_score=r["scam_score"], scam_reasons=json.loads(r["scam_reasons"]),
        )

    def close(self) -> None:
        self._conn.close()
