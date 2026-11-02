# ADR-003: Stateless JWT bearer tokens stored client-side

- **Status:** Accepted
- **Date:** 2026-11-02

## Context
The web app (Vercel) and the API (Render) are on different origins. The PRD specifies that `POST /auth/login` returns a JWT and that the browser talks only to FastAPI.

## Decision
- HS256 JWT (`sub`, `role`, `exp` = 60 min, `jti`), sent as `Authorization: Bearer`.
- Stored in `localStorage` so a page reload keeps the session. No refresh token: after an hour the user signs in again.
- The role is loaded from the database on every request; the role claim in the token is informational only.
- Protected pages render client-side behind an auth guard.

## Alternatives considered
- **httpOnly cookie set by the API:** cross-site cookies need `SameSite=None; Secure` plus CSRF protection, and are increasingly blocked by browsers.
- **Backend-for-frontend (Next.js route handlers proxy to FastAPI, httpOnly same-site cookie):** the most secure option, but it breaks the PRD's "browser only talks to FastAPI" design and adds a proxy hop and more code.
- **Server-side sessions:** needs a session store; no benefit over a short-lived JWT here.

## Consequences
- Simple and stateless. Easy to test with curl and Swagger.
- Exposed to token theft if an XSS bug exists. Mitigated by React escaping, a CSP, the short TTL, and role re-checks against the database. The documented upgrade path is the BFF + httpOnly cookie option.
- Tokens cannot be revoked before expiry. Acceptable at 60 minutes, and deactivation still takes effect immediately because the user is reloaded on every request.
