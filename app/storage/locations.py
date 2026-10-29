"""Country extraction for list_countries().

Lookup tables + pure function — the repository only supplies the raw
location strings from the DB.
"""
from __future__ import annotations

from typing import Iterable

from app.parsing.normalize import GLOBAL_LOC_MARKERS

# Locations equal to a bare country name are accepted as-is by list_countries().
KNOWN_COUNTRIES = {
    "ukraine", "україна", "canada", "usa", "united states", "germany",
    "deutschland", "poland", "польща", "united kingdom", "uk", "france",
    "spain", "italy", "czechia", "netherlands", "greece", "serbia",
    "norway", "mexico", "brazil", "hungary", "philippines", "australia",
    "ireland", "switzerland", "türkiye", "turkey", "portugal", "romania",
    "румунія", "кіпр", "cyprus", "bulgaria", "austria", "sweden",
    "denmark", "estonia", "latvia", "lithuania", "belgium", "finland",
    "croatia", "slovakia", "slovenia", "japan", "india", "israel",
    "argentina", "europe", "європа",
}

# Segments that look like locations but aren't countries.
NON_COUNTRIES = {
    "apac", "emea", "latam", "europe", "north america", "usa timezones",
    "michigan", "washington", "kansas", "california", "new york", "texas",
    "florida", "illinois", "georgia", "colorado", "massachusetts",
    "pennsylvania", "virginia", "oregon", "arizona", "minnesota",
    "wisconsin", "ohio", "maryland", "new jersey", "connecticut",
    "богунський", "шевченківський", "оболонський", "дарницький",
    "голосіївський", "печерський", "подільський", "святошинський",
    "солом'янський", "деснянський", "дніпровський",
}


def extract_countries(locations: Iterable[str]) -> list[str]:
    """Distinct countries from raw location strings: last comma-segment
    when present, or the whole string if it's a known country name.
    Junk (cities, distances, multi-country blurbs) is dropped."""
    out: set[str] = set()
    for raw in locations:
        loc = raw.strip()
        if "," in loc:
            c = loc.rsplit(",", 1)[-1].strip()
            # reject things that don't look like a country name
            if any(ch.isdigit() for ch in c) or any(s in c for s in "+();"):
                continue
            if c.lower() in NON_COUNTRIES:
                continue
            out.add(c)
        elif loc.lower() in KNOWN_COUNTRIES:
            out.add(loc)
    return sorted(
        c for c in out if c and c.lower() not in GLOBAL_LOC_MARKERS
    )
