"""Rule registry — the ONLY place that knows which rules exist.

Adding a rule = create file in app/filters/ + one line here. Nothing else changes.
"""
from __future__ import annotations

from app.filters.company_signals import BlacklistCompanyRule, MissingCompanyRule
from app.filters.content_signals import (
    MlmPatternRule,
    ShoutyTextRule,
    UnrealisticSalaryRule,
    UrgencyPressureRule,
    VagueRoleRule,
)
from app.filters.messenger_contact import FreeEmailRule, MessengerOnlyContactRule
from app.filters.payment_demand import PaymentDemandRule
from app.models import ScamRule


def build_rules() -> list[ScamRule]:
    return [
        PaymentDemandRule(),
        MessengerOnlyContactRule(),
        FreeEmailRule(),
        UnrealisticSalaryRule(),
        UrgencyPressureRule(),
        VagueRoleRule(),
        MlmPatternRule(),
        ShoutyTextRule(),
        MissingCompanyRule(),
        BlacklistCompanyRule(),
    ]
