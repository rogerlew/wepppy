# Pilot operator independent correctness review

Disposition: **PASS for local implementation; production pilot acceptance remains pending.**
Reviewer: roads_contract_review (independent of operator/controller implementation).

Reviewed `tools/query_catalog_pilot.py` and `tests/tools/test_query_catalog_pilot_cli.py`
against the bounded-pilot catalog/deployment contracts and acceptance specification.
No production operations were performed by this review.

## Findings closed

- Scheduler cadence originally started 30 seconds after a tick ended. It now
  schedules from the tick start, matching the capacity analysis and contract.
- Raw ordinary-job observation originally excluded all reserved-prefix IDs.
  It now excludes only IDs authorized by the global ledger; an unknown
  prefix-shaped job remains ordinary and contributes wait evidence.
- Initial observation/resume originally sat outside the failure boundary.
  Startup now persists pause/failure through the same boundary, and a failed
  post-renewal observation pauses immediately in the observer thread.
- Missing global accounting is handled before numeric outstanding comparisons.
- Explicit receipt waves retry capacity-deferred requests after inventory
  completion. They do not depend on the disabled ordinary dirty index.

## Correctness evidence

Exclusive fixture preparation uses eight independent copies plus an excluded
sentinel, immutable marker/locator checks, and live source hashes/schema/row
counts. Raw catalog publication, incarnation, digest and pending receipts are
checked before consumer queries; consumers cannot repair output into acceptance.
A second explicit receipt wave requires acknowledgment readback and distinct
finished job lineage. Incomplete receipt creation cannot silently replay after
restart. Existing failed acceptance remains failed across manual resume.

The observer continues during admission pause and admitted-work drain. It reads
raw queue/job fields without deserialization, retains observed ordinary wait
intervals through started transitions, treats missing accounting as uncertain,
and cannot blindly renew after observation failure. The explicit drain command
does not resume admissions or depend on successful artifact setup. General
asynchronous refresh remains disabled; negative controls preserve the sentinel.

Focused controller tests include actual publication/DuckDB readback plus
controller sequencing, observation failure, lease/accounting uncertainty,
unknown-prefix classification, interrupted receipt waves and capacity retry.
See `pilot-operator-tests.log` for the implementation author's retained run.
The reviewer also inspected all test assertions and the final implementation;
this review does not substitute those local tests for production identity,
shared-batch contention, installed-image parity or scientific pilot evidence.

Final follow-up review: artifact identity now checks the exact admitted path set,
namespace, scope ID, incarnation and inode before raw readback, before consumer
queries and after queries. Both operator entry points supply immutable manifest
bindings. A rotated incarnation with a newly valid catalog is rejected, closing
the self-consistent-but-wrong-incarnation acceptance gap. Final retained run:
**24 passed**, including that regression.

## Reviewed hashes

- `tools/query_catalog_pilot.py`:
  `1f22c196845ff394747b6286593a7f69329430b2cea507d6550ccb9b084ea1c5`
- `tests/tools/test_query_catalog_pilot_cli.py`:
  `8c9b06e58c90302db03b439f23bbfb7f6f76d2415e1ad5eedf5ae48e2d8bacaa`
