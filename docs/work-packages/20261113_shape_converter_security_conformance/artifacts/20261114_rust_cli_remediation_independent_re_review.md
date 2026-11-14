# Rust CLI remediation independent re-review

Date: 2026-11-14

Review target: `2bbf8498e` (implementation `7b1f0bd85`, resource invariant
`21a12c9d0`, evidence `2bbf8498e`)

Overall verdict: **FAIL / HOLD**. Do not close #656 or roll out.

## Code review

Verdict: FAIL / HOLD. Critical 0; High 1; Medium 1; Low 1.

- High: parser wait is asynchronous, but archive extraction, inspection,
  reprojection, GeoJSON/GeoParquet construction, encoding, and output writes can
  still block the sole ASGI event loop. No real blocked-conversion plus
  concurrent-health/cancellation regression proves the normative availability
  contract.
- Medium: canceling an `asyncio.to_thread` payload decode cancels its awaiter,
  not the thread. Scratch and the single-flight slot can be released while the
  old thread still retains JSON/geometry allocations.
- Low: deployment takedown has textual assertions but no fault-injected execution
  test.

Prior record alignment, LDID mapping, provenance, and manifest findings are
closed. Parser-child cancellation is fixed; whole-handler cancellation remains
open.

## Correctness review

Verdict: FAIL / HOLD. Critical 0; High 1; Medium 1.

- High: an independent probe reproduced `request_task_done=True` while the
  decode thread remained active. Repeated cancelations can therefore multiply
  the parent-memory envelope despite global concurrency one. The request must
  retain admission and scratch ownership until bounded decode completion.
- Medium: direct coverage still omits MultiPoint/M variants, multipart
  line/polygon, logical and supported-LDID DBF cases, and FirstRing/Ring/
  TriangleFan MultiPatch behavior. The `Ring` policy is not validated against
  the retained Fiona oracle.

Focused rerun: 28 passed.

## QA review

Verdict: FAIL / HOLD. Critical 0; High 0; Medium 2; Low 0.

- Medium: the ratified semantic matrix remains incomplete for MultiPoint, M
  variants, multipart line/polygon, logical/supported-LDID values, and remaining
  MultiPatch patch families.
- Medium: reproducible CPU/address-space/core, parser panic/abort, malformed
  parts, concurrent readiness, and retained near-ceiling fixture tooling remain
  incomplete. The nonexistent ExecPlan command was corrected.

Focused rerun: 26 passed.

## Operations review

Verdict: FAIL / HOLD for rollout. Critical 0; High 1; Medium 2.

- High: readiness-failure takedown is implemented but not execution-tested by
  the deploy harness. Required evidence is failure to nonzero exit, stop and
  verify no running converter, no prune/success banner, and unrelated-service
  preservation.
- Medium: `--skip-pull` can build dirty shape-converter inputs while labeling
  them with clean `HEAD`; relevant tracked and untracked build inputs must be
  clean on every release build.
- Medium: 72 Medium Grype records lack traceable advisory/class dispositions.

Pinned snapshot/timestamp reproducibility and startup-cached readiness are
closed. Operator-authorized takedown validly supersedes parser rollback, subject
to executable evidence.

## Required remediation before another re-review

1. Preserve admission/scratch ownership across cancellation until every
   offloaded thread ends, and remove remaining heavy event-loop work or make it
   explicitly cancelable.
2. Enforce the reviewed resource envelope at startup/deploy, including unsafe
   override rejection.
3. Apply Rust resource limits before hostile path/record scanning and stop the
   alignment scan at `max_features`.
4. Add fault-injected deploy execution coverage for fail-closed takedown.
5. Enforce clean relevant build inputs even with `--skip-pull`.
6. Complete or explicitly narrow the semantic/resource matrix with operator
   approval and retained reproducible fixtures.
7. Provide traceable dispositions for all unique Medium scan advisories.

No reviewer modified repository files.
