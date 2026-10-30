"""Relevance scoring + ordering: direct keyword hits must lead the list."""
from app.models import Job
from app.services.relevance import score_relevance
from app.storage.query_builder import matches_keywords
from app.storage.sqlite_repo import SqliteJobRepository


def _job(title: str, company: str | None = None, description: str = "",
         job_id: str = "j1") -> Job:
    return Job(
        id=job_id, source="test", url=f"https://x/{job_id}", title=title,
        company=company, location=None, salary_min=None, salary_max=None,
        currency=None, remote=False, description=description,
        published_at=None,
    )


def test_no_keywords_scores_zero():
    assert score_relevance(_job("C# Developer"), "") == 0


def test_no_match_scores_zero():
    assert score_relevance(_job("Aircraft Mechanic"), "c#") == 0


def test_title_hit_beats_company_and_description():
    title = score_relevance(_job("C# Developer"), "c#")
    company = score_relevance(_job("Engineer", company="C# Systems"), "c#")
    desc = score_relevance(_job("Engineer", description="requires c# skills"), "c#")
    assert title > company > desc > 0


def test_each_word_scores_independently():
    # "c# developer": title word hit (3) vs title+desc word hits (3+1)
    partial = score_relevance(_job("C# Engineer"), "c# developer")
    full = score_relevance(_job("C# Engineer", description="developer role"), "c# developer")
    assert full > partial


def test_comma_terms_take_best_match():
    # OR semantics like build_where — the best term wins, not the sum
    job = _job("C# Developer")
    assert score_relevance(job, "java, c#") == score_relevance(job, "c#")


def test_case_insensitive():
    assert score_relevance(_job("C# DEVELOPER"), "c#") > 0


def test_hr_abbreviation_not_matched_inside_hour_rate():
    # 'hr' in '$12/hr', 'per hr', '13 hr' means hour, not human resources
    for junk_desc in (
        "Up to $12/hr remote work",
        "compensation per hr negotiable",
        "rate 13 hr USD",
    ):
        assert score_relevance(_job("Transcription Expert", description=junk_desc), "hr") == 0
    assert score_relevance(_job("HR Manager"), "hr") > 0


def test_repo_query_hr_skips_hour_rate_rows():
    repo = SqliteJobRepository(":memory:")
    junk = _job("Transcription Expert", description="Up to $12/hr", job_id="junk")
    real = _job("HR Manager", job_id="real")
    repo.save(junk)
    repo.save(real)
    hits = repo.list_jobs(query="hr")
    assert [j.id for j in hits] == ["real"]


def test_repo_orders_relevance_first():
    repo = SqliteJobRepository(":memory:")
    fuzzy = _job("Aircraft Mechanic", job_id="f1")
    fuzzy.relevance = 0
    direct = _job("C# Developer", job_id="d1")
    direct.relevance = 3
    partial = _job("Engineer", description="some c# work", job_id="p1")
    partial.relevance = 1
    for j in (fuzzy, direct, partial):  # inserted scrambled on purpose
        assert repo.save(j)
    listed = repo.list_jobs()
    assert [j.id for j in listed] == ["d1", "p1", "f1"]


# -- matches_keywords: feed-only sources (remoteok/jobicy/himalayas/
#    freelancehunt/arbeitnow) used `kw in haystack` — 'hr' hit 'three' --

def test_matches_keywords_hr_not_in_three_or_rate():
    assert not matches_keywords("We grow through three phases", "hr")
    assert not matches_keywords("Rate: $45/hr, weekly", "hr")
    assert matches_keywords("HR Generalist, remote", "hr")


def test_matches_keywords_term_semantics():
    # comma = OR, space = AND — same as build_where/score_relevance
    assert matches_keywords("HR Manager", "python, hr")
    assert not matches_keywords("HR Manager", "python, java")
    assert matches_keywords("Senior Python Dev", "senior python")
    assert not matches_keywords("Senior Python Dev", "senior java")


def test_matches_keywords_empty_passes():
    assert matches_keywords("anything", "")
