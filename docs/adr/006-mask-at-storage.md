# ADR-006: Store only the last four digits of BVN and account numbers

- **Status:** Accepted
- **Date:** 2026-11-02

## Context
Staff need to recognise a director's BVN or a bank account during support, but nobody in operations needs the full number. The Nigeria Data Protection Act expects data minimisation.

## Decision
`businesses` stores `bvn_last4` and `account_last4` only. The API returns them masked (`*******1234`). Full identifiers are never accepted, stored or logged by this service.

## Alternatives considered
- **Store the full value and mask in the API serializer:** one forgotten serializer or debug log leaks it.
- **Encrypt the full value at rest:** needed only when something must use the full number. Here verification is the provider's job.

## Consequences
- Leaking the data through this service's database, backups or logs is impossible by construction.
- If a future feature needs the full number, it must come from a separate, access-controlled vault with its own ADR.
