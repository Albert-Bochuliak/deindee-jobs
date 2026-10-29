---
name: frontend-development
description: Frontend development guidelines for this project. React + TypeScript + TailwindCSS conventions for the jobs dashboard UI. Use for any component, page, or styling task.
---

# Frontend Development Skill

React + TypeScript + TailwindCSS. Same core rules as backend: KISS, DRY, SOLID-adapted (single responsibility per component, props via typed interfaces, dependencies via props/context — not deep imports).

## Stack conventions

- React 18+ with function components and hooks only. No class components.
- TypeScript strict mode. No `any` — use `unknown` and narrow.
- TailwindCSS for all styling. No inline `style={{}}` except dynamic values (e.g. progress widths).
- Lucide React for icons. No emojis in UI.
- Data fetching: a single `api/` client module — components never call `fetch` directly.

## Component rules (KISS)

- One component = one job. Presentational components take props, render, done.
- If a component exceeds ~150 lines — split into subcomponents or extract logic to a hook.
- State lives at the lowest level that needs it. Lift up only when sharing is real.
- No prop drilling deeper than 2 levels — use context or composition instead.
- Prefer derived values over duplicated state. No `useEffect` for things computable during render.

## DRY

- Shared UI primitives (Badge, Card, ScoreIndicator) go in `components/ui/` — built once, reused everywhere.
- Reusable logic goes to custom hooks (`useJobs`, `useDebounce`) in `hooks/`.
- Types mirroring backend models live in `types/` — single source, imported everywhere.
- Repeated Tailwind class-strings become small components, not copy-paste.

## Structure

```
src/
  api/          # typed API client
  components/
    ui/         # primitives: Badge, Card, ScoreIndicator, Skeleton
    jobs/       # JobCard, JobList, JobFilters, ScamBadge
  hooks/        # useJobs, useFilters
  pages/        # route-level components
  types/        # Job, Filter types
```

## UX requirements for this project

- Scam score shown as a colored badge: green (safe), yellow (suspicious), red (likely scam).
- Source platform shown on every card.
- Filters: query, source, min scam-score threshold, remote only.
- Loading states — skeletons, not spinners. Empty states with a helpful message.
- Responsive: cards grid on desktop, list on mobile.

## Anti-patterns — reject on sight

- `fetch`/`axios` inside components.
- Business logic or scam-score math in components — comes from API.
- CSS files per component, `!important`, magic pixel values.
- `useEffect` chains for derived data.
- Untyped props (`props: any`), index-as-key in lists.
