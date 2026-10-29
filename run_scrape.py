"""CLI entry: python run_scrape.py --keywords "python" --remote"""
from __future__ import annotations

import argparse
import logging

from app.config import load_config
from app.filters.registry import build_rules
from app.models import SearchQuery
from app.parsing.normalize import Normalizer
from app.services.pipeline import ScraperService
from app.services.scoring import FilterPipeline
from app.sources.registry import build_sources
from app.storage.sqlite_repo import SqliteJobRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape jobs from all configured sources")
    parser.add_argument("--keywords", default="", help="search keywords")
    parser.add_argument("--location", default="", help="location filter")
    parser.add_argument("--remote", action="store_true", help="remote only")
    parser.add_argument("--limit", type=int, default=50, help="max jobs per source")
    args = parser.parse_args()

    config = load_config()
    repo = SqliteJobRepository(config.db_path)
    service = ScraperService(
        sources=build_sources(config),
        normalizer=Normalizer(),
        pipeline=FilterPipeline(build_rules(), config),
        repository=repo,
    )
    report = service.run(
        SearchQuery(
            keywords=args.keywords,
            location=args.location,
            remote_only=args.remote,
            limit_per_source=args.limit,
        )
    )
    print("\n=== Report ===")
    for name, r in report.per_source.items():
        status = f"error: {r.error}" if r.error else f"fetched={r.fetched} new={r.new} dupes={r.duplicates}"
        print(f"  {name:<12} {status}")
    print(f"  {'TOTAL':<12} new={report.total_new}")
    print("\nStats:", repo.stats())
    repo.close()


if __name__ == "__main__":
    main()
