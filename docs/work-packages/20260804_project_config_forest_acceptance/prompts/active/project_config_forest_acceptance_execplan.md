# Accept project-owned configuration on Forest

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, operators have production-like evidence that the complete
project-owned configuration stack can run on Forest, survive restart and
lifecycle operations, and roll back without losing defaults compatibility.
The accepted revision remains noncanonical until WP12 merges and deploys it to
production.

## Progress

- [x] (2026-08-26) Read the rollout contract, roadmap, WP01 handoff, deploy entry point, and Forest runbooks.
- [x] (2026-08-26) Scaffold WP11 and record Forest-only safety/rollback scope.
- [ ] Add default-off Compose flag passthrough and local contract tests.
- [ ] Push and deploy the exact candidate revision to Forest twice.
- [ ] Execute the complete deployed acceptance and rollback matrix.
- [ ] Review evidence, archive, close, commit, and push.

## Surprises & Discoveries

- Observation: the four Python feature flags are absent from production
  Compose's shared environment map.
  Evidence: `rg WEPPPY_PROJECT_CONFIG docker` returns no production wiring.

## Decision Log

- Decision: pass all four flags through the shared production Compose anchor
  with explicit `false` defaults and keep Forest values in `docker/.env`.
  Rationale: every web/RQ reader and writer receives one fleet-consistent state,
  an absent host value remains safe, and no tracked file carries environment-
  specific activation.
  Date/Author: 2026-08-26, Codex.

## Outcomes & Retrospective

In progress.

## Context and Orientation

Forest test production is host `forest1` with checkout `/workdir/wepppy` and
production Compose file `docker/docker-compose.prod.yml`. The only canonical
full deploy entry point is `./scripts/deploy-production.sh` with no arguments.
The initiative candidate is branch `feature/project-owned-config`; production
remains `master`. Four independent strict flags control the reader, preset
writer, builder writer, and additive update path.

## Plan of Work

First wire and test the four flags through production Compose, defaulting each
to false. Commit and push the candidate so Forest can fast-forward a clean
feature-branch checkout. Inventory current containers, revision, flags, shared
defaults alias, and rollback target without exposing secret values.

Deploy with the exact no-argument command. With writers off, prove stack health,
legacy/defaults compatibility, flattened reading, and worker revision parity.
Then set Forest-only flags, redeploy, and exercise the registered four-way
DEM/backend matrix, named preset, builder, climate/soil/land-use paths, update,
restart, fork, archive, restore, and degraded-manifest behavior. Use disposable
acceptance run IDs and record only safe summaries and hashes.

Rehearse rollback to the recorded compatible `master` revision while the shared
alias remains, verify the rollback reader/defaults contract, then restore the
accepted candidate and rerun health/read probes. Run the canonical full deploy
again for idempotence and retain exact service/revision evidence.

## Concrete Steps

Work locally in `/home/workdir/wepppy` and remotely in `/workdir/wepppy` on
`forest1`. Use `wctl`/pytest locally and `./scripts/deploy-production.sh` on
Forest. Before every remote mutation, verify hostname, clean checkout, branch,
revision, and Compose plan. Do not print `docker/.env` or secret values.

## Validation and Acceptance

Acceptance requires exact deployed revision and container-image labels/hashes,
all required services healthy, identical shared alias bytes, an older-reader
probe, unchanged legacy effective values, flattened reader isolation, supported
creation combinations, representative model preparation, additive update,
restart/reopen, byte-preserving lifecycle, and successful rollback/restoration.
Every unexecuted item must have a specific blocking disposition; unsupported or
failing combinations remain disabled.

## Idempotence and Recovery

The deploy script is designed for repeated full runs and performs safe
fast-forward pulls. Disposable acceptance projects use unique run IDs. Rollback
uses the recorded prior revision and preserves the shared alias. If candidate
health fails, stop activation tests, return Forest to the prior known-good
revision, and record the failure without touching production.

## Artifacts and Notes

Store sanitized deployment inventory, matrix results, rollback transcript,
security review, and final validation under `artifacts/`.

## Interfaces and Dependencies

No new dependency. Use production Compose, the existing project config flags,
canonical rq-engine APIs/test fixtures, `/wc1/runs`, and the existing archive
and fork workers. The forest1 companion-worker skill applies only if the
separate batch companion must be inspected; it is not a substitute for the
main production stack workers.

Plan revision note (2026-08-26): initial executable plan.
