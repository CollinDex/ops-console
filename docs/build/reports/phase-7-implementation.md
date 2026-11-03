# Phase 7 implementation report

- **Branch:** `phase/7-polish-delivery`
- **Implementer:** Sonnet
- **Date:** 2026-11-03
- **Commits:** (`git log --oneline main..HEAD`, before this report's own commit)

```text
62f2edc docs: add phase 7 demo screenshots
737c8b5 docs: write full readme
8da77b2 fix(web): label the drawer action Re-run check with the check name
28bad0a fix(web): focus the option list so keyboard users can pick filter options
e3b7925 fix(web): raise mobile touch targets to 40px and honour reduced motion
c8845bf fix(web): derive sparkline label span from ping timestamps
163ba92 chore: add render blueprint and deploy guide
5719f5f feat(api): normalise postgres URLs and accept comma-separated CORS origins
59bcaa1 feat(web): add per-page titles, favicon and route loading skeleton
a6da37e feat(web): add provider health page
```

## Summary
Built the Provider health page (`/providers`) with summary strip, outage banner, four cards with sparkline, simulate control (ops admin only) and incident history. Ran the polish pass (responsive, keyboard, reduced motion, titles, favicon, loading skeleton) and fixed what it found. Wrote the 12-section README, `render.yaml`, `docs/deploy.md`, URL normalisation plus comma-separated CORS parsing with unit tests, then ran the 8-step demo on a fresh clone.

## Acceptance criteria
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Providers page meets §1, simulate is ops_admin only, incidents show seeded history | ✅ | Admin: 4 cards, "3 up · 0 slow · 1 down", banner, simulate toast, incidents list showed seeded 25 min incident plus "Ongoing" badge. Viewer: 0 radiogroups, no "Simulate" text. API: viewer and analyst `POST /providers/bvn/simulate` both return 403. Screenshots `docs/screenshots/phase-7/06-*`, `02-viewer-providers.jpg` |
| 2 | Polish checklist done, fixes listed | ✅ (see "Polish fixes") | Custom audit script in the browser pane, keyboard run, 4 widths |
| 3 | README covers 12 sections, quick start works on a fresh clone | ✅ | `README.md`; `docker compose up --build -d` on a fresh clone gave a seeded, working stack. One transient build failure, see Deviations |
| 4 | `render.yaml`, `docs/deploy.md`, DB URL normalisation with a test | ✅ | `render.yaml`, `docs/deploy.md`, `api/app/core/config.py`, `api/tests/test_config.py` (5 tests) |
| 5 | Full 8-step demo passes on a fresh clone | ✅ | Table below |
| 6 | `make lint`, `make test`, `make web-check`, `make web-test` pass; CI green once a remote exists | ✅ locally, CI not applicable (no remote) | Verify output below |

### Demo run on the fresh clone (`/tmp/credisure-fresh`, built from the branch HEAD at 737c8b5)
| Step | Result | Notes |
|---|---|---|
| 1. One-line why (README) | ✅ | README opens with the pitch paragraph, live-demo placeholder and screenshot |
| 2. Viewer sees only Overview and Providers, no personal data; then ops admin | ✅ | Viewer nav: Overview, Providers. Only link inside `main` was `/providers`. No 7+ digit numbers on the page. No Simulate control on Providers. Signed out through the user menu (keyboard), signed in as admin. `02-*.jpg` |
| 3. Overview funnel, click a needs-attention business | ✅ | Funnel 30/36/114/45/75 of 300. Clicking "Bright Estates Global Services Ltd" opened `/businesses?id=…` with the drawer. `03-*.jpg` |
| 4. Search, then "Checks in progress" + "BVN failed", copy URL, open in a new tab | ✅ | Search "agro" gave 8 results. Filters gave 36 businesses, SQL count on the fresh DB is 36. A new tab with the same URL showed 36, the same two chips and the same first row. `04-*.jpg` |
| 5. Drawer: failure reason, re-run, double-click gives one audit entry | ✅ | "BVN name does not match director"; re-run took BVN to Passed (attempts 2 to 3), audit had exactly 1 `check.retry` entry. The UI button disappears after the first click (check is no longer failed), so the second click can't reach the server. To prove the server side, I sent two POSTs with the same `Idempotency-Key` with curl: first `replayed=False`, second `replayed=True`, still 1 audit entry. `05-*.jpg` |
| 6. Providers: BVN Down, banner, amber header dot, retry BVN shows "Provider unavailable" | ✅ | Banner "BVN (NIBSS) is down. BVN checks will fail until it recovers. This is a provider problem, not an applicant problem." Header dot "1 provider degraded" in amber. Re-run on Naija Stores Enterprises: toast "BVN check re-run: failed. Provider unavailable (bvn)" and the callout updated. BVN set back to Up afterwards. `06-*.jpg` |
| 7. Phone width: hamburger nav | ✅ | 375 px: no horizontal scroll, sidebar hidden, hamburger opens the slide-in menu, choosing Team navigated and closed it. `07-*.jpg` |
| 8. Close with trade-offs (README) | ✅ | README "Decisions and trade-offs" present in the fresh clone |

Teardown: `docker compose down -v` in the clone, `rm -rf /tmp/credisure-fresh`, and the dev stack was stopped earlier. No containers are running and ports 3000, 8000 and 5433 are free.

## Polish fixes
| # | Finding | Fix | Commit |
|---|---|---|---|
| 1 | Touch targets under 40 px on mobile (header icon buttons 32, filters 32, Export CSV 32, sort headers 28, pagination 28, search 32, "View providers" link 18) | `max-sm:` heights on Button (default, sm, icon, icon-sm, icon-xs), Input, Select trigger, health dot, table sort header, provider summary link. Re-measured at 375 px: Overview, Team, Providers and the drawer report none; Businesses reports only the business-name buttons inside table rows (20 px tall, but the whole row opens the drawer and rows are about 66 px tall) | `e3b7925` |
| 2 | Reduced motion only covered the progress bar; skeleton pulse, spinners and sheet/popover animations still ran | Global `@media (prefers-reduced-motion: reduce)` rule in `globals.css` | `e3b7925` |
| 3 | Keyboard: in multi-selects without a search box (Stage) focus landed on the popover container, so ArrowDown and Enter never reached cmdk and a keyboard user couldn't pick an option (a Phase 6 bug, found by the keyboard run) | `onOpenAutoFocus` focuses the cmdk list when there is no search box. Verified: Enter on Stage, ArrowDown x2, Enter selects "Checks in progress" and the URL updates; Escape returns focus to the trigger | `28bad0a` |
| 4 | Copy: the drawer action said "Re-run" while the phase doc and tooltips use "Re-run check"; the accessible name didn't say which check | Label "Re-run check", `aria-label="Re-run BVN check"` (and the "(not permitted)" variant) | `8da77b2` |
| 5 | Sparkline aria-label hard-coded the span; seeded history is 40 minutes, not 10 | Span derived from the first and last ping timestamps | `c8845bf` |
| 6 | No per-page titles or favicon; only the default `favicon.ico` | Title template `%s · CrediSure Ops Console`, route layouts for overview, businesses, providers, team and login, SVG navy "C" favicon (`app/icon.svg`, removed `favicon.ico`), `(console)/loading.tsx` skeleton | `59bcaa1` |

Checks that found nothing to fix:
- **Horizontal scroll:** none at 375, 768, 1024 or 1280 px on Overview, Businesses (with and without the drawer open), Providers, Team and Login (`scrollWidth` equals the viewport width, or the viewport minus the scrollbar).
- **Contrast (AA):** a custom in-page script computed the ratio for every visible text node (composited backgrounds, large-text threshold). Zero failures on Overview, Businesses with drawer, Providers (including the red Down banner), Team and Login, in light and dark. axe-core could not be used: loading it from a CDN into the page was blocked by the permission system, so I wrote the check myself. It does not cover SVG text or non-text contrast.
- **Accessible names:** zero icon-only buttons or links without a name on every page.
- **Keyboard-only run** (dev server, real key presses, with `document.activeElement` read back after each step): skip link, nav, theme toggle, account menu, Export CSV (not activated), search, Stage filter (after fix 3), row button then Enter opens the drawer with focus on Close, Shift+Tab to Re-run check then Enter re-ran the check, Escape closed the drawer, Providers link by Enter, account menu then ArrowDown, Enter on Sign out landed on `/login`. A visible focus ring was reported on every stop. After closing the drawer focus ended on `body`, because the re-run made the business drop out of the active "BVN failed" filter, so the row it came from no longer existed.
- **Dark mode:** Overview, drawer, Providers (cards, sparkline, banner, badges), Team and the login brand panel checked at 1024 and 1280 px. Sonner toasts were seen in light mode only in screenshots.
- **Bundle:** `/overview` is 116 kB (Recharts); `/businesses` 10.7 kB, `/providers` 5.3 kB, `/team` 6.7 kB. Recharts is only pulled in by Overview. No server-only imports.

## Verify output
```text
$ make lint && make test && make web-check && make web-test
cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy app
All checks passed!
83 files already formatted
Success: no issues found in 56 source files
cd web && pnpm lint && pnpm format:check
eslint: no output
Checking formatting...
All matched files use Prettier code style!
cd api && uv run pytest
TOTAL                               1405     20    99%
124 passed, 1 warning in 23.13s
cd web && pnpm typecheck && pnpm build
tsc --noEmit: no output
 ✓ Compiled successfully in 5.7s
 ✓ Generating static pages (10/10)
Route (app)                                 Size  First Load JS
├ ○ /businesses                          10.7 kB         235 kB
├ ○ /icon.svg                                0 B            0 B
├ ○ /login                               20.5 kB         164 kB
├ ○ /overview                             116 kB         271 kB
├ ○ /providers                           5.31 kB         167 kB
└ ○ /team                                 6.7 kB         201 kB
cd web && pnpm test
 Test Files  1 passed (1)
      Tests  15 passed (15)
exit code: 0

$ docker compose down
(dev stack stopped; ports freed)

$ rm -rf /tmp/credisure-fresh && git clone . /tmp/credisure-fresh && cd /tmp/credisure-fresh && docker compose up --build -d
first attempt: web image build failed in `pnpm build`:
  src/app/layout.tsx  An error occurred in `next/font`.  TypeError: Cannot read properties of null (reading '1')
second attempt, no changes: all three containers started.
api log: alembic "Running upgrade  -> 649689db837a, initial schema", seed ran, "Uvicorn running on http://0.0.0.0:8000"
$ curl localhost:8000/health -> {"status":"ok","db":"ok","providers":{"up":4,"slow":0,"down":0},...}
$ curl -o /dev/null -w "%{http_code}" localhost:3000/login -> 200

(8-step demo, see table above)

$ docker compose down -v && cd - && rm -rf /tmp/credisure-fresh
(volume and network removed; no containers running)

$ git log --format=%B main..HEAD | grep -ci 'co-authored\|claude\|generated'
0
```

The `make test` run includes `api/tests/test_config.py` (URL normalisation for `postgres://`, `postgresql://` and already-correct URLs, and comma-separated or JSON `CORS_ORIGINS`). `pnpm gen:api` was not re-run: no API schema changed in this phase.

## Files added or changed
- **Web, providers feature:** `web/src/features/providers/{providers-page,provider-card,sparkline,incidents}.tsx`, `queries.ts`; `web/src/app/(console)/providers/page.tsx`.
- **Web, polish:** `components/ui/{button,input,select}.tsx`, `components/data/{data-table,multi-select}.tsx`, `components/layout/health-dot.tsx`, `features/businesses/{business-drawer,filter-bar}.tsx`, `features/overview/provider-summary.tsx`, `app/globals.css`, `app/layout.tsx` (title template), route `layout.tsx` files for titles, `app/icon.svg`, `app/(console)/loading.tsx`; `app/favicon.ico` removed.
- **API:** `api/app/core/config.py` (URL normalisation, comma-separated CORS), `api/tests/test_config.py`, `api/.env.example` (comment).
- **Delivery:** `render.yaml`, `docs/deploy.md`, `README.md`.
- **Docs and evidence:** `docs/screenshots/overview.png`, `docs/screenshots/phase-7/*.jpg` (13 images), this report.
- Unexpected: shadcn buttons are shared everywhere, so raising their mobile height touches every page. I checked Businesses, Team, Overview, Providers and the drawer at 375 px after the change and the layout holds (filters wrap to two rows).

## Deviations / questions
1. **The PRD is not in the repo**, so I could not read PRD §9 or the PRD pitch line. The README pitch is based on design §1.1 and the login panel copy, and the demo script follows the 8 steps in this phase doc.
2. **Fresh-clone build is network-dependent and failed once.** `next/font/google` downloads IBM Plex at build time. The first `docker compose up --build` died with a `next/font` TypeError, and a second run with no changes passed. A reviewer on a flaky or offline network could hit the same. Suggest a follow-up to self-host the fonts (`next/font/local`) or use `geist`-style bundled fonts. Not changed here (out of scope).
3. **`CORS_ORIGINS` format.** The phase doc says it "accepts a comma-separated list", but `list[str]` in pydantic-settings only parsed JSON, so Render's dashboard value `https://a,https://b` would have crashed the API at startup. I made `Settings` accept both a JSON list and a comma-separated string (`NoDecode` plus a validator) and tested both. The committed `.env.docker` still uses JSON and still works.
4. **`PORT=8000` in `render.yaml`.** Render defaults to port 10000 for Docker services; the image listens on 8000 (`scripts/start.sh`), so I set `PORT=8000`. Not in the phase doc. I could not test a Render deploy.
5. **Simulate toast wording.** The toast uses the provider label ("BVN (NIBSS) set to Down"); the phase doc example says "BVN set to Down".
6. **Outage banner for other providers.** The doc gives the BVN wording only. For any provider that is down the banner reads "<label> is down. <check name>s will fail until it recovers. This is a provider problem, not an applicant problem.", for example "Tax ID checks will fail". One banner paragraph per down provider.
7. **`/businesses?failed=bvn` versus the API.** The UI URL param is `failed`, the API param is `failed_check`. Not a defect; I tripped over it while scripting the idempotency check. Worth a line in the README API section if a reviewer scripts it.
8. **Demo-script step 5 as written** ("double-click to show only one audit entry") can't show the server-side protection through the UI, because the first click flips the check to passed and removes the button. The UI is safe, and I demonstrated the server path with a repeated `Idempotency-Key` via curl. The README step says "double-click if you like".
9. **Phase 6 bug found and fixed here:** multi-select popovers couldn't be operated with the keyboard (polish fix 3). It should have been caught by the Phase 6 review's keyboard check; flagging in case the reviewer wants to adjust their checklist.

## Known gaps / follow-ups
- **No live demo link.** README says "Live demo: _to be added after deploy_". `docs/deploy.md` and `render.yaml` are untested against real Render and Vercel. `credisure-api.onrender.com` in `docs/deploy.md` is the assumed service URL; Render may add a suffix.
- **Business-name buttons in table rows** are under 40 px tall on mobile (the whole row is the touch target). Left as is.
- **Contrast** was measured with my own script, not axe. Non-text contrast (focus rings, chart bars, sparkline stroke) was judged by eye only.
- **Toasts in dark mode** weren't screenshotted; the audit script excludes toast text because toasts were not on screen when it ran.
- **Overview ErrorState** and the Providers error state were not forced in the browser (same as Phase 6). The Providers page uses the shared `ErrorState` with Retry.
- **Seeded history in the dev DB** now contains test pings and a few incidents from this session (BVN down/slow runs), so incident lists there show extra rows. The fresh clone had only the seeded 25 min incident until I created new ones in step 6. `make seed ARGS=--reset` rebuilds the dev DB.
- **CI** can't be confirmed green until a remote exists.
- The dev API, dev web server and all containers were stopped when I finished.
