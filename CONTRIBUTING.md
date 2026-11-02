# Contributing

## Branches
- Build phases: `phase/N-<slug>` (for example `phase/1-repo-setup`), cut from `main`.
- Other work: `feat/<topic>` or `fix/<topic>`.

## Commits
One line in [Conventional Commits](https://www.conventionalcommits.org/) form, short and specific:
`feat(api): add business list filters`, `fix(web): keep filters on refresh`, `docs: ...`, `chore: ...`.
No body and no trailers.

## Workflow
Each phase is planned, implemented, reviewed and fast-forward merged into `main`. See [docs/build/README.md](docs/build/README.md).

## Checks
`make lint`, `make test` (needs `make db`) and `make web-check` must pass before a phase is merged.
