# Phase 1 review

- **Branch:** `phase/1-repo-setup`
- **Reviewer:** Opus
- **Date:** 2026-11-03
- **Verdict:** Ready to merge after the fixes below

## Verify (re-run by the reviewer)
```text
$ make lint            → ruff, ruff format, mypy strict, eslint, prettier: all clean
$ make test            → 1 passed (health), coverage 85%
$ make web-check       → tsc clean, next build OK (static placeholder)
$ docker compose up --build -d
$ curl localhost:8000/health → {"status":"ok","db":"ok","version":"0.1.0",...}
$ curl localhost:3000        → 200
$ uvx pre-commit run --all-files → all hooks pass
```

## Findings
| # | Severity | Area | Finding | Fix |
|---|---|---|---|---|
| 1 | minor | `.pre-commit-config.yaml` | The ruff hook was pinned to `v0.8.6` while the lockfile has a much newer ruff, so hook and CI could disagree on lint and format | Changed to local hooks that run `uv run ruff`, so the lockfile is the single version source |
| 2 | minor | `api/Dockerfile` | `ghcr.io/astral-sh/uv:latest` made image builds non-reproducible | Pinned to `0.9.22`, matching the local toolchain |
| 3 | minor | `web/package.json` | `next build --turbopack` is still beta for production builds in Next 15.5 | `build` now uses the stable webpack build. Dev keeps turbopack |
| 4 | nit | `web/src/components/ui/*` | Components import `cn` from the `cn` package rather than a local helper | Left as-is: `cn` is shadcn's own package (`shadcn-ui/cn`), and `src/lib/utils.ts` re-exports it |
| 5 | nit | `/health` | When the DB is down it returns `status: "degraded"` plus 503. The design reserves `degraded` for provider issues | Left for Phase 4, which redefines `status` when it adds provider counts. Noted in the next section |

## Acceptance criteria check
| # | Criterion | Result |
|---|---|---|
| 1 | docs commit on main, work on branch | ✅ |
| 2 | tree matches design, placeholder docstrings | ✅ |
| 3 | `make install` | ✅ (working tree) |
| 4 | lint and test | ✅ |
| 5 | web-check | ✅ |
| 6 | compose up, health ok, placeholder ok | ✅ |
| 7 | db down gives 503 | ✅ (implementer evidence) |
| 8 | no secrets, env examples | ✅ |
| 9 | CI YAML valid | ⚠️ parsed only; actionlint isn't installed. CI runs once a remote exists |

## Notes for the next phase
- In Phase 4, make `/health` return `status: "down"` (503) for a DB outage and `"degraded"` only for provider problems.
- `zod` resolved to **v4**. Its API differs from v3 in places (`z.email()`, and `error` instead of `message` in some options). Phase 5 and 6 implementers should use v4 syntax.
- `recharts` resolved to v3 and `lucide-react` to v1. Check their APIs against the installed versions, not memory.
