"""Contact signals: only messenger contact, free email claiming a real company."""
from __future__ import annotations

import re

from app.models import Job, RuleHit

MESSENGER_ONLY_WEIGHT = 25
FREE_EMAIL_WEIGHT = 20

MESSENGER_ONLY = re.compile(
    r"(контакт|зв'язок|пишіть|пиши|резюме|cv|відгук|звертайтеся|details|apply|contact)"
    r"[^.\n]{0,60}(тільки|лише|only|via|through|in|у|в|к)"
    r"[^.\n]{0,30}(telegram|телеграм|whatsapp|ватсап|viber|вайбер|сигнал|signal)",
    re.IGNORECASE,
)
FREE_EMAIL = re.compile(
    r"[a-z0-9._%+-]+@(gmail|yahoo|hotmail|outlook|ukr\.net|i\.ua|mail\.ru|yandex|meta\.ua|bk\.ru|list\.ru|inbox\.ru)"
    r"\.(com|net|ua|ru|org)",
    re.IGNORECASE,
)
HAS_CORPORATE_SITE = re.compile(r"https?://", re.IGNORECASE)


class MessengerOnlyContactRule:
    name = "messenger_only_contact"
    weight = MESSENGER_ONLY_WEIGHT

    def check(self, job: Job) -> RuleHit | None:
        if not MESSENGER_ONLY.search(job.description):
            return None
        if HAS_CORPORATE_SITE.search(job.description):
            return None  # messenger + real site = probably fine
        return RuleHit(rule=self.name, weight=self.weight, reason="contact only via messenger, no site")


class FreeEmailRule:
    name = "free_email"
    weight = FREE_EMAIL_WEIGHT

    def check(self, job: Job) -> RuleHit | None:
        m = FREE_EMAIL.search(job.description)
        if not m:
            return None
        if not job.company:
            return RuleHit(rule=self.name, weight=self.weight, reason=f"free email {m.group(0)}, no company")
        return RuleHit(
            rule=self.name,
            weight=self.weight // 2,
            reason=f"'{job.company}' uses free email {m.group(0)}",
        )
