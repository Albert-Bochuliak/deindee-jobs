"""Regression: USAJOBS returned 'Quantico, Virginia' which got dropped by a
'United States' filter — city-level locations must resolve to their country."""
from app.services.pipeline import location_matches
from app.storage.query_builder import build_where


def test_us_state_matches_united_states():
    assert location_matches("Quantico, Virginia", "United States")
    assert location_matches("Austin, Texas", "United States")
    assert location_matches("Quantico, Virginia", "USA")  # alias


def test_ca_province_matches_canada():
    assert location_matches("Toronto, Ontario", "Canada")


def test_different_country_rejected():
    assert not location_matches("Madrid, Spain", "United States")
    assert not location_matches("Berlin, Germany", "Canada")


def test_empty_and_global_pass():
    assert location_matches(None, "United States")
    assert location_matches("", "United States")
    assert location_matches("Remote", "United States")


def test_no_wanted_keeps_everything():
    assert location_matches("Madrid, Spain", "")


def test_countries_sql_includes_state_suffixes():
    """build_where must also LIKE '%, <state>' so city-level rows render
    under a 'United States' filter (saved USAJOBS rows were invisible)."""
    _sql, params = build_where(countries="United States")
    assert "%United States%" in params
    assert "%, virginia" in params  # LIKE is case-insensitive on ASCII
    assert "%, texas" in params


def test_countries_sql_unknown_country_unchanged():
    _sql, params = build_where(countries="Spain")
    assert params == ["%Spain%"]
