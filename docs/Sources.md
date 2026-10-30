# Sources

~19 boards. Enablement logic: `app/sources/registry.py::build_sources(config)`.

## Keyless (work out of the box)

- **Djinni, Freelancehunt, LinkedIn** — HTML via `HttpFetcher`
- **DOU** — RSS via `rss_source.py` + feedparser (`DOU_FEED_URL`;
  a Work.ua RSS feed also rides along via `WORKUA_FEED_URL`)
- **RemoteOK, Remotive, Arbeitnow, Jobicy, Himalayas, Job Bank (CA)** —
  public JSON APIs
- **Kijiji (CA)** — no API/RSS; parses `StandardListing` objects from
  `__NEXT_DATA__.__APOLLO_STATE__` on the SSR search page
  (`/b-jobs/canada/<kw>/k0c45l<locId>`)

## API-key sources (skip silently without keys)

| Source  | Env vars                          |
| ------- | --------------------------------- |
| Jooble  | `JOOBLE_API_KEY`                  |
| Adzuna  | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `ADZUNA_COUNTRY` (default `us`) |
| USAJOBS | `USAJOBS_API_KEY`, `USAJOBS_EMAIL` |

Keys configurable via `/api/settings` -> `settings` table (DB > .env).

## Playwright sources (`uses_browser = True`, single-worker pool)

- **Work.ua, OLX, Robota.ua, Dice, Craigslist** — JS-rendered or
  anti-bot protected. Base: `playwright_source.py` +
  `playwright-stealth`. `PLAYWRIGHT_HEADLESS` env (default true).
  Need `playwright install chromium`.
- **Dice** — Cloudflare wall; `/jobs?q=&location=&pageSize=`; markup via
  `data-testid` selectors (see `dice.py` module docstring).

## Quirks

- **Kijiji** — URL slug is decorative; the `l<id>` suffix is the real
  location filter. `LOCATION_IDS` in `kijiji.py` was verified against
  page titles (e.g. Vancouver = 80003, not 1700297).
- **USAJOBS** returns city-level locations (`"City, State"`) — see
  [[Pitfalls#Locations]].
- **Dice/USAJOBS-style `"City, State"` rows** are exactly why the
  country filter needs state suffixes — [[Pitfalls#Locations]].
- **Jobicy** — debug history in `_dbg_jobicy.py` (throwaway);
  `_tmp_dice_inspect.py` is the same for Dice.

## Adding a new source

Follow `.windsurf/workflows/add-source.md` and
`.windsurf/skills/scraping/` — source protocol, anti-bot, rate limits,
dedup, API-first strategy.
