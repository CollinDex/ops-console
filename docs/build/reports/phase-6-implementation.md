# Phase 6 implementation report

- **Branch:** `phase/6-screens`
- **Implementer:** Sonnet
- **Date:** 2026-11-03
- **Commits:** (`git log --oneline main..HEAD`, before this report's own commit)
```text
127b632 docs: add phase 6 screenshots
28f74e8 fix(web): return focus to the row that opened the drawer
a7bbb08 feat(web): add team table with url search, role filter and sort
784767a feat(web): add businesses table, filters, drawer with retry and csv export
5b0b899 feat(web): add overview screen with stat cards, funnel, attention list, chart and provider summary
4bab5fd feat(web): add data table, pagination, badges, states and filter inputs
28561d7 feat(web): add url filter state with vitest, make web-test and ci step
cf29b43 fix(api): expose content-disposition header to browsers via cors
```

## Summary
Built the Overview (4 stat cards, funnel, needs attention, sign-ups chart, provider summary, each with its own loading and error state), the Businesses screen (URL-driven filters, debounced search, sortable paginated table, detail drawer with masked data, audit timeline and idempotent retry, CSV export) and the Team table. Shared `DataTable`, `Pagination`, badges, states and filter inputs live in `web/src/components/data/`. One small API fix was needed (CORS did not expose `Content-Disposition`, so the browser could not read the CSV filename).

## Acceptance criteria
Browser checks used the built-in browser pane against the compose stack (production build) for the first passes, then `pnpm dev` after one fix (focus return). Fresh data via `make seed ARGS=--reset`. Real clicks and typing were used for the interactions; `javascript_tool` was used to read DOM state, count requests and to open rows or toggle popovers where coordinates were awkward.

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Overview shows 4 cards, funnel, needs-attention, chart, provider summary; blocks have loading and error states; viewers see no links into businesses | ✅ browser (error state not exercised) | Admin overview screenshots. Viewer: the only link inside `main` was `/providers`, nav had 2 items. Each block renders `Block` with skeleton and `ErrorState` + Retry, but I did not force a failure in the browser |
| 2 | "ade" filters after about 300 ms with one request; Stage=Checks in progress + Failed=BVN equals the SQL count; copying the URL restores the view; Clear all resets | ✅ browser | Fetch wrapper recorded one list request (`search=ade`) for typing "ade", 43 results. `/businesses?stage=checks_in_progress&failed=bvn` showed 35 businesses, SQL gave 35. Loading that URL cold (a fresh navigation) restored stage chip, failed chip and count. Clear all emptied the URL and input and returned 300 |
| 3 | Sort by score both directions, nulls last; pagination range text | ✅ browser + API | UI toggled descending to ascending (`aria-sort`), ascending starts 480, 480, 482. API page 15 of both orders ends in six `null` scores. Page 15 read "Showing 281–300 of 300", pager `1 … 11 12 13 14 15`, Next disabled |
| 4 | Needs-attention row opens `/businesses?id=…` with the drawer | ✅ browser | Clicked "Arewa Agro Nigeria Ltd", URL became `/businesses?id=56a0…`, drawer open |
| 5 | Drawer: masked BVN and account only, failure reasons, audit timeline | ✅ browser | `*******5002`, `******8923`, red "BVN name does not match director" callout, timeline entries "Adaeze Okafor (Ops admin) re-ran the BVN check: failed, Provider unavailable (bvn)" |
| 6 | Retry as ops_admin: one request, toast, badge, stage and audit update, overview count updates; double-click gives one audit entry | ✅ browser | Double-click on Re-run: fetch wrapper saw 1 POST with one Idempotency-Key, API log shows one POST, audit list has one `check.retry` row, badge went to Passed (attempts 3). Overview "Stuck" later read 122 (was 123). Note: the button is disabled by the first click so the second click never leaves the browser. The server-side 409 path was not exercised from the UI |
| 7 | With BVN down, retry shows "failed. Provider unavailable (bvn)" | ✅ browser | `curl simulate bvn down`, Re-run: toast "BVN check re-run: failed. Provider unavailable (bvn)", callout updated, header dot "1 provider degraded". Set back to up afterwards |
| 8 | Analyst: Re-run disabled with tooltip. Viewer: /businesses and /team Forbidden | ✅ browser | Analyst (avatar TB): button `disabled`, tooltip "Only ops admins can re-run checks" shown on focus of the wrapper. Viewer: both routes showed "Your role (Viewer) can't view …" |
| 9 | Team: search, role filter, sort, pagination, state in URL | ✅ browser (pagination not visible) | `?role=viewer` gave 3 rows, "Showing 1–3 of 3"; `?search=okafor&sort=created_at&order=desc` gave 2 rows with `aria-sort` descending on Joined. There are fewer than 20 staff, so more than one page cannot be shown. `Pagination` is the same component as Businesses |
| 10 | 375 px: filters wrap, table scrolls horizontally, drawer full width | ✅ browser | 375x812: page scrollWidth 375, table container 341 wide with 639 scroll width, sheet left 0 width 375. Screenshots saved |
| 11 | `make lint`, `make web-check`, `make web-test` pass | ✅ | Output below |

Not verified in a browser: overview ErrorState (no forced failure), clicking the Export CSV button and the "Exported N businesses" toast (a file download, so I did not trigger it). I did check with `fetch` from the page, using the stored token, that the browser can now read `Content-Disposition: attachment; filename="credisure-businesses-20261103.csv"` and that the filtered export has 35 rows. Dark and light modes were both seen; contrast was judged by eye.

## Verify output
```text
$ make lint && make web-check && make web-test
All checks passed!   (ruff check)
82 files already formatted
Success: no issues found in 56 source files   (mypy)
eslint: clean; prettier --check: All matched files use Prettier code style!
tsc --noEmit: clean
next build: ✓ Compiled successfully in 8.7s, ✓ Generating static pages (10/10)
Route (app)                                 Size  First Load JS
├ ○ /businesses                          11.2 kB         233 kB
├ ○ /overview                             120 kB         270 kB
├ ○ /team                                3.44 kB         201 kB
vitest run: Test Files 1 passed (1), Tests 15 passed (15)

$ make test
119 passed, 1 warning in 23.07s

$ docker compose up --build -d      → api and web containers started, /health returned status ok, /login returned 200
$ git log --format=%B main..HEAD | grep -ci 'co-authored\|claude'   → 0
```
The manual pass from the Verify section is the table above. The compose stack is down and no dev servers are running. Screenshots are in `docs/screenshots/phase-6/`.

## Files added or changed
- `api/`: `app/main.py` (CORS `expose_headers`), `tests/test_export.py` (asserts it)
- `web/src/lib/`: `url-state.ts`, `use-url-state.ts`, `use-debounced-value.ts`, `use-now.ts`, `score.ts`, `format.ts` (`formatShortDate`), `api-client.ts` (`apiDownload`)
- `web/src/components/data/`: data-table, pagination, status-badges (StatusBadge, CheckBadge, ProviderStatusBadge), stage-badge, score-pill, states (EmptyState, ErrorState), search-input, multi-select
- `web/src/features/businesses/`: filters (+ `filters.test.ts`), queries (incl. `useRetryCheck`), filter-bar, businesses-table, business-drawer, audit-timeline, businesses-page
- `web/src/features/overview/`: queries, block, stat-cards, funnel, needs-attention, signups-chart, provider-summary, overview-page (removed `overview-count.tsx`)
- `web/src/features/staff/`: filters, staff-page
- `web/vitest.config.mts`, `web/package.json` (vitest, `test` script), `Makefile` (`web-test`), `.github/workflows/ci.yml` (`pnpm test`)
- Page files for overview, businesses and team now render the feature components.

## Deviations / questions
- **API fix (blocking):** CORS `expose_headers` only had `X-Request-ID`, so the browser could not read `Content-Disposition` (or `X-Truncated`) cross-origin. Added both, with a test (`fix(api): expose content-disposition header to browsers via cors`).
- **Score bands for viewers:** `/meta/filters` is analyst and admin only, but the Overview average card (all roles) needs the band name, so `lib/score.ts` holds the five bands as a constant (same values as design §2.1). The filter bar still takes ranges from `/meta/filters`.
- **Retry keys:** the key ref is cleared on settle as the spec says. The error toast's Retry re-sends the captured key (the same one), not a fresh one. After any settle, the drawer queries, `businesses` and `stats` are invalidated, including after a 409, so a stale view refreshes.
- **`router.replace`** adds no history entries, so the browser Back button leaves the page instead of undoing filters (follows ADR-007). The search box re-sync is covered by Clear all and by URL changes from outside.
- Overview queries are `silent` (no toast) because each block shows its own ErrorState; the providers poll is also `background`.
- The Business and Team "page header" is an `h2`, because the app header already has the `h1` with the same text.
- Team default sort is name ascending (the API default), so the URL stays clean.
- The success/failed toast is top-right and covers the drawer's close button while visible (about 10 s for errors only; success and warning use the default). Not changed.
- Export CSV counts rows from the downloaded text (lines minus the header) for the toast.

## Known gaps / follow-ups
- ErrorState paths, the Export button toast and the server 409 (`request_in_progress`) toast were not exercised in a browser.
- Team has only one page of seeded staff, so multi-page behaviour was not visible there.
- Overview chart tooltip and axis colours use CSS variables; I saw dark mode on the chart and light mode on the tables, not every component in both themes.
- Mono font is used for CAC numbers, masked values and emails; no full identifiers are shown anywhere.
