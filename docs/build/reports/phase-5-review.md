# Phase 5 review

- **Branch:** `phase/5-frontend-shell`
- **Reviewer:** Opus
- **Date:** 2026-11-03
- **Verdict:** Ready to merge

## Verify (re-run by the reviewer)
```text
$ make lint      → mypy "no issues found in 56 source files", ruff, eslint, prettier clean
$ make test      → 119 passed
$ make web-check → tsc clean, "Compiled successfully"
$ git log --format=%B main..HEAD | grep -ci 'co-authored\|claude' → 0
```
I also reviewed the screenshots in `docs/screenshots/phase-5/` (login light, overview dark). The layout, hierarchy and theming are clean.

## Findings
| # | Severity | Area | Finding | Fix |
|---|---|---|---|---|
| 1 | minor | `/health` contract | There was no `response_model`, so the generated types had `unknown` and the frontend hand-wrote `HealthResponse`, which breaks the "generated types only" rule | Added `HealthOut` with a documented 503 response, regenerated `api-types.ts`, and the frontend now uses the generated type (`fix(api): document health response schema in openapi`, `refactor(web): use generated health response type`) |
| 2 | nit | login demo buttons | The browser tool dump showed no accessible name | Checked the code: each button contains visible label text, so its accessible name is that text. Tooling quirk, no change |
| 3 | nit | overview placeholder | No inline retry once the toast is dismissed | Superseded by Phase 6, where every block has its own ErrorState with Retry |

## Checklist
- [x] No protected-content flash. The guard waits for `status`, and the `redirecting` flag keeps logout's `?reason=` intact.
- [x] `safeNext` allows only `/`-relative paths and rejects `//` and `/\`.
- [x] A 401 leads to logout in exactly one place (`api-client` → registered handler).
- [x] Background polls are excluded from the progress bar and are silent. Toasts are deduped by query key.
- [x] Status shows colour, icon and text together.
- [x] Mobile Sheet closes on navigation and on Esc, and focus returns to the trigger.
- [x] `useSearchParams` is under Suspense and `next build` passes.
- [x] Generated `api-types.ts` is used, with no hand-written duplicates (after fix 1).

## Accepted deviations
Slate-hued neutrals plus semantic `--success/--warning/--danger/--info` tokens (an improvement), the fixed navy login panel, 10 s error toasts, and keeping the token on network or 5xx errors at load.

## Notes for the next phase
- Use the semantic tokens (`text-success`, `text-warning`, `text-danger`) for check and status badges.
- Every data block needs its own ErrorState with Retry. Don't rely on toasts alone.
