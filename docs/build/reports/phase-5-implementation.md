# Phase 5 implementation report

- **Branch:** `phase/5-frontend-shell`
- **Implementer:** Sonnet
- **Date:** 2026-11-03
- **Commits:** (`git log --oneline main..HEAD`, before this report's own commit)
```text
6a7f380 docs: add phase 5 screenshots
bc5aced fix(web): keep token on network errors and keep error toasts for 10 s
e538e95 fix(web): put font variables on html and use fixed navy login panel
2473db4 feat(web): add app shell, role gating and status layer
9283c5e feat(web): add auth provider and login screen
49778b5 feat(web): add api client, query client and formatters
b4125b8 chore(web): generate API types
```

## Summary
Built the frontend shell: generated `api-types.ts` from the running API, the API client and TanStack Query defaults (error envelope, 401 hook, deduped toasts with Retry), the AuthProvider and token store, the login screen, the role-aware app shell (sidebar, mobile sheet, header, user menu, theme toggle, skip link, RoleGate/Forbidden), and the status layer (TopProgressBar, HealthDot). The navy primary and IBM Plex fonts are set in light and dark. Feature pages are placeholders; Overview fetches `/stats/overview` for one live number.

## Acceptance criteria
All browser checks were done by me in the built-in browser pane against a production build (`next start`) with the API run locally (`uvicorn`), then #7 again against the real compose stack. Browser-pane clicks were real; some state reads and timing used `javascript_tool`.

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Each demo account can sign in. Wrong credentials show the inline banner. Validation errors appear before any request | ✅ browser | Viewer, analyst and admin demo buttons filled the form and signed in. Wrong password showed the role="alert" banner "Email or password is incorrect.". Empty submit showed both field errors, focused email, and the network log had no `/auth/login` request |
| 2 | Viewer sees only Overview and Providers. `/businesses` shows Forbidden | ✅ browser | Viewer nav had 2 items. Direct load of `/businesses` showed "Your role (Viewer) can't view Businesses." (`docs/screenshots/phase-5/forbidden-viewer.png`) |
| 3 | Analysts and admins see four nav items, active highlighted | ✅ browser | Analyst saw 4 items, `/team` item had `aria-current="page"` and the highlight. Admin signed in too (4 items by the same code path) |
| 4 | Sign out clears the session, back button shows no protected page | ✅ browser | After Sign out: `localStorage` token null, URL `/login`. History back landed on `/login?next=%2Foverview`, no sidebar rendered |
| 5 | Session expiry with `JWT_TTL_MINUTES=1` goes to `/login?reason=expired` with banner | ✅ browser | API restarted with TTL 1, signed in as admin, after ~60 s the page was at `/login?reason=expired` with "Your session expired. Sign in again." and the token cleared. Also checked the 401 path: a garbage token goes to `/login?reason=signin` with "Sign in to continue." |
| 6 | At 375 px hamburger opens slide-in nav, closes after navigating and on Esc. At 1024+ the sidebar is always visible | ✅ browser | 375x812 emulation: hamburger opened the sheet (`aria-expanded` true, focus inside dialog). Esc closed it and focus returned to the hamburger. Clicking Team navigated and the sheet closed (after the 200 ms exit animation). No horizontal overflow. Sidebar visible at 1024 and 1280 |
| 7 | Stopping the API turns the dot red within 30 s and the Overview number fails with a toast with Retry. Restart and Retry recovers | ✅ browser | `docker compose stop api`: dot "API unreachable" after 14 s. First pass with local uvicorn: 22 s. Toast "Can't reach the CrediSure API..." with Retry appeared. API restart: dot back to "All systems normal" within 23 s. Retry click recovery was verified by forcing one failed `/stats` fetch in the page (the toast had timed out while the API restarted), then clicking Retry: card went from "Unavailable" to 300 |
| 8 | Provider down turns the dot amber | ✅ browser | `curl simulate bvn down` (admin token): dot showed the warning triangle and "1 provider degraded" within 4 s of the next poll. Set back to up, `/health` returned ok |
| 9 | Progress bar shows during the Overview fetch but not during the 30 s health polls | ✅ browser | `MutationObserver` on the progressbar. With `/health` delayed 1.5 s, a poll ran (start 30.08 s, end 31.6 s) and the bar never became visible. With `/stats` delayed 1.5 s, navigating to Overview made `data-visible` go true at ~460 ms (after the 150 ms delay) and false when it finished |
| 10 | Dark mode toggles and persists, both themes legible | ✅ browser | Toggle set `html.light` and `localStorage.theme=light`, which persisted after a full reload. Screenshots of both themes saved |
| 11 | `make lint` and `make web-check` pass | ✅ | Output below |

Not verified: Lighthouse accessibility score (Lighthouse isn't installed, and I didn't download it). Dark-mode legibility was judged by eye from screenshots, not measured for contrast. The admin account was signed in via the real UI, but I didn't look at an admin-specific screen (there isn't one in this phase). The Retry button recovery was verified with a forced client-side fetch failure as noted above, not purely with the container.

## Verify output
```text
$ make lint && make web-check
cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy app
All checks passed!
81 files already formatted
Success: no issues found in 55 source files
cd web && pnpm lint && pnpm format:check
> eslint
> prettier --check .
Checking formatting...
All matched files use Prettier code style!
cd web && pnpm typecheck && pnpm build
> tsc --noEmit
> next build
 ✓ Compiled successfully in 2.6s
 ✓ Generating static pages (10/10)
Route (app)                                 Size  First Load JS
┌ ○ /                                      355 B         103 kB
├ ○ /_not-found                            127 B         103 kB
├ ○ /businesses                          3.88 kB         124 kB
├ ○ /login                               44.3 kB         161 kB
├ ○ /overview                            2.21 kB         124 kB
├ ○ /providers                             127 B         103 kB
└ ○ /team                                3.88 kB         124 kB
+ First Load JS shared by all             103 kB
exit 0

$ docker compose up --build -d
 Image ops-console-api Built
 Image ops-console-web Built
 Container ops-console-api-1 Started
 Container ops-console-web-1 Started
$ curl localhost:8000/health
{"status":"ok","db":"ok","providers":{"up":4,"slow":0,"down":0},"version":"0.1.0","time":"2026-11-03T00:10:09.203227+00:00"}
$ curl -o /dev/null -w "%{http_code}" localhost:3000/login      → 200
$ curl -o /dev/null -w "%{http_code}" localhost:3000/overview   → 200

$ git log --format=%B main..HEAD | grep -ci 'co-authored\|claude'
0
```
The manual browser pass from the Verify section is the table above. The stack was brought down with `docker compose down` afterwards (the db volume is kept). No servers are left running.

Screenshots (`docs/screenshots/phase-5/`, taken with headless Chrome against the running app): `login-desktop-light`, `login-desktop-dark`, `login-mobile-light`, `overview-analyst-desktop-light`, `overview-analyst-desktop-dark`, `overview-mobile`, `mobile-nav-open`, `forbidden-viewer`.

## Files added or changed
- `web/src/lib/`: `api-types.ts` (generated), `api-client.ts`, `query-client.ts`, `format.ts`
- `web/src/features/auth/`: `token-store.ts`, `auth-provider.tsx`, `login-form.tsx`, `redirect.ts` (safe `next`), `types.ts`
- `web/src/features/overview/overview-count.tsx`
- `web/src/components/layout/`: app-shell, app-sidebar, mobile-nav, nav-links, nav-config, header, health-dot, top-progress-bar, user-menu, theme-toggle, role-gate, forbidden, brand
- `web/src/app/`: `layout.tsx`, `providers.tsx`, `page.tsx`, `not-found.tsx`, `globals.css`, `(auth)/login/page.tsx`, `(console)/layout.tsx` and four placeholder pages
- Removed the `.gitkeep` files in folders that now have content.
- `docs/screenshots/phase-5/*.png`

## Deviations / questions
- **`/health` is untyped in OpenAPI.** The route has no `response_model`, so `api-types.ts` types it as `unknown`. I declared a small `HealthResponse` type in `health-dot.tsx` with a comment. Suggest adding a Pydantic `response_model` to `/health` in a later API fix so the generated types cover it.
- **`globals.css` neutrals.** The shadcn init had pure-grey tokens even though `components.json` says slate. I moved the neutrals to a slate hue (about 255) and added `--success/--warning/--danger/--info` tokens for the status layer.
- **Login left panel uses a fixed navy** rather than `bg-primary`, because dark mode's primary is a light periwinkle and gave poor contrast with white text.
- **Toast duration is 10 s** (spec didn't say). The default 4 s made Retry hard to reach.
- **Session restore on network error:** if `/auth/me` fails with a non-401 error at load, the token is kept (not cleared) and the user lands on the login screen. A reload after the API recovers restores the session. The spec didn't cover this case.
- **Auth `redirecting` flag:** `logout()` navigates itself with `?reason=`. Without a flag the console guard also redirected and overwrote the reason, so the context exposes `redirecting` and the guard skips its redirect when it's set.
- **Sheet exit animation:** after a nav click the sheet closes on the route change but is visible for the ~200 ms exit animation.
- `api-types.ts` already starts with the generator's "auto-generated, do not edit" header, so I added nothing more.
- Used the production build (`next start`) for browser testing rather than `next dev`.

## Known gaps / follow-ups
- Lighthouse accessibility score for `/login` was not measured. Worth running before delivery.
- The demo-account buttons show no accessible name in the browser tool's accessibility tree dump, though they contain text. Likely a tooling quirk, but a reviewer may want to confirm with a screen reader or axe.
- After the error toast is dismissed, the Overview card shows "Unavailable" with no inline retry (spec only asks for the toast Retry).
- The progress bar only has a static-bar `prefers-reduced-motion` path via CSS, which I haven't visually checked.
