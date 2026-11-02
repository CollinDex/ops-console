# ADR-007: The URL is the source of truth for table state

- **Status:** Accepted
- **Date:** 2026-11-02

## Context
PRD M4 requires a filtered view to survive a refresh and to be shareable. The detail drawer should also be linkable from the needs-attention list.

## Decision
`search`, `stage`, `sector`, `score_min`/`score_max`, `failed_check`, `sort`, `order`, `page` and `id` (open drawer) live in the URL search params. A `useBusinessFilters()` hook parses and validates them (zod) and updates them with `router.replace`. Search input is debounced by 300 ms before it writes to the URL. The TanStack Query key is derived from the parsed params.

## Alternatives considered
- **React state or a global store (Zustand):** lost on refresh and not shareable.
- **localStorage:** survives refresh but not sharing, and stale filters surprise users later.

## Consequences
- Deep links, the back button, and refresh all work, and the API query parameters mirror the URL one-to-one.
- Every filter change resets `page` to 1, and invalid params are silently dropped back to their defaults.
