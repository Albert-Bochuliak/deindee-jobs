---
name: scam-detection
description: Anti-scam filtering rules for job listings. Scoring pipeline, rule conventions, signal catalog, thresholds. Use when adding or tuning scam-detection rules in app/filters/.
---

# Scam Detection Skill

## Pipeline model

- Output is a **score 0–100** (0 = clean, 100 = obvious scam), not binary.
- Each rule is a small independent class implementing:

```python
class ScamRule(Protocol):
    name: str
    weight: int          # contribution to score when triggered
    def check(self, job: Job) -> RuleHit | None: ...
```

- Rules register in `app/filters/registry.py`. Adding a rule = new file + registry line. Never an `if/elif` chain.
- `RuleHit` carries `reason: str` — every triggered rule must explain itself for the UI.
- Thresholds live in config: `<30` safe, `30–60` suspicious, `>60` likely scam. Tunable without code changes.

## Signal catalog

### Payment/demand signals (weight 30–50)
- Requests money: deposit, "страховий внесок", training fee, "оплата за навчання", commission upfront.
- Mentions of crypto investment, "фінансовий консультант" + guaranteed income.

### Contact signals (weight 15–30)
- Contact only via Telegram/WhatsApp/DM, no company site.
- Email on free domains (gmail, ukr.net, i.ua) claiming to represent a real company.
- Phone-only posting with no company name.

### Content signals (weight 10–25)
- Salary wildly above market for the role/region (>3x median) or "від 5000$ без досвіду".
- Urgency pressure: "тільки сьогодні", "обмежена кількість місць".
- Vague role: no responsibilities, "робота для всіх", "додатковий заробіток".
- MLM patterns: "побудуй свою команду", "пасивний дохід", network marketing vocabulary.
- Text quality: excessive CAPS, emoji spam, repeated exclamation marks.

### Company signals (weight 15–40)
- No company name or "конфіденційна компанія" + no verifiable site.
- Domain younger than ~6 months (WHOIS check — optional rule, cached).
- Company name appears in known scam-blacklist (local DB table, editable).
- Mismatch: claims big-brand name but posts via free email/unrelated domain.

## Rules for the rules

- Rules read `Job` only — no network calls inside `check()` except explicitly-cached lookups (WHOIS).
- No rule may discard a job; only the pipeline decides by total score.
- Weights are constants at top of each rule file — never magic numbers inside logic.
- A rule must not duplicate another's signal — overlapping evidence is merged in the pipeline, not double-counted.
- Deterministic only: same input → same score. No randomness, no time-dependence except domain-age rule.

## Testing

- Each rule has unit tests: fixture job that triggers, fixture that doesn't.
- Regression corpus in `tests/fixtures/scam/` — real scam examples (sanitized) must keep scoring >60.
