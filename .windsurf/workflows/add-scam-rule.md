---
description: Checklist for adding a new anti-scam detection rule, following the scam-detection skill
---

# Add a new scam-detection rule

Read `.windsurf/skills/scam-detection/SKILL.md` first. Every rule is a small independent class — no edits to other rules or pipeline internals.

## 1. Define the signal

- [ ] Articulate exactly what scam pattern the rule detects, in one sentence.
- [ ] Confirm it does NOT duplicate an existing rule — check `app/filters/` first. Overlapping evidence is merged by the pipeline, not double-counted.
- [ ] Pick a weight from the catalog ranges: payment signals 30–50, contact 15–30, content 10–25, company 15–40.

## 2. Create the rule file

- [ ] New file: `app/filters/<signal_name>.py` (snake_case).
- [ ] Class implements `ScamRule` protocol: `name: str`, `weight: int`, `check(self, job: Job) -> RuleHit | None`.
- [ ] `WEIGHT` is a constant at the top of the file — no magic numbers inside `check()`.
- [ ] `check()` returns `RuleHit(reason=...)` with a human-readable explanation for the UI, or `None` if clean.
- [ ] Rule only reads `Job` fields — no network calls (except explicitly cached lookups like WHOIS).
- [ ] Deterministic: same input → same result. No randomness, no `datetime.now()` except domain-age rule.

## 3. Register

- [ ] Add the rule class to `app/filters/registry.py` — the ONLY file that knows about all rules.

## 4. Tests

- [ ] Fixture job that triggers the rule → `check()` returns `RuleHit`, expected reason string.
- [ ] Fixture job that does NOT trigger → returns `None`.
- [ ] If rule targets a real scam pattern — add sanitized example to `tests/fixtures/scam/` and assert the pipeline scores it above its threshold.

## 5. Verify

// turbo
- [ ] Run: `pytest tests/ -k filters`
- [ ] Manually score a few real jobs — confirm no spike of false positives on legitimate listings.

## Forbidden during this workflow

- Binary accept/reject inside a rule — only the pipeline threshold decides.
- Editing thresholds in `check()` — they live in config.
- Keyword lists hardcoded inline in logic — extract to a named constant at file top.
