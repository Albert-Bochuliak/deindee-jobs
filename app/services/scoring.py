"""FilterPipeline: runs all ScamRules, sums weights, caps at 100. Binary decision stays in config thresholds."""
from __future__ import annotations

from app.config import Config
from app.models import Job, ScamRule


class FilterPipeline:
    def __init__(self, rules: list[ScamRule], config: Config) -> None:
        self._rules = rules
        self._config = config

    def score(self, job: Job) -> Job:
        total = 0
        reasons: list[str] = []
        for rule in self._rules:
            hit = rule.check(job)
            if hit is None:
                continue
            total += hit.weight
            reasons.append(f"{hit.rule}: {hit.reason}")
        job.scam_score = min(total, 100)
        job.scam_reasons = reasons
        return job
