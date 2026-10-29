"""Cross-platform deduplication: canonical URL first, content hash as fallback."""
from __future__ import annotations

from app.models import Job
from app.parsing.normalize import content_hash


class Deduplicator:
    def __init__(self) -> None:
        self._seen_urls: set[str] = set()
        self._seen_hashes: set[str] = set()

    def seen(self, job: Job) -> bool:
        if job.url and job.url in self._seen_urls:
            return True
        chash = content_hash(job)
        if chash in self._seen_hashes:
            return True
        if job.url:
            self._seen_urls.add(job.url)
        self._seen_hashes.add(chash)
        return False
