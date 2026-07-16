# Code Review - AgFields Watershed Parent Job

## Scope

Independent read-only review covered the Run All route, suite worker,
failure-tolerant dependencies, recursive status/cancellation, response contract,
frontend tracking, and focused tests.

## Findings and Disposition

| Severity | Finding | Disposition |
| --- | --- | --- |
| High | Concept 2, hybrid, and the finalizer could remain deferred when a predecessor failed before dependent registration. | Applied the Batch Runner ready-deferred release guard after every failure-tolerant enqueue; added met/unmet and call-order regressions. |
| High | Parent metadata and cancellation could race during child dispatch. | Stored the complete planned tree in parent enqueue metadata and added a shared dispatch/cancel lock plus marker. The worker refreshes and checks the marker before any save, state write, or child enqueue. |
| High | Global run authorization initially broke the legacy Culvert cancellation credential. | Cancellation now collects all accepted scopes, permits the Culvert path only for server-owned `culvert_batch_uuid` metadata, and otherwise enforces normal run access. Single- and dual-scope Culvert plus non-Culvert denial regressions pass. |
| Medium | Suite children emitted the same terminal trigger as the finalizer. | Suite-owned children emit completion records without the terminal trigger; only the finalizer publishes it. |
| Medium | Child audit metadata was saved after enqueue. | Parent, child, and finalizer metadata are supplied atomically in `enqueue_call(meta=...)`. |
| Medium | AgFields' named `job_ids` response differed from the general list contract. | Documented the already-shipped named-child compatibility form; `job_id` is the tree root and the mapping contains domain children. |
| Low | Finalizer wording included stopped/canceled dependencies not released by RQ `allow_failure`. | Narrowed the contract to finished/failed; suite cancellation cancels the finalizer. |

## Verification and Verdict

- Final reviewer-focused suite: 43 tests passed.
- No unresolved actionable findings.
- **Verdict**: pass.
