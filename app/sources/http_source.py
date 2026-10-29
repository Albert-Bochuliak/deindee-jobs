"""Shared HTTP fetching: rate limit, timeouts, retries, UA. One class reused by all sources."""
from __future__ import annotations

import logging
import time

import httpx

from app.config import Config
from app.models import SourceError

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 2.0   # delay between retries: 2s, 4s, 8s


class HttpFetcher:
    """Rate-limited, retrying GET client. Injected into sources — no source builds its own."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._last_request_at: float = 0.0
        self._client = httpx.Client(
            headers={
                "User-Agent": config.user_agent,
                "Accept": "application/json, application/rss+xml, text/html;q=0.9",
            },
            timeout=httpx.Timeout(config.request_timeout, connect=10.0),
            follow_redirects=True,
        )

    def get(self, url: str, params: dict | None = None, source_name: str = "?") -> httpx.Response:
        """GET with rate limit + exponential-backoff retries.

        403/429 (anti-bot / rate limited) are retried; other 4xx/5xx raise
        immediately via raise_for_status. SourceError after MAX_RETRIES.
        """
        self._respect_rate_limit()
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.get(url, params=params)
                if response.status_code in (403, 429):
                    self._backoff(attempt, source_name, url, response.status_code)
                    last_error = SourceError(
                        f"[{source_name}] HTTP {response.status_code} for {url}"
                    )
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPError as exc:
                last_error = exc
                self._backoff(attempt, source_name, url, str(exc))
        raise SourceError(f"[{source_name}] failed after {MAX_RETRIES} tries: {last_error}")

    def post(self, url: str, json: dict, source_name: str = "?") -> httpx.Response:
        """POST without retries — used only by JSON APIs (Jooble)."""
        self._respect_rate_limit()
        try:
            response = self._client.post(url, json=json)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            raise SourceError(f"[{source_name}] POST {url} failed: {exc}") from exc

    def close(self) -> None:
        self._client.close()

    def _respect_rate_limit(self) -> None:
        """Sleep so requests are at least rate_limit_seconds apart."""
        elapsed = time.monotonic() - self._last_request_at
        wait = self._config.rate_limit_seconds - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    @staticmethod
    def _backoff(attempt: int, source: str, url: str, detail: object) -> None:
        """Log + sleep BACKOFF_BASE**attempt before the next retry."""
        delay = BACKOFF_BASE**attempt
        logger.warning("[%s] attempt %d failed for %s (%s); retry in %.1fs", source, attempt, url, detail, delay)
        time.sleep(delay)
