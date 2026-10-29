"""Core domain models. Dataclasses only — nothing dict-shaped crosses layer boundaries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SearchQuery:
    keywords: str = ""
    location: str = ""
    remote_only: bool = False
    limit_per_source: int = 50


@dataclass
class RawJob:
    """Exactly what a source returned. Sources must NOT normalize anything."""

    source: str
    url: str
    title: str
    company: str | None = None
    location: str | None = None
    salary_raw: str | None = None
    description: str = ""
    remote: bool | None = None
    published_at: str | None = None
    external_id: str | None = None


@dataclass
class Job:
    """Normalized, deduplicated, scored job — the unit the API serves."""

    id: str
    source: str
    url: str
    title: str
    company: str | None
    location: str | None
    salary_min: float | None
    salary_max: float | None
    currency: str | None
    remote: bool
    description: str
    published_at: str | None
    external_id: str | None = None
    scam_score: int = 0
    scam_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RuleHit:
    rule: str
    weight: int
    reason: str


class SourceError(Exception):
    """The only exception type allowed to escape a Source."""


class Source(Protocol):
    name: str

    def fetch(self, query: SearchQuery) -> "list[RawJob]": ...


class ScamRule(Protocol):
    name: str
    weight: int

    def check(self, job: Job) -> RuleHit | None: ...


class JobRepository(Protocol):
    def save(self, job: Job) -> bool: ...
    def list_jobs(
        self,
        query: str | None = None,
        source: str | None = None,
        max_scam: int | None = None,
        remote_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Job]: ...
    def stats(self) -> dict: ...
