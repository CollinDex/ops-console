# Phase 5: Frontend shell: login, auth, navigation, status layer

| | |
|---|---|
| **Branch** | `phase/5-frontend-shell` |
| **Depends on** | Phase 2 merged (auth API). Phases 3–4 should be merged so the type generation covers every endpoint |
| **Read first** | design §1.5 (brief coverage: login, status indicator, responsive nav), §4.2 (frontend layout and state strategy), §6.5 (error envelope), §7.2 (401/403 handling), §7.5 (status layer), ADR-003, ADR-007 |
| **Estimated effort** | 3 h |

## Goal
A working, polished shell: staff sign in, see navigation for their role, move around on desktop and phone, and always know whether the app and its providers are healthy. Feature pages are placeholders in this phase. Overview fetches one real number so the status layer can be tested end to end.

## Visual direction
- This is an internal ops tool, so it should be calm, dense and legible. Use shadcn/ui on the **slate** base with a **CrediSure navy primary**: light `--primary: oklch(0.36 0.09 260)` (≈ #1f3a68), dark `oklch(0.72 0.1 260)`. Set both in `globals.css`, light and dark.
- Fonts via `next/font/google`: **IBM Plex Sans** for UI (400/500/600) and **IBM Plex Mono** for identifiers and numbers (CAC, masked BVN, latency). Use `font-variant-numeric: tabular-nums` on numeric cells.
- Status colours are semantic and separate from the brand: up/passed = emerald, slow/pending = amber, down/failed = red. **Never colour alone:** always pair it with an icon and text.

## 1. API layer (`src/lib/`)
- **`api-types.ts`:** generate it with `pnpm gen:api` against the running API (from Phase 4) and commit it. Add a header comment saying it is generated and must not be edited by hand.
- **`api-client.ts`**
  ```ts
  export class ApiError extends Error { status: number; code: string; requestId?: string; details?: unknown }
  export async function api<T>(path: string, init?: { method?: string; body?: unknown; headers?: Record<string,string>; signal?: AbortSignal }): Promise<T>
  ```
  - Base URL: `process.env.NEXT_PUBLIC_API_URL`. Paths starting with `/health` go to the root, and everything else gets the `/api/v1` prefix.
  - Adds `Authorization: Bearer <token>` from the token store, plus `Content-Type: application/json` when there is a body.
  - Parses non-2xx responses into `ApiError` from the envelope. If the body isn't an envelope, use `code: "http_error"`.
  - A network failure or CORS error becomes `ApiError(status 0, code "network_error", "Can't reach the CrediSure API. Check your connection and try again.")`.
  - **401 on any path except `/auth/login`:** call the registered `onUnauthorized(code)` handler. The AuthProvider registers it to clear the session and redirect to `/login?reason=expired` (for `token_expired`) or `/login?reason=signin`.
  - Also export `apiBlob(path)` for the CSV download in Phase 6.
- **`query-client.ts`:** `makeQueryClient()` with these defaults:
  - queries: `staleTime: 30_000`, `refetchOnWindowFocus: true`, `retry: (n, err) => !(err instanceof ApiError && err.status >= 400 && err.status < 500) && n < 1`
  - `QueryCache.onError(error, query)`: skip if `query.meta?.silent`, or if status is 401 or 403 (handled elsewhere). Otherwise `toast.error(error.message, { id: JSON.stringify(query.queryKey), description: requestId ? \`Ref ${requestId.slice(0,8)}\` : undefined, action: { label: "Retry", onClick: () => query.fetch() } })`. Using the query key as the toast id means a failing poll doesn't stack duplicate toasts.
  - `MutationCache.onError`: toast with the message unless `mutation.meta?.silent` is set (Phase 6 retry handles its own messages).
  - Type `meta` through module augmentation: `{ silent?: boolean; background?: boolean }`.
- **`format.ts`:** `formatDate`, `formatDateTime` (`Intl.DateTimeFormat("en-NG", { timeZone: "Africa/Lagos" })`), `formatRelative` ("3 min ago", "2 days ago"), `formatNumber`, and `initials(name)`.

## 2. Auth (`src/features/auth/`)
- **Token store** (`token-store.ts`): `get()`, `set(token, expiresAt)` and `clear()`, backed by `localStorage` keys `credisure.token` and `credisure.token_exp`, with every access in try/catch.
- **`AuthProvider`** (client):
  - state: `{ status: "loading" | "authenticated" | "anonymous", user: Me | null }`
  - on mount: if there is a token and it isn't expired, run `GET /auth/me`; otherwise go to `anonymous`.
  - `login(email, password)` → POST `/auth/login`, store the token, set the user, and schedule `logout("expired")` with `setTimeout` at `expires_at`.
  - `logout(reason?)` → clear the token, `queryClient.clear()`, and `router.replace("/login" + (reason ? \`?reason=${reason}\` : ""))`.
  - registers `onUnauthorized` with the api-client.
  - `useAuth()` hook, and `hasRole(...roles)`.
- **Providers tree** (`src/app/providers.tsx`): `ThemeProvider` (next-themes, `attribute="class"`, `defaultTheme="system"`), `QueryClientProvider` (create the client once with `useState`), `AuthProvider`, `TooltipProvider`, and `<Toaster richColors closeButton position="top-right" />`.

## 3. Routes
```
src/app/layout.tsx                 fonts, <Providers>, metadata title "CrediSure Ops Console"
src/app/page.tsx                   client redirect → /overview
src/app/(auth)/login/page.tsx      the login screen
src/app/(console)/layout.tsx       "use client": auth guard + <AppShell>
src/app/(console)/overview/page.tsx      placeholder plus one live number (see §6)
src/app/(console)/businesses/page.tsx    <RoleGate roles={["analyst","ops_admin"]}> placeholder
src/app/(console)/providers/page.tsx     placeholder
src/app/(console)/team/page.tsx          <RoleGate roles={["analyst","ops_admin"]}> placeholder
src/app/not-found.tsx              friendly 404 with a link to Overview
```
- **Guard:** while `status === "loading"`, show a full-height shell skeleton. When `anonymous`, `router.replace("/login?next=" + encodeURIComponent(pathname))`. Never flash protected content.
- **Next.js 15 gotcha:** any component using `useSearchParams()` must sit inside `<Suspense>`, or `next build` fails. That includes the login page, which reads `next` and `reason`.

## 4. Login screen (brief item 1)
- **Layout:** two columns at `lg` and above, one column below.
  - **Left panel** (navy, hidden below `lg`): "CrediSure Ops Console", the line "See which businesses are stuck in onboarding, why, and whether it's us or a provider.", and three small facts with icons (4 verification checks tracked, provider health every 15 s, role-based access).
  - **Right:** the form card.
- **Form** (react-hook-form + zod):
  - email: required, valid email ("Enter a valid work email")
  - password: required ("Enter your password"), with a show/hide toggle button (`aria-pressed`)
  - inline field errors via `aria-describedby`
  - the submit button shows a spinner and disables while pending. The first invalid field gets focus.
- **Server errors:** a `role="alert"` banner above the form. A 401 shows "Email or password is incorrect.", a network error shows the network message, and a 422 maps onto the fields.
- **`?reason=expired`:** an info banner, "Your session expired. Sign in again." **`?reason=signin`:** "Sign in to continue."
- **Demo accounts:** a "Demo accounts" section with three buttons (Ops admin, Credit analyst, Viewer). Each fills in the email and password. It doesn't auto-submit, so the reviewer sees the form work. Each shows what that role can do in one line.
- **Footer note:** "Prototype for CrediSure's engineering assessment. All data is fictional."
- After a successful login, go to `next` (only when it's a relative `/` path, which prevents open redirects) or `/overview`. If the user is already authenticated when they visit `/login`, redirect them the same way.

## 5. App shell (`src/components/layout/`, brief item 6)
- **`nav-config.ts`:**
  | Label | Href | Icon (lucide) | Roles |
  |---|---|---|---|
  | Overview | `/overview` | `LayoutDashboard` | all |
  | Businesses | `/businesses` | `Building2` | analyst, ops_admin |
  | Providers | `/providers` | `Activity` | all |
  | Team | `/team` | `Users` | analyst, ops_admin |
- **`AppShell`:** at `lg` (≥1024 px), a fixed 240 px `AppSidebar` plus a content column. Below `lg` there's no sidebar, and the header shows a hamburger.
- **`AppSidebar`:** the CrediSure wordmark, nav links filtered by role, the active link highlighted (`pathname.startsWith(href)`) with `aria-current="page"`, and an environment tag at the bottom ("Demo data").
- **`MobileNav`:** a shadcn `Sheet` (side left) with the same links. It closes automatically on route change (`useEffect` on `pathname`). Radix gives focus trap, `Esc` to close, and focus returning to the hamburger. The hamburger has `aria-label="Open navigation"` and `aria-expanded`.
- **`Header`** (sticky): hamburger (below lg), page title (from nav config), then on the right: `HealthDot`, theme toggle (`aria-label="Toggle theme"`), and `UserMenu`.
- **`UserMenu`:** an avatar with initials, then a dropdown with full name, email, a role badge ("Ops admin", "Credit analyst", "Viewer"), and Sign out.
- **Skip link:** "Skip to content" as the first focusable element, targeting `<main id="content">`.
- **`RoleGate`:** `({ roles, children, feature })`. When the role isn't allowed, it renders `<Forbidden feature=… />`: an icon, "Your role (Viewer) can't view Businesses.", and "Ask an ops admin if you need access." with a link back to Overview. Phase 6 reuses `Forbidden` for API 403s.

## 6. Status layer (brief item 5, app level)
- **`TopProgressBar`:** fixed at the top, 2 px, brand colour, `z-50`. Visible when `useIsFetching({ predicate: q => !q.meta?.background }) + useIsMutating() > 0`, after a **150 ms delay** to avoid flicker. Indeterminate sliding animation. With `prefers-reduced-motion`, it shows a static full-width bar instead. Mark it `role="progressbar"` with `aria-label="Loading"` and `aria-hidden` when idle.
- **`HealthDot`:** `useQuery(["health"], () => api("/health"), { refetchInterval: 30_000, meta: { silent: true, background: true } })`.
  | State | Condition | Colour | Label |
  |---|---|---|---|
  | ok | `status: ok` | emerald | "All systems normal" |
  | degraded | `status: degraded` | amber | "n provider(s) degraded" |
  | down | query error or `db: down` | red | "API unreachable" |
  | checking | first load | slate (pulse) | "Checking…" |
  The label text is visible at `sm` and wider, and `sr-only` below. A tooltip shows "Last checked 12 s ago" and the request time. Clicking it goes to `/providers`.
- **Overview placeholder:** a card that fetches `/stats/overview` and shows "Total businesses: 300" plus "Full overview arrives in Phase 6." This exercises the normal (non-silent) error toast path.

## 7. Quality
- ESLint (next/core-web-vitals + typescript) is clean. `tsc --noEmit` is clean. No `any` without a comment explaining why.
- Every interactive element is reachable by keyboard and has visible focus (`focus-visible:ring`).
- Lighthouse accessibility on `/login` scores 95 or higher (if Lighthouse is available, put the score in the report).

## Acceptance criteria
1. Each demo account can sign in. Wrong credentials show the inline banner. Validation errors appear before any request is sent.
2. A viewer sees only Overview and Providers in the nav. Visiting `/businesses` directly shows the Forbidden state.
3. Analysts and ops admins see all four nav items, and the active item is highlighted.
4. Signing out clears the session, and the back button doesn't show protected pages.
5. Session expiry: with `JWT_TTL_MINUTES=1` on the API, the user gets sent to `/login?reason=expired` with the banner.
6. At 375 px wide, the hamburger opens the slide-in nav, which closes after navigating and on `Esc`. At 1024 px and wider, the sidebar is always visible.
7. Stopping the API container turns the health dot red within 30 s, and makes the Overview number fail with a toast that has Retry. Restarting the API and clicking Retry recovers.
8. Setting a provider to down (via curl, Phase 4) turns the dot amber.
9. The progress bar shows during the Overview fetch but **not** during the 30 s health polls.
10. Dark mode toggles and persists, and both themes are legible.
11. `make lint` and `make web-check` pass.

## Verify
```bash
make lint && make web-check
docker compose up --build -d
# Manual pass in the browser (record results in the report): http://localhost:3000
#  - each role signs in; nav per role; /businesses as viewer → Forbidden
#  - DevTools device toolbar at 375×812 → hamburger nav
#  - docker compose stop api → red dot + toast with Retry; docker compose start api → Retry recovers
#  - curl simulate bvn down → amber dot; set back to up
```

## Out of scope
Real Overview widgets, the Businesses table, the drawer, the Providers page, and the Team table (Phases 6–7).

## Review checklist (Opus)
- [ ] There's no protected-content flash before the auth check finishes.
- [ ] The `next` redirect only allows relative paths (no open redirect).
- [ ] 401 → logout happens in exactly one place (the api-client hook), not scattered across pages.
- [ ] Background polls are excluded from the progress bar and don't toast.
- [ ] Toasts are deduped by query key, and Retry refetches that query.
- [ ] Status is shown by colour, icon and text together, never colour alone.
- [ ] The mobile Sheet closes on navigation and has correct aria attributes. The skip link works.
- [ ] Every `useSearchParams` sits under `Suspense`, and `next build` passes.
- [ ] The generated `api-types.ts` is committed and used, with no hand-written duplicate response types.
