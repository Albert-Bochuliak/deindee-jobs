from pathlib import Path

from app.sources.linkedin import parse_listing

FIXTURE = Path(__file__).parent / "fixtures" / "linkedin_listing.html"


def _jobs():
    return parse_listing(FIXTURE.read_text(encoding="utf-8"))


def test_parse_cards():
    jobs = _jobs()
    assert len(jobs) == 2


def test_first_job_fields():
    job = _jobs()[0]
    assert job.source == "linkedin"
    assert job.title == "Senior Python Developer IRC307341"
    assert job.company == "GlobalLogic"
    assert job.location == "Kyiv, Kyiv City, Ukraine"
    assert job.external_id == "4481901446"
    assert job.published_at == "2026-10-23"
    # tracking params stripped
    assert job.url == (
        "https://ua.linkedin.com/jobs/view/"
        "senior-python-developer-at-globallogic-4481901446"
    )


def test_remote_location_and_missing_company():
    job = _jobs()[1]
    assert job.remote is True
    assert job.company is None


def test_empty_html_returns_empty():
    assert parse_listing("") == []
