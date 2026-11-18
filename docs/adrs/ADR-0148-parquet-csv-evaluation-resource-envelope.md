# ADR-0148: Parquet CSV evaluation resource envelope

Status: Accepted for standalone evaluation only
Date: 2026-11-18

## Context

The production Python exporter retains complete CSVs and creates Python objects
for every cell. Observed long conversions motivate an isolated Rust evaluation.
The selected local corpus includes a 3,004,240-row, 51 MB compressed H.wat file.
An initial 385,704-row event export took 37.13 seconds and 374.6 MiB peak RSS in
the current exporter; native PyArrow took 0.72 seconds but emitted different float
representations. These initial measurements are preliminary baseline evidence.

## Decision

Use the ceilings in the [standalone contract](../schemas/parquet-csv-cli-contract.md#resource-envelope):
512 MiB input, 2 GiB output, 1 GiB address space, 120 CPU seconds, 180 wall seconds
each for staging/conversion, 64 descriptors, no core dumps, two shared file-lock
slots retained through artifact cleanup. Fixed batch size is 8192 rows.
Use bounded same-descriptor footer/page preflight with 4 GiB cumulative decoded
bytes, 10 million rows and the other structural limits listed in the contract.
These are initial evaluation limits, not production defaults or scientific changes.
Only tightening is permitted without an amended checkpoint.

## Rationale and alternatives

The corpus requires more than the GeoParquet upload parser's 100,000-row and
128 MiB cumulative decode bounds, while flat schema, page and dictionary bounds
can remain narrow. Address-space and CPU rlimits bound decoder failures; page
preflight prevents trusting oversized allocation claims. Two slots plus retained
artifact ownership cap ordinary scratch occupancy and avoid queuing work.
No new queue, daemon or privileged cgroup manager is justified for this evaluation.
A per-process semaphore cannot provide cross-process admission. A whole-output
memory buffer defeats the intended memory improvement. Thread counts are one to
avoid oversubscription across callers.

## Decision provenance

Venue: user/Codex session, 2026-11-18 UTC.
Participants: Roger Lew (operator), Codex (implementer).
Operator instruction: "commit scaffold and implement the work-package".
Decision owner: Roger Lew for standalone scope; Codex selects bounded evaluation
parameters under that instruction. No operator approval of runtime integration is
implied. Independent checkpoint review precedes implementation.

## Validation, consequences and recovery

Require byte-compatible outputs for the supported corpus, 2x median speedup versus
current Python and at most 512 MiB parent-plus-child RSS. Native PyArrow is a
comparator, not an authorized replacement. Exercise every limit with real children,
near-limit valid inputs, cancellation, overflow, denied files and no-space failures.
No-go if legitimate selected inputs exceed ceilings; do not silently increase them.
Same-UID adversaries and harness SIGKILL scratch cleanup are explicit limitations.
Removing isolated evaluation artifacts is rollback; no production change occurs.

## Evidence

See `docs/work-packages/20261118_parquet_csv_cli/artifacts/` for corpus, baseline,
dependency evaluation, checkpoint reviews, tests and final decision. Evidence
pending at initial checkpoint must remain marked pending rather than inferred.
