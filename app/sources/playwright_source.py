"""Browser-based fetcher for anti-bot/JS-rendered sources (Work.ua, Robota.ua, OLX...).

Same role as HttpFetcher — injected into sources — but renders pages in headless
Chromium with stealth patches. Lazily launches the browser on first get() so
plain-HTTP runs never pay the startup cost.
"""
from __future__ import annotations

import logging
import time

from app.config import Config
from app.models import SourceError

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 2.0
# body substrings meaning the page is a bot challenge, not real content
BLOCK_MARKER = (
    "just a moment",          # Cloudflare interstitial
    "challenge-platform",
    "captcha",
    "ваш браузер занадто старомодний",
)


class RenderedPage:
    """Minimal httpx.Response lookalike so HTML sources work with both fetchers."""

    def __init__(self, html: str, url: str, status_code: int = 200) -> None:
        self.text = html
        self.url = url
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise SourceError(f"HTTP {self.status_code} for {self.url}")


class PlaywrightFetcher:
    """Rate-limited headless-Chromium GET. Browser is shared across all sources."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._pw = None
        self._browser = None
        self._last_request_at: float = 0.0

    def get(
        self,
        url: str,
        source_name: str = "?",
        wait_selector: str | None = None,
        wait_ms: int = 3000,
    ) -> RenderedPage:
        """Render a page and return its final DOM HTML."""
        self._respect_rate_limit()
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            page = None
            try:
                page = self._new_page_ready(self._ensure_browser())
                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self._config.request_timeout * 1000,
                )
                if wait_selector:
                    page.wait_for_selector(wait_selector, timeout=15000)
                page.wait_for_timeout(wait_ms)  # let XHR/CF settle
                html = page.content()
                status = response.status if response else 0
                if status >= 400 or self._looks_blocked(html):
                    last_error = SourceError(
                        f"[{source_name}] blocked/HTTP {status} for {url}"
                    )
                    self._backoff(attempt, source_name, url, last_error)
                    continue
                return RenderedPage(html, url, status)
            except SourceError as exc:
                last_error = exc
            except Exception as exc:  # playwright errors — retry like httpx path
                last_error = exc
                self._backoff(attempt, source_name, url, exc)
            finally:
                if page is not None:
                    page.close()
        raise SourceError(
            f"[{source_name}] failed after {MAX_RETRIES} tries: {last_error}"
        )

    def close(self) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._browser = self._pw = None

    # -- internals ---------------------------------------------------------

    def _ensure_browser(self):
        """Launch headless Chromium on first use, wrapped in stealth patches."""
        if self._browser is None:
            # local import — playwright isn't needed unless a rendered source runs
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth

            self._pw = Stealth().use_sync(sync_playwright()).__enter__()
            self._browser = self._pw.chromium.launch(
                headless=self._config.playwright_headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            logger.info("playwright: chromium %s launched", self._browser.version)
        return self._browser

    def _new_page_ready(self, browser):
        """Fresh page with UA-ish headers matching a real UA browser."""
        page = browser.new_page()
        page.set_extra_http_headers(
            {"Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8"}
        )
        return page

    @staticmethod
    def _looks_blocked(html: str) -> bool:
        """Scan the first 8k chars for challenge-page markers."""
        body = html[:8000].lower()
        return any(m in body for m in BLOCK_MARKER)

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait = self._config.rate_limit_seconds - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    @staticmethod
    def _backoff(attempt: int, source: str, url: str, detail: object) -> None:
        delay = BACKOFF_BASE**attempt
        logger.warning(
            "[%s] attempt %d failed for %s (%s); retry in %.1fs",
            source, attempt, url, detail, delay,
        )
        time.sleep(delay)
