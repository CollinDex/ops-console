# Final review

- **Reviewer:** Opus
- **Date:** 2026-11-03
- **Scope:** `main` after phases 1–7, ahead of submission (due Thu 5 Nov 2026, 11:58 WAT)
- **Verdict:** Ready to submit. Deploying and adding a remote are owner actions

## Gates
| Gate | Result |
|---|---|
| `make lint` (ruff, mypy strict, ESLint, Prettier) | Pass |
| `make test` (pytest on Postgres) | 125 passed, 99% coverage |
| `make web-check` (tsc, production build) | Pass |
| `make web-test` (Vitest, URL filter state) | 15 passed |
| Fresh clone, `docker compose up --build` | Built first time. Migrates and seeds automatically, `/health` ok |
| Commit history | 72+ commits, all one-line Conventional Commits. 0 bodies, 0 attribution trailers |

## The six brief items (design §1.5)
| Brief item | Evidence |
|---|---|
| Login screen | `/login`: validation, wrong-credential error, demo-account buttons, redirect on expiry |
| Dashboard overview | `/overview`: stat cards, funnel, needs-attention, sign-ups chart, provider summary |
| User table | `/businesses` (sortable, paginated, drawer) and `/team` |
| Search and filter | Server-side debounced search, combinable filters, state kept in the URL (deep link restores the same 35 to 36 rows) |
| API request status indicator | App level: progress bar, toast with Retry, health dot. Provider level: `/providers` cards, sparkline, incidents, 15 s refresh |
| Responsive navigation | Sidebar at 1024 px and up, hamburger sheet below that. Checked at 375 px |

## Cross-cutting checks
- **PII:** only last-4 digits of BVN and account numbers are stored (ADR-006). No full-number pattern appears in `api/app` or the seed. The drawer shows `******8451`-style values.
- **Auth:** the role is re-read from the DB on every request. 401 and 403 use the error envelope. Viewer and analyst get 403 on simulate and retry (API tests), and the UI hides or disables those actions.
- **Idempotent retry:** a double-click gives one attempt and one audit entry (checked in the browser). Concurrency and replay are covered by API tests.
- **Outage vs applicant:** with BVN simulated down, the banner says it is a provider problem, the header shows "1 provider degraded", and the re-run reason reads "Provider unavailable (bvn)".
- **Secrets:** no `.env` or key files are tracked. `render.yaml` uses `generateValue` and manual values. **New in this review:** the API refuses to start with `ENV=prod` and the dev JWT secret (`8f94457`).

## Findings in this review
| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | major | With `ENV=prod` and `JWT_SECRET` unset, tokens would be signed with the public dev default | `fix(api): refuse to start in prod with the dev jwt secret` (`8f94457`), with a test |

Earlier phase findings, including the build-time Google Fonts fetch fixed in Phase 7, are in the per-phase review reports.

## Known limits (documented in the README)
- JWT in `localStorage` with no refresh tokens (ADR-003).
- One API instance, because of the in-process pinger and in-memory simulate mode (ADR-005).
- Offset pagination, no caching.
- Free-tier cold start of about 50 s.

## Owner actions before submission
1. Create the GitHub repo and push `main`. CI runs then.
2. Deploy using `docs/deploy.md`: Render Blueprint for the API and DB, Vercel for `web/`, then set `CORS_ORIGINS` to the Vercel URL.
3. Put the live URL in the README's "Live demo" line, and run the smoke checklist in `docs/deploy.md`.
