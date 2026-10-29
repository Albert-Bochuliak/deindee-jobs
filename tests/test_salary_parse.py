"""parse_salary: yearly amounts are normalized to monthly (÷12)."""
from app.parsing.normalize import parse_salary


def test_monthly_range_unchanged():
    assert parse_salary("$3,000–$6,000") == (3000, 6000, "USD")


def test_yearly_range_divided_by_12():
    assert parse_salary("$50,000 — $150,000/year") == (4167, 12500, "USD")


def test_yearly_single_per_year():
    assert parse_salary("60000 USD per year") == (5000, 5000, "USD")


def test_yearly_ukrainian():
    assert parse_salary("240000 грн в рік") == (20000, 20000, "UAH")


def test_monthly_unchanged_uah():
    assert parse_salary("25 000 – 75 000 грн") == (25000, 75000, "UAH")
