"""Company signals: no name, confidential, blacklist."""
from __future__ import annotations

import re

from app.models import Job, RuleHit


class MissingCompanyRule:
    name = "missing_company"
    weight = 20
    CONFIDENTIAL = re.compile(r"конфіденц|confidential|анонім|не\s+вказан|н/д|n/a", re.IGNORECASE)

    def check(self, job: Job) -> RuleHit | None:
        if not job.company:
            return RuleHit(rule=self.name, weight=self.weight, reason="no company name")
        if self.CONFIDENTIAL.search(job.company):
            return RuleHit(rule=self.name, weight=self.weight, reason=f"vague company '{job.company}'")
        return None


class BlacklistCompanyRule:
    """Company name matches the local scam blacklist (storage table)."""

    name = "blacklist_company"
    weight = 60

    def __init__(self, blacklist: set[str] | None = None) -> None:
        self._blacklist = {b.lower() for b in (blacklist or set())}

    def update(self, blacklist: set[str]) -> None:
        self._blacklist = {b.lower() for b in blacklist}

    def check(self, job: Job) -> RuleHit | None:
        if job.company and job.company.lower() in self._blacklist:
            return RuleHit(rule=self.name, weight=self.weight, reason=f"'{job.company}' is blacklisted")
        return None
