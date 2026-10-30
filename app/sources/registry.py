"""Source registry — the ONLY place that knows which sources exist.

Adding a source = create file in app/sources/ + one line here. Nothing else changes.
"""
from __future__ import annotations

from app.config import Config
from app.models import Source
from app.sources.arbeitnow import ArbeitnowSource
from app.sources.craigslist import CraigslistSource
from app.sources.dice import DiceSource
from app.sources.djinni import DjinniSource
from app.sources.freelancehunt import FreelancehuntSource
from app.sources.himalayas import HimalayasSource
from app.sources.http_source import HttpFetcher
from app.sources.jobbank import JobBankSource
from app.sources.jobicy import JobicySource
from app.sources.kijiji import KijijiSource
from app.sources.linkedin import LinkedInSource
from app.sources.olx import OlxSource
from app.sources.playwright_source import PlaywrightFetcher
from app.sources.remoteok import RemoteOkSource
from app.sources.robota import RobotaUaSource
from app.sources.remotive import RemotiveSource
from app.sources.rss_source import build_rss_sources
from app.sources.workua import WorkUaSource


def build_sources(config: Config) -> list[Source]:
    """Instantiate all enabled sources, sharing one fetcher of each kind."""
    fetcher = HttpFetcher(config)        # plain-HTTP sources
    pw_fetcher = PlaywrightFetcher(config)  # JS-rendered / anti-bot sources
    sources: list[Source] = [
        RemoteOkSource(fetcher),
        RemotiveSource(fetcher),
        ArbeitnowSource(fetcher),
        DjinniSource(fetcher, config),
        FreelancehuntSource(fetcher),
        LinkedInSource(fetcher),
        JobicySource(fetcher),
        HimalayasSource(fetcher),
        WorkUaSource(pw_fetcher),
        OlxSource(pw_fetcher),
        RobotaUaSource(pw_fetcher),
        DiceSource(pw_fetcher),
        CraigslistSource(pw_fetcher),
        JobBankSource(fetcher),
        KijijiSource(fetcher),
        *build_rss_sources(fetcher, config.dou_feed_url, config.workua_feed_url),
    ]
    # API-key sources are optional — skipped silently when unconfigured
    if config.jooble_api_key:
        from app.sources.jooble import JoobleSource

        sources.append(JoobleSource(fetcher, config.jooble_api_key))
    if config.adzuna_app_id and config.adzuna_app_key:
        from app.sources.adzuna import AdzunaSource

        sources.append(AdzunaSource(fetcher, config))
    if config.usajobs_api_key and config.usajobs_email:
        from app.sources.usajobs import UsaJobsSource

        sources.append(
            UsaJobsSource(fetcher, config.usajobs_api_key, config.usajobs_email)
        )
    return sources
