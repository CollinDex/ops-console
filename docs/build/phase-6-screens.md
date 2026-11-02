# Phase 6: Screens: Overview, Businesses (table, filters, drawer), Team

| | |
|---|---|
| **Branch** | `phase/6-screens` |
| **Depends on** | Phases 3, 4 and 5 merged |
| **Read first** | design §1.5 (brief coverage: overview, user table, search and filter), §2.1 (definitions), §6.2–6.4 (list, detail and retry contracts), §7.3 (retry from the client's side), ADR-007 |
| **Estimated effort** | 4–5 h (the largest phase) |

## Goal
The screens the reviewer will spend the most time on: a dashboard overview that tells the onboarding story at a glance, a businesses table with server-side search and filters kept in the URL, a detail drawer with masked data, safe retry and an audit timeline, and a Team table of staff users.

## 1. Shared building blocks (`src/components/data/`)
- **`DataTable<T>`:** a thin generic over the shadcn `Table`, used by both Businesses and Team.
  - Props: `columns: { id; header; cell(row); sortKey?; className?; hideBelow?: "md" | "lg" }[]`, `rows`, `getRowId`, `sort`, `order`, `onSortChange`, `onRowClick?`, `loading`, `skeletonRows = 20`.
  - Sortable headers are `<button>`s with an arrow icon and `aria-sort` on the `<th>`.
  - Clickable rows: the whole row responds to click, and the **first cell holds a real `<button>` or link** for keyboard users. Row hover and focus styles.
  - Loading shows skeleton rows that match the column widths. `rows` stay visible while refetching (TanStack `placeholderData: keepPreviousData`), and the table dims slightly to show it's working.
  - The table sits in an `overflow-x-auto` wrapper. Columns marked `hideBelow` are hidden on small screens.
- **`Pagination`:** "Showing 21–40 of 137", Previous and Next buttons, and page numbers with ellipsis (max 7 shown). Buttons are disabled at the ends. The page change scrolls the table top into view.
- **`StatusBadge` / `CheckBadge`:** icon + text, and colour by semantics (passed = emerald `CheckCircle2`, failed = red `XCircle`, pending = amber `Clock`). `CheckBadge` is compact: a type label ("CAC", "TIN", "BVN", "Bank") with an icon, and a tooltip showing the status in full.
- **`StageBadge`:** a neutral badge with the stage label from `/meta/filters`.
- **`ScorePill`:** the number in mono font with the band colour and band name in its tooltip. "—" when null.
- **`EmptyState`, `ErrorState`** (message, request ref, Retry button), and **`Forbidden`** (from Phase 5). Every data block uses all three.
- **`useDebouncedValue(value, 300)`.**

## 2. URL filter state (`src/features/businesses/filters.ts`, ADR-007)
- A zod schema `businessFiltersSchema` for `search`, `stage[]`, `sector[]`, `band` (score band key), `failed` (`any|cac|tin|bvn|bank_link`), `sort`, `order`, `page` and `id`. Invalid values **fall back to defaults silently** (`.catch()`).
- `parseFilters(searchParams) -> Filters` and `serializeFilters(filters) -> URLSearchParams` drop defaults so URLs stay short. Repeated keys handle arrays (`stage=a&stage=b`).
- `toApiParams(filters, bands)` maps `band` to `score_min`/`score_max` and `failed` to `failed_check`.
- `useBusinessFilters()` returns `{ filters, setFilters(patch, { resetPage = true }), clearAll() }` and uses `router.replace(\`?${qs}\`, { scroll: false })`. Any change other than `page` or `id` resets `page` to 1.
- **Unit tests (Vitest):** add `vitest` and a `pnpm test` script, add `make web-test`, and add the step to the CI web job. Test the round-trip of parse and serialize, invalid values falling back, defaults omitted, band mapping, and page reset.

## 3. Overview (`/overview`, brief item 2; all roles)
Data comes from `GET /stats/overview` (query key `["stats","overview"]`, refetch every 60 s, background) and `GET /providers/status` (`["providers","status"]`, every 15 s, background).

The layout is a responsive grid. At `lg`, it's a 4-column card row, then funnel (2/3 width) plus provider summary (1/3), then needs attention (2/3) plus sign-ups (1/3). Below `lg`, everything stacks.
- **Stat cards (4):** Total businesses, Fully verified (plus "% of total"), Stuck in onboarding (with a small line, "failed check or more than 7 days in onboarding"), and Average credit score (plus its band name). Large tabular numbers, an icon, and a one-line definition in muted text. For analyst and ops_admin, "Stuck" links to `/businesses?failed=any`. Viewers see no links.
- **Onboarding funnel:** five horizontal bars in funnel order, each with label, count and % of total, and bar width proportional to the largest stage. For analyst and ops_admin, each bar links to `/businesses?stage=<stage>`.
- **Needs attention:** up to 10 rows, each with the business name, a stage badge, reason chips ("BVN failed" in red, "Bank data 12 days old" in amber), and a relative `since`. For analyst and ops_admin, a row links to `/businesses?id=<id>` (opening the drawer). For viewers, rows aren't interactive. Empty state: "Nothing needs attention right now."
- **Sign-ups chart (Could):** a Recharts `BarChart` of weekly sign-ups over 12 weeks. Axis, grid and tooltip colours come from CSS variables so it works in both themes. Ticks are short dates ("17 Aug"). Add an `aria-label` summary such as "Sign-ups per week, last 12 weeks, peak 31 in week of 19 Oct".
- **Provider summary:** four compact rows (label, status badge, latency), "Updated 5 s ago", and a "View providers" link.
- Each block has its own skeleton and its own error state with Retry, so one failing block doesn't blank the page.

## 4. Businesses (`/businesses`, brief items 3 and 4; analyst and ops_admin)
- **Page header:** the title "Businesses", the subtitle "Every SME on the marketplace, from sign-up to loan-ready", and on the right an **Export CSV** button. The button calls `apiBlob("/businesses/export.csv?" + toApiParams(...))`, then downloads through an object URL named from the response's `Content-Disposition`, with a toast saying "Exported N businesses". While working it shows a spinner.
- **`FilterBar`** (wraps on small screens):
  - **Search** input with a search icon and a clear (×) button. The placeholder is "Search name, CAC number or director". Local state is debounced by 300 ms before writing to the URL, and it **re-syncs** when the URL changes from outside (back button, Clear all). `aria-label="Search businesses"`.
  - **Stage** multi-select: a Popover with checkboxes, and the trigger shows "Stage · 2".
  - **Sector** multi-select: the same pattern, with a search box inside (shadcn `Command`).
  - **Score band** single select: "Any score" plus 5 bands with ranges.
  - **Failed check** single select: "Any status", "Has a failed check", "CAC failed", "Tax ID failed", "BVN failed", "Bank link failed".
  - **Result line:** "137 businesses", plus **Clear all** whenever any filter is active. Active filters also show as removable chips under the bar.
  - Options come from `GET /meta/filters` (`staleTime: Infinity`).
- **Table columns:**
  | Column | Content | Sort | Hide below |
  |---|---|---|---|
  | Business | name (button) + `state` in muted text; CAC in mono | `name` | |
  | Sector | label | | md |
  | Stage | `StageBadge` | | |
  | Checks | 4 `CheckBadge`s in fixed order CAC, TIN, BVN, Bank | | |
  | Score | `ScorePill` | `credit_score` | |
  | Last bank sync | relative time, plus an amber "Stale" badge if `bank_data_stale`; "—" if none | `last_bank_sync_at` | md |
  | Joined | `formatDate` | `created_at` | lg |
- **States:**
  - loading → 20 skeleton rows
  - empty → `EmptyState` saying "No businesses match these filters", with a Clear all button
  - error → `ErrorState` with Retry
  - API 403 → `Forbidden`
- The query key is `["businesses", apiParams]` with `placeholderData: keepPreviousData`.

## 5. Business drawer (brief item: detail; PRD M7, S1, S2)
Opens when the URL has `?id=`. It's a shadcn `Sheet` on the right, `sm:max-w-lg`, full width on mobile. Closing it removes `id` and keeps the other filters. Focus returns to the row that opened it.
- **Data:** `GET /businesses/{id}` (`["business", id]`) and `GET /businesses/{id}/audit` (`["audit", id]`).
- **Header:** the name, a `StageBadge`, then CAC number, sector and state in a muted line.
- **Sections** (as definition lists):
  1. **Verification checks:** one row per check with the `CheckBadge`, the status text, "Updated 3 h ago" (absolute time in a tooltip), and "Attempts: 2". A failed check shows the `failure_reason` in a red-tinted callout. **Re-run** button rules:
     - visible only when the check is `failed`
     - ops_admin: enabled
     - analyst: disabled, with the tooltip "Only ops admins can re-run checks"
     - viewers never reach the drawer
  2. **Credit profile:** the `ScorePill` with band, and consent ("Given 12 Oct 2026" or "Not given" in amber).
  3. **Bank data:** bank name, masked account in mono, and last sync with a Stale warning when it applies.
  4. **Identity:** director name, and masked BVN in mono with a small "Masked: last 4 digits only" note.
  5. **Activity (audit timeline):** a vertical list of icon, sentence and relative time.
     - `check.retry`: "**Adaeze Okafor** (Ops admin) re-ran the BVN check: failed, Provider unavailable (bvn)"
     - `businesses.export` isn't per business, so it won't appear here
     - empty: "No staff activity yet."
- **Retry mutation** (`useRetryCheck(businessId)`, `meta: { silent: true }`):
  - `keyRef = useRef<Record<CheckType, string | null>>({})`. On click: `keyRef.current[type] ??= crypto.randomUUID()`, then `mutate({ type, key })`. On settled, set it back to `null`. Disable the button while `isPending` for that check type.
  - `onSuccess`: toast "BVN check re-run: passed" (success) or "BVN check re-run: failed. <reason>" (warning). If `replayed`, use "Already processed, showing the original result." Then invalidate `["business", id]`, `["audit", id]`, `["businesses"]` and `["stats"]`.
  - `onError`: `request_in_progress` → info toast "This retry is already running." `check_not_retryable` → "This check is no longer failed." and a refetch. `forbidden` → the role message. Anything else → error toast with Retry, which re-calls with the **same** key.
- **Drawer states:** loading → skeleton sections. 404 → "Business not found" with a Close button. Error → ErrorState.

## 6. Team (`/team`, brief item 3, literal reading; analyst and ops_admin)
- The title is "Team" with the subtitle "Staff who can sign in to the Ops Console".
- Toolbar: a debounced search ("Search name or email") and a role multi-select. URL state works the same way as businesses (`search`, `role[]`, `sort`, `order`, `page`), with a small `useTableUrlState` generalised from the businesses hook, or a parallel hook.
- Columns: Name (avatar initials + full name), Email (mono), Role (badge), Joined. Sortable by name, role and joined. Uses `DataTable` and `Pagination`, with 20 per page.
- Loading, empty and error states, and Forbidden for a viewer (via RoleGate and the API 403).

## 7. Acceptance criteria
1. **Overview** shows all four cards, the funnel, needs-attention, the sign-ups chart and the provider summary with seeded data. Each block has its own loading and error state. Viewers see it with no links into businesses.
2. **Businesses:** typing "ade" filters after about 300 ms with a single request, and the network panel shows debouncing. Combining Stage = Checks in progress + Failed check = BVN gives the same total as the Phase 3 SQL check. **Copying the URL into a new tab restores exactly the same view**, and Clear all resets everything.
3. Sorting by score works in both directions, with nulls last. Pagination shows the correct range text.
4. Clicking a needs-attention row on Overview opens `/businesses?id=…` with the drawer open.
5. **Drawer:** masked BVN and account only, failure reasons visible, and the audit timeline is populated.
6. **Retry as ops_admin** on a failed BVN check: one request, a toast with the result, the badge, stage and audit timeline all update, and the "Needs attention" count updates on Overview. A quick double-click produces **one** audit entry (check the audit list and the API logs).
7. With BVN simulated down, a retry shows "failed. Provider unavailable (bvn)".
8. **Analyst:** the Re-run button is disabled with a tooltip. Viewer: `/businesses` and `/team` show Forbidden.
9. **Team** table: search, role filter, sort and pagination work, and the state lives in the URL.
10. **Mobile (375 px):** the filters wrap, the table scrolls horizontally with secondary columns hidden, and the drawer is full width and usable.
11. `make lint`, `make web-check` and `make web-test` pass.

## Verify
```bash
make lint && make web-check && make web-test
docker compose up --build -d
# Manual browser pass (record each acceptance criterion with a short note or screenshot path):
#  admin@credisure.demo → Overview → click a needs-attention row → drawer → Re-run (double-click) → audit entry ×1
#  /businesses?stage=checks_in_progress&failed=bvn → copy URL → new tab → same view
#  curl simulate bvn down → Re-run → "Provider unavailable (bvn)"
#  analyst@ → Re-run disabled; viewer@ → /businesses Forbidden
#  375×812 viewport pass
```

## Out of scope
The full Providers page and incident history (Phase 7). The README (Phase 7).

## Review checklist (Opus)
- [ ] The URL is the single source of truth: no duplicated filter state in React state (except the debounced search input).
- [ ] Back and forward work, and the search box re-syncs from the URL.
- [ ] The idempotency key is stable across a double-click and reset after it settles. The button is disabled while pending.
- [ ] Every query invalidated after a retry is listed and correct (`business`, `audit`, `businesses`, `stats`).
- [ ] Analysts never see an enabled Re-run, and viewers can't reach the drawer.
- [ ] No full identifiers anywhere in the UI. The mono font is used for masked values.
- [ ] Each data block has loading, empty and error states. One failure doesn't blank the page.
- [ ] Chart colours come from theme variables, and the chart has a text alternative.
- [ ] The CSV download sends the auth header (not a bare `<a href>`) and uses the filename from the server.
