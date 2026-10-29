"""Offline smoke tests: normalization + scam scoring. No network."""
from __future__ import annotations

from app.config import load_config
from app.filters.registry import build_rules
from app.models import RawJob
from app.parsing.normalize import Normalizer
from app.services.scoring import FilterPipeline

SCAM_RAW = RawJob(
    source="test",
    url="https://example.com/job/1?utm_source=x&fbclid=abc",
    title="Легкий заробіток без досвіду!!!",
    company=None,
    description=(
        "Робота для всіх! Додатковий заробіток. "
        "Пишіть тільки в телеграм. Страховий внесок 50 дол. "
        "Побудуй свою команду. Обмежена кількість місць!"
    ),
)

LEGIT_RAW = RawJob(
    source="test",
    url="https://example.com/job/2",
    title="Senior Python Developer",
    company="TechCorp",
    location="Kyiv / Remote",
    salary_raw="4000-6000 USD",
    description=(
        "We are looking for a Senior Python Developer. "
        "Requirements: 5+ years with Django/FastAPI. "
        "Apply via https://techcorp.example.com/careers"
    ),
    remote=True,
)


def _score(raw: RawJob) -> tuple[int, list[str]]:
    job = Normalizer().normalize(raw)
    scored = FilterPipeline(build_rules(), load_config()).score(job)
    return scored.scam_score, scored.scam_reasons


def test_scam_job_scores_high():
    score, reasons = _score(SCAM_RAW)
    print("scam reasons:", reasons)
    assert score >= 60
    rule_names = {r.split(":")[0] for r in reasons}
    assert "payment_demand" in rule_names
    assert "missing_company" in rule_names


def test_legit_job_scores_low():
    score, reasons = _score(LEGIT_RAW)
    print("legit reasons:", reasons)
    assert score < 30


def test_url_canonicalized():
    job = Normalizer().normalize(SCAM_RAW)
    assert job.url == "https://example.com/job/1"


def test_salary_parsed():
    job = Normalizer().normalize(LEGIT_RAW)
    assert job.salary_min == 4000
    assert job.salary_max == 6000
    assert job.currency == "USD"
