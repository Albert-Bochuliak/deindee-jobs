---
name: backend-development
description: Backend development guidelines for this project. Enforces SOLID, DRY, KISS principles on Python code — scrapers, parsers, filters, API layer, storage. Use for any backend implementation, refactoring, or review task.
---

# Backend Development Skill

All backend code in this project (Python) MUST follow SOLID, DRY, KISS. These are hard requirements, not suggestions.

## KISS — Keep It Simple, Stupid

- Prefer the simplest solution that works. No speculative abstractions, no "just in case" flexibility.
- No configuration options, plugin systems, or base classes until there are at least 2 real consumers.
- Flat is better than nested: max 3 levels of indentation; use early returns and guard clauses.
- Functions do one thing and fit on one screen (~40 lines). If longer — split.
- No clever one-liners. Readable boring code beats smart code.

## DRY — Don't Repeat Yourself

- A piece of knowledge lives in exactly one place: constants, validation rules, URL patterns, parsing logic.
- If code is copied a second time — extract it into a function/module immediately.
- Shared normalization (dates, salary, text cleanup) lives in one module, imported everywhere.
- Don't over-abstract: duplication is cheaper than the wrong abstraction. Extract only when the duplication is real, not incidental.

## SOLID

### Single Responsibility
- One class/module = one reason to change.
- Scraper fetches HTML. Parser extracts fields. Filter scores scam. Repository stores. Nothing mixes.
- Each job platform gets its own scraper module; shared HTTP logic goes into a common client.

### Open/Closed
- Adding a new job platform MUST NOT require editing existing code — only adding a new `Source` implementation and registering it.
- New anti-scam rules plug into a rules registry, not into an `if/elif` chain.

### Liskov Substitution
- Every source implements the same interface (`fetch() -> Iterable[RawJob]`) and can be swapped without callers knowing.
- No source may raise source-specific exception types outward — wrap into a common `SourceError`.

### Interface Segregation
- Small interfaces: `fetch()`, `parse()`, `score()`, `save()` — not one fat `do_everything()`.
- A source that can't provide salary simply returns `None`; no fake placeholder values.

### Dependency Inversion
- Scraper service depends on `Source` protocol, not on concrete classes.
- Storage behind a `JobRepository` interface — SQLite today, Postgres later, zero call-site changes.
- Inject dependencies (http client, repository, config) via constructors. No imports of concrete implementations deep inside business logic. No globals, no singletons.

## Structure conventions

```
app/
  sources/        # one file per platform, each implements Source protocol
  parsing/        # shared parsing/normalization helpers
  filters/        # scam-detection rules, each rule = one small class/function
  storage/        # repository interface + implementations
  services/       # orchestration (ScraperService, FilterPipeline)
  api/            # HTTP API for the React frontend
```

## Code quality rules

- Type hints on all public functions. `dataclass`/`pydantic` for models — no dicts passing through layers.
- Errors: catch at boundaries, log with context (source name, URL), never `except: pass`.
- Logging via `logging` module, not `print`.
- Config via environment variables / a single `config.py`. No hardcoded URLs, tokens, or paths in logic.
- Every new module ships with at least a smoke test or a `__main__` demo path.

## Anti-patterns — reject on sight

- God-classes / `utils.py` dump files.
- Business logic inside API route handlers.
- Parsing HTML inside scrapers' fetch methods.
- Mutable default arguments, wildcard imports, bare `except`.
- Commented-out dead code committed "for later".
