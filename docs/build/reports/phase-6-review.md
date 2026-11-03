# Phase 6 review

- **Branch:** `phase/6-screens`
- **Reviewer:** Opus
- **Date:** 2026-11-03
- **Verdict:** Ready to merge

## Verify (re-run by the reviewer)
```text
$ make lint && make test && make web-check && make web-test   → exit 0
  ruff/mypy/eslint/prettier "All checks passed!"
  pytest: 119 passed
  vitest: Test Files 1 passed, Tests 15 passed
$ docker compose up --build -d && curl localhost:8000/health   → {"status":"ok","db":"ok",...}
$ git log --format=%B main..HEAD | grep -ci 'co-authored\|claude' → 0
```

I also ran a browser check against the compose stack:
- Overview renders every block.
- The deep link `/businesses?stage=checks_in_progress&failed=bvn` restores 35 rows with the filter chips.
- The drawer shows the failure reason and a masked account (`******8451`).
- A double-click on Re-run raised the BVN attempts from 3 to 4 (one attempt) and showed one toast.
- At 375 px, Team shows the hamburger nav, and the table scrolls inside its wrapper.

## Findings
| # | Severity | Area | Finding | Fix |
|---|---|---|---|---|
| 1 | minor | `app/providers.tsx` | The top-right toasts covered the drawer's close button while visible (the implementer flagged this). The cause was the Phase 5 spec's `position="top-right"` | Moved to bottom-right in `9ef9f99 fix(web): move toasts to bottom-right so they clear the drawer close button` |
| 2 | minor | API CORS | `Content-Disposition` was not exposed, so the CSV filename was unreadable | Fixed by the implementer in `cf29b43`, with a test. Accepted |
| 3 | nit | `lib/score.ts` | The score bands are duplicated client-side because viewers can't read `/meta/filters` | Left as-is. The bands are static display copy, and the filter bar still uses the API ranges |
| 4 | nit | `useRetryCheck` | Because the button disables on the first click, the server's 409 path can't be reached from the UI | Left as-is. This is defence in depth, and the 409 path is covered by the API concurrency test |

## Acceptance criteria check
All 11 pass. Implementer evidence is in `phase-6-implementation.md`. The reviewer re-checked #2, #4, #5, #6 and #10 in the browser.

## Checklist
- [x] The URL is the only filter state (ADR-007). `router.replace`, page reset on filter change, and Vitest cover parse, serialize and merge.
- [x] Idempotency key: one per click intent, reused on double-click and by the toast Retry, and cleared on settle.
- [x] Masked identifiers only. No full BVN or account number reaches the client.
- [x] Role gating: analyst Re-run disabled with a tooltip, viewer gets Forbidden on businesses and team, and the API still enforces it.
- [x] Status always shows colour, icon and text.

## Notes for the next phase
- Toasts are bottom-right now. The Providers page simulate toast lands there too.
- For the Phase 7 fresh-clone run, stop the dev stack first (`docker compose down`): ports 5433, 8000 and 3000 are shared.
