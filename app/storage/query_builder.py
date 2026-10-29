"""WHERE-clause builder for job queries.

Pure function — takes filter values, returns (sql, params) over the jobs
table. Keyword lookup tables (level/years/lang/hybrid) live here because
they only exist to feed this builder.
"""
from __future__ import annotations

LEVEL_PATTERNS = {
    "junior": ["junior", "джун", "стаж", "trainee", "intern"],
    "middle": ["middle", "мідл"],
    "senior": ["senior", "сеньор", "сіньор", "lead", "лід", "head"],
}

HYBRID_PATTERNS = ["гібрид", "hybrid", "частково в офісі", "office+remote"]
HYBRID_COLUMNS = ("title", "location", "description")

# Experience in years — option key -> range of years to match in text.
YEAR_RANGES = {
    "0-1": range(0, 2),
    "1-3": range(1, 4),
    "3-5": range(3, 6),
    "5-10": range(5, 11),
    "10+": range(10, 21),
}

LANG_PATTERNS = {
    "en": ["english", "англійськ"],
    "uk": ["ukrainian", "українськ"],
    "pl": ["polish", "польськ"],
    "de": ["german", "німецьк", "deutsch"],
    "fr": ["french", "французьк", "français"],
    "es": ["spanish", "іспанськ", "español"],
    "it": ["italian", "італійськ", "italiano"],
    "pt": ["portuguese", "португальськ"],
    "nl": ["dutch", "нідерландськ", "голландськ"],
    "cs": ["czech", "чеськ"],
}


def _year_patterns(years: range) -> list[str]:
    pats: list[str] = []
    for n in years:
        pats += [
            f"{n}+ year", f"{n} year", f"{n} years",
            f"{n}+ років", f"{n} років", f"{n} рік", f"{n} роки",
        ]
    return pats


def _any_like(columns: tuple[str, ...], patterns: list[str]) -> tuple[str, list[str]]:
    """Build '(col LIKE ? OR col LIKE ? ...)' + params for column×pattern matrix."""
    parts = [f"COALESCE({col}, '') LIKE ?" for col in columns for _ in patterns]
    params = [f"%{p}%" for p in patterns] * len(columns)
    return " OR ".join(parts), params


def build_where(
    query: str | None = None,
    source: str | None = None,
    max_scam: int | None = None,
    scam_level: str | None = None,
    remote_only: bool = False,
    min_salary: float | None = None,
    currency: str | None = None,
    level: str | None = None,
    years: str | None = None,
    lang: str | None = None,
    workplace: str | None = None,
    countries: str | None = None,
) -> tuple[str, list]:
    """SELECT * FROM jobs WHERE 1=1 + one AND-branch per active filter."""
    sql = "SELECT * FROM jobs WHERE 1=1"
    params: list = []
    if query:
        # Comma = OR between terms; spaces inside a term = AND of words.
        # "wordpress, php" -> wordpress OR php; "wordpress php" -> both words.
        terms = [t.strip() for t in query.split(",") if t.strip()]
        if terms:
            groups = []
            for term in terms:
                words = term.split()
                if len(words) > 1:
                    sub = []
                    for w in words:
                        sub.append(
                            "(title LIKE ? OR description LIKE ?"
                            " OR company LIKE ?)"
                        )
                        params += [f"%{w}%"] * 3
                    groups.append("(" + " AND ".join(sub) + ")")
                else:
                    groups.append(
                        "(title LIKE ? OR description LIKE ?"
                        " OR company LIKE ?)"
                    )
                    params += [f"%{term}%"] * 3
            sql += " AND (" + " OR ".join(groups) + ")"
    if source:
        srcs = [s.strip() for s in source.split(",") if s.strip()]
        if srcs:
            sql += f" AND source IN ({','.join('?' * len(srcs))})"
            params += srcs
    if max_scam is not None:
        sql += " AND scam_score <= ?"
        params.append(max_scam)
    if scam_level:
        if scam_level == "safe":
            sql += " AND scam_score < 30"
        elif scam_level == "suspicious":
            sql += " AND scam_score >= 30 AND scam_score <= 60"
        elif scam_level == "scam":
            sql += " AND scam_score > 60"
    if remote_only:
        sql += " AND remote = 1"
    if min_salary is not None:
        sql += " AND COALESCE(salary_min, salary_max) >= ?"
        params.append(min_salary)
    if currency:
        sql += " AND currency = ?"
        params.append(currency)
    if level and (pats := LEVEL_PATTERNS.get(level)):
        clause, p = _any_like(("title", "description"), pats)
        sql += f" AND ({clause})"
        params += p
    if years and (rng := YEAR_RANGES.get(years)):
        clause, p = _any_like(("title", "description"), _year_patterns(rng))
        sql += f" AND ({clause})"
        params += p
    if lang and (pats := LANG_PATTERNS.get(lang)):
        clause, p = _any_like(("title", "description"), pats)
        sql += f" AND ({clause})"
        params += p
    if workplace:
        kinds = {k.strip() for k in workplace.split(",") if k.strip()}
        if kinds:
            clause, p = _any_like(HYBRID_COLUMNS, HYBRID_PATTERNS)
            ors: list[str] = []
            if "remote" in kinds:
                ors.append("remote = 1")
            if "hybrid" in kinds:
                ors.append(f"({clause})")
                params += p
            if "office" in kinds:
                ors.append(f"(remote = 0 AND NOT ({clause}))")
                params += p
            sql += " AND (" + " OR ".join(ors) + ")"
    if countries:
        cs = [c.strip() for c in countries.split(",") if c.strip()]
        if cs:
            sql += " AND (" + " OR ".join("location LIKE ?" for _ in cs) + ")"
            params += [f"%{c}%" for c in cs]
    return sql, params
