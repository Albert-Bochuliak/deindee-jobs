"""Content signals: unrealistic salary, urgency pressure, vague role, MLM vocabulary."""
from __future__ import annotations

import re
import unicodedata

from app.models import Job, RuleHit


class UnrealisticSalaryRule:
    name = "unrealistic_salary"
    weight = 30  # crosses the suspicious threshold on its own
    MONTHLY_USD_CAP = 15000  # above this without senior signals = suspicious
    NO_EXP_HIGH_SALARY_CAP = 5000

    NO_EXPERIENCE = re.compile(
        r"без\s+(досвіду|опыта|experience)|no\s+experience|entry[\s-]level|початків", re.IGNORECASE
    )

    def check(self, job: Job) -> RuleHit | None:
        if job.salary_min is None:
            return None
        # crude normalization: treat UAH ~ /40, EUR ~ *1.1
        usd = job.salary_min
        if job.currency == "UAH":
            usd /= 40
        elif job.currency == "EUR":
            usd *= 1.1
        if self.NO_EXPERIENCE.search(job.description) and usd >= self.NO_EXP_HIGH_SALARY_CAP:
            return RuleHit(rule=self.name, weight=self.weight, reason=f"high salary ({usd:.0f} USD) + 'no experience'")
        if usd >= self.MONTHLY_USD_CAP:
            return RuleHit(rule=self.name, weight=self.weight, reason=f"salary {usd:.0f} USD above market cap")
        return None


class UrgencyPressureRule:
    name = "urgency_pressure"
    weight = 15
    PATTERNS = re.compile(
        r"тільки\s+сьогодні|лише\s+сьогодні|обмежена\s+кількість|встигни|залишилось\s+\d+\s+(місц|вакансій|place|spot)"
        r"|only\s+today|limited\s+(spots?|places?|offer)|act\s+now|hurry",
        re.IGNORECASE,
    )

    def check(self, job: Job) -> RuleHit | None:
        m = self.PATTERNS.search(job.description)
        if m:
            return RuleHit(rule=self.name, weight=self.weight, reason=f"urgency pressure: '{m.group(0)}'")
        return None


class VagueRoleRule:
    name = "vague_role"
    weight = 15
    PATTERNS = re.compile(
        r"робота\s+для\s+(всіх|кожного)|додатковий\s+заробіток|легк(і|ий)\s+(гроші|заробіток)"
        r"|вільний\s+графік[^.]{0,40}(високий|гарний)?\s*(дохід|заробіток)"
        r"|работа\s+для\s+всех|easy\s+(money|income)|work\s+for\s+everyone|no\s+skills\s+required",
        re.IGNORECASE,
    )

    def check(self, job: Job) -> RuleHit | None:
        text = f"{job.title} {job.description}"
        m = self.PATTERNS.search(text)
        if m:
            return RuleHit(rule=self.name, weight=self.weight, reason=f"vague/too-good role: '{m.group(0)}'")
        return None


class MlmPatternRule:
    name = "mlm_pattern"
    weight = 30
    PATTERNS = re.compile(
        r"побудуй\s+сво[юї]\s+команд|будуй\s+команд|мереже\w+\s+маркетинг|сетев(ой|ого)\s+маркетинг"
        r"|пірамід|бінарн(а|ий)\s+система|реферальн(а|ий)\s+(програм|дохід)|network\s+marketing"
        r"|multi[\s-]level|mlm\b|build\s+your\s+(own\s+)?team|passive\s+income\s+guarantee",
        re.IGNORECASE,
    )

    def check(self, job: Job) -> RuleHit | None:
        m = self.PATTERNS.search(job.description)
        if m:
            return RuleHit(rule=self.name, weight=self.weight, reason=f"MLM pattern: '{m.group(0)}'")
        return None


class ShoutyTextRule:
    """Excessive CAPS / emoji / !!! — typical of scam posts."""
    name = "shouty_text"
    weight = 10

    def check(self, job: Job) -> RuleHit | None:
        text = job.description
        if len(text) < 50:
            return None
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return None
        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        exclam = text.count("!") + text.count("!!!") * 2
        emoji = sum(1 for c in text if unicodedata.category(c) in ("So", "Sk"))
        if caps_ratio > 0.4 or exclam >= 6 or emoji >= 8:
            return RuleHit(
                rule=self.name, weight=self.weight,
                reason=f"shouty formatting (caps {caps_ratio:.0%}, !x{exclam}, emoji {emoji})",
            )
        return None
