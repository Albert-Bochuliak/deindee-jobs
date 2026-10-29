"""Payment-demand signals: job asks candidate to pay anything. Highest weight."""
from __future__ import annotations

import re

from app.models import Job, RuleHit

WEIGHT = 50

PATTERNS = [
    r"страхов(ий|ого)?\s+внес",
    r"внесок\s+(за|для)\s+(навчання|реєстрац)",
    r"оплат\w+\s+(за\s+)?(навчання|курс|тренінг|реєстрац)",
    r"платн\w+\s+(навчання|стажування|реєстрац)",
    r"депозит",
    r"задаток",
    r"купи(ти|ть)\s+(наш|стартов|пакет|комплект|товар)",
    r"викуп",
    r"стартов(ий|ого)\s+(капітал|внесок|пакет)",
    r"training\s+fee",
    r"registration\s+fee",
    r"deposit\s+required",
    r"pay\s+(for|to)\s+(training|start|register)",
    r"investment\s+required",
    r"buy\s+(our|a)\s+(starter|package|kit|product)",
]

_REGEX = re.compile("|".join(PATTERNS), re.IGNORECASE)


class PaymentDemandRule:
    name = "payment_demand"
    weight = WEIGHT

    def check(self, job: Job) -> RuleHit | None:
        m = _REGEX.search(job.description)
        if not m:
            return None
        return RuleHit(rule=self.name, weight=self.weight, reason=f"asks for payment: '{m.group(0)}'")
