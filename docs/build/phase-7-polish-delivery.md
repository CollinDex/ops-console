# Phase 7: Providers page, polish & delivery

| | |
|---|---|
| **Branch** | `phase/7-polish-delivery` |
| **Depends on** | Phase 6 merged |
| **Read first** | design §1.5, §7.4 (pinger and simulate), §7.5 (status layer), §11 (deployment), §12 (trade-offs and future work); PRD §9 demo script |
| **Estimated effort** | 3 h, plus deploy time with the owner |

## Goal
This phase finishes the provider-level half of the status indicator, gives the whole app an accessibility and responsiveness pass, writes the README a reviewer reads first, and prepares the live deployment. When it's done, the full 8-step PRD demo runs cleanly from `docker compose up --build`.

## 1. Provider Health page (`/providers`, brief item 5, provider level; all roles)
- **Data:** `["providers","status"]` with a 15 s refetch (background), plus `["providers", name, "incidents"]` per provider when that provider's history is opened.
- **Header:** the title "Provider health", the subtitle "Live status of the verification APIs onboarding depends on", "Updated 4 s ago" (ticks every second), and a **Refresh** button (icon spins while fetching, `aria-label="Refresh provider status"`).
- **Summary strip:** "3 up · 0 slow · 1 down". When anything is down, show a red banner: "BVN (NIBSS) is down. BVN checks will fail until it recovers. This is a provider problem, not an applicant problem." That banner answers the PRD goal "tell a provider outage from an applicant problem".
- **Provider cards** (2×2 grid at `md` and wider, stacked below):
  - label + `StatusBadge` (Up, Slow, Down or Unknown, with icon and text)
  - current latency in mono ("143 ms", or "—" when down), last checked (relative), 24 h uptime %, 24 h average latency
  - **sparkline** of the `recent` latencies: inline SVG, about 160×36, area fill at low opacity, last point emphasised, and down points drawn as red ticks on the baseline. The colour comes from CSS variables. It has `role="img"` with an aria-label ("Latency over the last 10 minutes, currently 143 ms").
  - which checks depend on it ("Used by: BVN check")
  - **Demo controls (ops_admin only):** a segmented control (Up / Slow / Down) labelled "Simulate (demo only)". It calls `POST /providers/{name}/simulate`, toasts "BVN set to Down", and invalidates `["providers"]` and `["health"]`. Other roles don't see the control.
  - a "View incidents" toggle that expands the incident list
- **Incident history (Could):** per provider, a list of incidents with started (absolute plus relative), duration ("25 min"), worst status badge, and an "Ongoing" badge when `ended_at` is null. Empty state: "No incidents in the last 7 days."
- Loading skeleton cards and an error state with Retry.

## 2. Polish pass (the whole app)
Fix anything this pass finds. Report each fix in the implementation report.
- **Responsive:** check 375, 768, 1024 and 1280 px widths on every page and the drawer. No horizontal page scroll (only tables scroll inside their wrapper). Touch targets at least 40 px on mobile.
- **Accessibility:**
  - keyboard-only run of login → filters → open the drawer → re-run → close the drawer → nav → sign out
  - visible focus throughout, correct `aria-*` on custom controls
  - every icon-only button has an `aria-label`
  - colour contrast AA in both themes (use the browser contrast checker or axe DevTools if available)
  - `prefers-reduced-motion` respected (progress bar, skeleton shimmer, spinners)
- **Dark mode:** each page checked, including charts, badges, the sparkline, toasts and the login brand panel.
- **Copy:** consistent sentence case, the same terms everywhere ("Re-run check", "Credit analyst", "Bank link"), no lorem ipsum, and useful error messages.
- **Metadata:** a per-page `<title>` ("Businesses · CrediSure Ops Console"), a favicon (a simple navy "C" mark as SVG), and `loading.tsx` skeletons for route transitions.
- **Performance sanity check:** the Businesses page bundle has no server-only imports, and Recharts is loaded only on Overview (`next/dynamic` if needed).

## 3. README (repo root, the reviewer's first read)
Sections, in this order:
1. **CrediSure Ops Console:** one paragraph of why, using the PRD pitch line. A live demo link (filled in after deploy) and a screenshot (`docs/screenshots/overview.png`, taken in the final pass).
2. **What the assessment asked for → where to find it:** the six brief items as a table (copy design §1.5 in short form).
3. **Quick start:** prerequisites (Docker), `git clone … && cd ops-console && docker compose up --build`, then open http://localhost:3000. Note that the first run migrates and seeds automatically.
4. **Demo accounts:** the three accounts with their passwords and what each role can do.
5. **Five-minute demo script:** the PRD §9 steps, adapted to the real UI labels.
6. **Architecture:** a short summary, the Mermaid container diagram (copy design §3.2), and links to `docs/system-design.md` and `docs/adr/`.
7. **API:** the endpoint table (design §6.1), with a note that interactive docs are at http://localhost:8000/docs.
8. **Development:** the `make` targets, running the API and web outside Docker, running tests, and regenerating API types.
9. **Decisions & trade-offs:** 6–8 bullets taken from the ADRs and design §12, including the "different keys are different intents" note from Phase 4.
10. **What I'd build next:** from design §12.
11. **Data & privacy:** all data is fictional and seeded, scores are illustrative, and BVN and account numbers are stored as last-4 digits only.
12. **AI-assisted workflow:** how the project was planned and reviewed (design → phase docs → implementation → review reports in `docs/build/`).

## 4. Deployment preparation (the owner clicks deploy)
- **`render.yaml`** (Render Blueprint):
  - a `credisure-db` Postgres (free plan)
  - a `credisure-api` web service: Docker from `./api`, `healthCheckPath: /health`, env vars `DATABASE_URL` (fromDatabase), `JWT_SECRET` (generateValue), `CORS_ORIGINS` (set manually to the Vercel URL), and `ENV=prod`
- **Database URL:** Render gives `postgres://` or `postgresql://` URLs. `config.py` must normalise them to `postgresql+psycopg://`. Add a unit test for that.
- **Vercel:** document the steps in `docs/deploy.md`: import the repo, set root directory to `web`, the framework is detected, and set `NEXT_PUBLIC_API_URL=https://credisure-api.onrender.com`. Building with `output: "standalone"` is fine on Vercel.
- **CORS:** `CORS_ORIGINS` accepts a comma-separated list. Check that the preview and production Vercel URLs can both be added.
- **Cold starts:** the README says the free API sleeps after 15 minutes and the first request can take about 50 s. The health dot shows "Checking…" and then recovers.
- **`docs/deploy.md`** also covers the smoke-test checklist for the live URL (login, overview, filter URL, retry, simulate, mobile).

## 5. Final end-to-end pass
On a **fresh clone** (`git clone` into a temporary folder, then `docker compose up --build`), run the PRD demo script step by step:
1. Explain the one-line why (README).
2. Sign in as viewer: only Overview and Providers are visible, and no personal data. Then sign in as ops admin.
3. Overview: walk the funnel, then click a needs-attention business.
4. Businesses: search, then filter to "Checks in progress" + "BVN failed". Copy the URL, open it in a new tab, and confirm the same view.
5. Drawer: show the failure reason, re-run the check, double-click to show only one audit entry is added.
6. Providers: set BVN to Down. The panel shows Down with the banner, and the header dot turns amber. Retry a BVN check: "Provider unavailable".
7. Resize to phone width: hamburger nav.
8. Close with the trade-offs (README).

Record pass or fail per step in the report, with screenshots saved in `docs/screenshots/`.

## Acceptance criteria
1. The Providers page meets §1, the simulate control is ops_admin only, and incidents show the seeded history.
2. The polish checklist in §2 is done, with fixes listed.
3. The README covers all 12 sections, and its quick start works on a fresh clone.
4. `render.yaml`, `docs/deploy.md` and the DB URL normalisation (with its test) exist.
5. The full 8-step demo passes on a fresh clone.
6. `make lint`, `make test`, `make web-check` and `make web-test` all pass, and CI is green once a remote exists.

## Verify
```bash
make lint && make test && make web-check && make web-test
rm -rf /tmp/credisure-fresh && git clone . /tmp/credisure-fresh && cd /tmp/credisure-fresh && docker compose up --build -d
# run the 8-step demo at http://localhost:3000, then:
docker compose down -v && cd - && rm -rf /tmp/credisure-fresh
```

## Out of scope
Real provider adapters, alerting, refresh tokens, and rate limiting (README "next" section).

## Review checklist (Opus)
- [ ] The outage banner wording clearly separates a provider outage from an applicant problem (PRD goal).
- [ ] The simulate control is hidden for non-admins, and the API still enforces it (403).
- [ ] The sparkline and charts are readable in both themes and have text alternatives.
- [ ] The README quick start works exactly as written on a fresh clone. The demo accounts are correct.
- [ ] No secrets in `render.yaml` (use generateValue or manual values). The DB URL is normalised.
- [ ] The six brief items are each demonstrably present (design §1.5). This is the final gate before submission.
