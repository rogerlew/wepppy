# AgFields Run All Job-Tree Compatibility Plan

## Current contract

Run All returns the Concept 1 job as `job_id` and three scheme IDs in `job_ids`.
The three jobs are serial dependencies but are not descendants of one root, so a
job dashboard, cancel request, or operator poll cannot address the suite as one
unit.

## Additive and intentional changes

- Add RedisPrep/state key `agfields_run_watershed_suite`.
- Change only Run All's `job_id` meaning from first scheme job to suite parent.
- Keep `job_ids` and every scheme-specific key/NoDb entry unchanged.
- Keep the historical `agfields_run_watershed` Concept 2 alias unchanged.
- Add canonical ordered `jobs:*` parent metadata.
- Preserve the preexisting named-child `job_ids` response as the documented
  compatibility form in `docs/schemas/rq-response-contract.md`; `job_id` is the
  registered root while the mapping contains its three domain children.
- Add one finalizer child that depends on all three schemes with
  `allow_failure=True`; it is not added to the scheme-only `job_ids` mapping.

No NoDb schema, route path, request field, scheme identifier, output path, or
generated artifact schema changes.

## Downstream propagation checks

- Route response: parent plus the same three child mappings.
- State response: additive suite parent key plus existing scheme keys.
- Browser: top-level polling/dashboard link uses parent; scheme cards use child
  IDs and persisted scheme state.
- Job status/info: recursive tree represents all children and stays non-terminal
  while any descendant is active.
- Cancellation: parent request is run-authorized and synchronizes with dispatch
  before reaching every registered child. The legacy Culvert cancellation scope
  remains limited to jobs carrying verified Culvert batch metadata.
- Artifacts: all three existing fixed roots complete; no `all/` tree appears.

## Regression matrix

| Case | Expected result |
| --- | --- |
| Omitted/default Concept 2 | One direct job; Concept 2 alias preserved |
| Explicit single scheme | One direct job and one-entry `job_ids` |
| Run All | One parent response plus three distinct child IDs |
| Any scheme child fails | Finalizer waits for all schemes, then still runs |
| First child fails, second active | Parent status remains non-terminal |
| All children terminal, one failed | Parent status is failed |
| Cancel after dispatch parent finishes | Active descendants are canceled |
| Browser reload during suite | Suite parent remains the tracked top-level job |
| Successful live suite | Three fixed output roots and terminal evidence |
