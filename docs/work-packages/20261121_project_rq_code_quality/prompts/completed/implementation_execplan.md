# Extract WBT subcatchment job-state validation from project workers

This ExecPlan follows the [repository plan template](../../../../prompt_templates/codex_exec_plans.md).

## Purpose

WBT delineation writes a build job and a completion receipt to Redis. Retrying
the same orchestration job can reuse the pair when its stored links and queue
membership agree. Extracting the validation code lets a maintainer find that
policy without reading the surrounding project workers and transaction code.

## Progress

- [x] Locate the validation block and Redis-backed tests.
- [x] Move validation and wire it through the current admission flow.
- [x] Record test evidence and prepare the package for integration.

## Surprises & Discoveries

The existing test suite exercises live Redis queues under unique names. It
already checks saved job links, orphaned active jobs, and retries after a
transaction commits but its response is lost. The graph artifacts are
already stale on the base, so the check compared fresh graphs. The
dev image needed the repository-pinned Markdown wheel to collect the
Redis-backed slice.

## Decision Log

- **2026-11-22 06:07 UTC** — Keep the transaction in `project_rq.py` and move
  the inspection helpers together. This preserves serialized job function
  paths and keeps all pipeline writes under the original owner.

## Outcomes & Retrospective

The extracted helpers run through the existing worker admission paths.
All 86 focused tests passed. [Validation evidence](../../artifacts/validation.md)
records Redis readback, the unchanged graph, and the exact test commands.

## Implementation

In `wepppy/rq/project_rq.py`, move the consecutive helper block beginning at
`_decode_redis_text` and ending after `_load_exact_subcatchment_tree` into
`project_rq_subcatchment_state.py` in the same directory. Move the shared WBT
admission metadata keys with it and import the keys and the called helpers
back into the worker. The exact-tree validator checks persisted identity,
dependencies, active queue or registry location, and the current tail.
Keep its Redis read order, refresh flags, and failure messages. Point the
one test that calls the dependency reader directly at its new module.

## Validation and Acceptance

Run targeted pytest for `tests/rq/test_project_rq_mutation_guards.py` and the
WBT admission and retry cases in
`tests/rq/test_wbt_controlled_failure_integration.py`. Use the dev container
and isolated candidate, and read actual Redis queue and dependency state using
the existing test fixtures. Run `wctl check-rq-graph`, the changed-code
exception guard, and scoped Markdown lint. An AST comparison against the
base should confirm the moved functions and stable worker bodies.

After the checks, open a PR to master and require both governance checks on
the exact reviewed head. Merge preserving commits and record an integration
receipt in a subsequent audit commit.

## Recovery

Revert the PR merge to restore the previous source layout. Existing queued
function paths and record fields require no data migration.
