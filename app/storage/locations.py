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


# US states + territories and CA provinces — a city-level location like
# "Quantico, Virginia" resolves to "united states" via its last segment.
US_REGIONS = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming", "district of columbia",
    "puerto rico", "guam",
}

CA_REGIONS = {
    "ontario", "quebec", "british columbia", "alberta", "manitoba",
    "saskatchewan", "nova scotia", "new brunswick",
    "newfoundland and labrador", "prince edward island",
    "northwest territories", "nunavut", "yukon",
}

# wanted-side aliases — "USA" should hit "united states"
COUNTRY_ALIASES = {
    "usa": "united states", "us": "united states", "u.s.": "united states",
    "u.s.a.": "united states", "america": "united states",
    "united states of america": "united states",
}


def region_country(loc: str) -> str | None:
    """Resolve a city-level location's last segment to its country (US/CA)."""
    region = loc.rsplit(",", 1)[-1].strip().lower()
    if region in US_REGIONS:
        return "united states"
    if region in CA_REGIONS:
        return "canada"
    return None


def country_regions(country: str) -> frozenset[str]:
    """Reverse of region_country — the regions a country filter must also
    match ('united states' -> all US states)."""
    key = COUNTRY_ALIASES.get(country.strip().lower(), country.strip().lower())
    if key == "united states":
        return frozenset(US_REGIONS)
    if key == "canada":
        return frozenset(CA_REGIONS)
    return frozenset()


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
