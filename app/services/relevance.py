"""Relevance scoring — ranks a run's results against its keywords.

Boards answer loosely (a "c#" query yields aircraft mechanics from
USAJOBS), so the live repo orders by relevance first: direct keyword
hits rise above fuzzy ones. Weighted by where each word landed —
title > company > description — mirroring build_where's fields.
"""
from __future__ import annotations

import re

from app.models import Job
from app.storage.query_builder import word_pattern

# per-word weight by field — a title hit outweighs a buried description hit
_TITLE, _COMPANY, _DESC = 3, 2, 1


def _term_score(term: str, title: str, company: str, desc: str) -> int:
    score = 0
    for word in term.split():
        # same token semantics as build_where's q-filter — 'hr' must not
        # score '$12/hr' or 'per hr' garbage in descriptions
        pat = word_pattern(word)
        if re.search(pat, title, re.IGNORECASE):
            score += _TITLE
        elif re.search(pat, company, re.IGNORECASE):
            score += _COMPANY
        elif re.search(pat, desc, re.IGNORECASE):
            score += _DESC
    return score


def score_relevance(job: Job, keywords: str) -> int:
    """Sum of per-word field weights; comma-separated terms are
    alternatives (OR) — the best-matching term wins, like build_where."""
    terms = [t.strip().lower() for t in keywords.split(",") if t.strip()]
    if not terms:
        return 0
    title = job.title.lower()
    company = (job.company or "").lower()
    desc = job.description.lower()
    return max(_term_score(t, title, company, desc) for t in terms)
