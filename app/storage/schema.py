"""SQLite DDL — executed once at repository init. Tables only; indexes
live next to their tables. Swap to a migrations runner when this grows."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    salary_min REAL,
    salary_max REAL,
    currency TEXT,
    remote INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    published_at TEXT,
    scraped_at TEXT NOT NULL,
    external_id TEXT,
    content_hash TEXT,
    scam_score INTEGER NOT NULL DEFAULT 0,
    scam_reasons TEXT NOT NULL DEFAULT '[]',
    -- keyword-match rank for the current run; direct hits first
    relevance INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_scam ON jobs(scam_score);
-- idx_jobs_relevance is created in sqlite_repo AFTER the column migration
CREATE TABLE IF NOT EXISTS blacklist (
    company TEXT PRIMARY KEY
);
-- API credentials managed via /admin — DB is the source of truth, .env only a fallback
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""
