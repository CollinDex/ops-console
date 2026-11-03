# Phase 7 review

- **Branch:** `phase/7-polish-delivery`
- **Reviewer:** Opus
- **Date:** 2026-11-03
- **Verdict:** Ready to merge

## Verify (re-run by the reviewer)
```text
$ make lint && make test && make web-check && make web-test   → exit 0
  pytest: 124 passed, coverage TOTAL 99%
  vitest: 15 passed
$ git clone . /tmp/credisure-fresh && docker compose up --build -d   → built first time (after fix #1)
  /health {"status":"ok","db":"ok","providers":{"up":4,"slow":0,"down":0}}, /login 200
$ git log --format=%B main..HEAD | grep -ci 'co-authored\|claude' → 0
```

Browser re-check on the fresh clone:
- Viewer nav shows only Overview and Providers.
- As admin, setting BVN to Down shows the Down card, the outage banner ("…a provider problem, not an applicant problem"), "1 provider degraded" in the header, a red tick on the sparkline, and the toast "BVN (NIBSS) set to Down".
- A BVN re-run in the drawer then returns "Provider unavailable (bvn)".
- The deep-link filter view still restores.

## Findings
| # | Severity | Area | Finding | Fix |
|---|---|---|---|---|
| 1 | major | `web/src/app/layout.tsx` | `next/font/google` fetches IBM Plex at build time. The implementer's first fresh-clone `docker compose up --build` failed on it, which risks the README quick start failing for a reviewer | Self-hosted the fonts with `@fontsource/ibm-plex-*`. The fresh clone then built first time (`9411f1b fix(web): self-host ibm plex fonts so builds never fetch google fonts`) |
| 2 | minor | `api/app/core/config.py` | `CORS_ORIGINS` accepted only JSON, but the spec says comma-separated | Fixed by the implementer in `5719f5f`, with tests. Accepted |
| 3 | nit | `render.yaml` | `PORT=8000` was added (Render defaults to 10000, while the image listens on 8000) | Accepted. It's correct for this Dockerfile. Untested until the owner deploys |
| 4 | nit | Simulate toast | "BVN (NIBSS) set to Down" instead of the spec's "BVN set to Down" | Accepted. The provider label is clearer |
| 5 | nit | Business-name button | 20 px tall on mobile | Accepted. The whole row is the touch target |

## Acceptance criteria check
| # | Criterion | Result |
|---|---|---|
| 1 | Providers page, simulate for ops_admin only, incidents | Pass (reviewer re-checked) |
| 2 | Polish checklist with fixes listed | Pass. 6 fixes in the implementation report |
| 3 | README 12 sections, quick start works on a fresh clone | Pass after fix #1 |
| 4 | `render.yaml`, `docs/deploy.md`, DB URL normalisation with a test | Pass |
| 5 | 8-step demo on a fresh clone | Pass. Implementer ran all 8 steps; reviewer re-ran 2, 4, 5 and 6 |
| 6 | lint, test, web-check, web-test | Pass. CI is pending a remote |

## Open items for the owner
- Deploy (Render Blueprint + Vercel, per `docs/deploy.md`), then put the live URL in the README.
- Push to a GitHub remote so CI runs.
