# Commit culture and versioning

## Commits

- Work directly on the established `main` branch.
- Keep one cohesive, reviewable change and stage paths deliberately; never use
  `git add -A`.
- Use a short imperative, sentence-case title with no trailing period.
- A release title carries its version, for example
  `Define optional recalibration contract — v0.2.0`.
- Explain the observable contract and reason in the body.
- End an agent-authored commit with a bare `agent: <name>` line and nothing
  after it. Do not add email, link, generated-with, or co-author trailers.
- Never push or tag unless queezz explicitly asks.

## Versions

The version describes the public container contract:

| Change | Bump |
|---|---|
| Compatible correction or documentation clarification | patch |
| New optional field, schema, or public capability | minor |
| Intentional incompatible format or API change | major |

Synchronize the manifest, runtime version, root and installed specification,
documentation, public changelog, and installed changelog in the release commit.
Tests enforce the public copies.

## Before committing

1. Inspect status, the complete diff, `git diff --check`, and staged contents.
2. Run every source gate in `../AGENTS.md`.
3. Build wheel and sdist from an external final-candidate copy.
4. Run Twine metadata validation and inspect both archives for required docs,
   specification resources, and absence of caches/build debris.
5. Install the wheel into a fresh external environment and run both entry
   points, import/version, plain-cube, optional-contract, and NetCDF smokes.
6. Record exact commands, results, artifact sizes/hashes, limitations, and
   scratch lifecycle in a dated log.

Do not add a lockfile by default. This small library follows Fleet's
lower-bound dependency convention; a lockfile is adopted only by an explicit
project policy change.
