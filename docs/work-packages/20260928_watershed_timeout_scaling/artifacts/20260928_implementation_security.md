# WRT-01 implementation security and noninterference review

Reviewer: independent `timeout_contract_security` agent. Date: 2026-09-28.
Contract ancestor: `728965382` (verified ancestor of HEAD). Reviewed working-tree
implementation against that checkpoint. Verdict: approved, no blocking security
or noninterference findings; final runtime evidence disposition follows below.

## Reviewed boundaries

`wepppy/rq/watershed_timeout.py` reads only the fixed owned `pw0.run` path. Its
binary read is bounded to 1 MiB plus one overflow-detection byte; oversized files
are rejected. Decoding and workload errors propagate explicitly. Parsing strips
comments, recognizes owned legacy/modern prompt positions and never opens or
executes paths named in the content. The reader extracts workload; it is not a
new complete native-input validator. It does not write source artifacts.

Positive integral admission rejects booleans, floats, nonfinite values and
malformed integer strings. Exact integer arithmetic rounds whole-hour budgets;
both computed and supplied continuous budgets must fit the positive RQ alarm
range. There is no unlimited-timeout sentinel or silent workload fallback.
The larger authorized resource allowance is the approved policy, not a new
caller-controlled API field.

All four pipeline entry points calculate required budgets before enqueueing any
child. Hillslope-only and preparation-only paths do not introduce required
workload reads. The shared helper returns early for single-storm modes, including
batch and user-defined single storms through the existing controller property.
Only continuous watershed child timeout and additive metadata change.

The enqueue helper copies the supplied metadata, merges matching fork-failure
lineage and retains the existing failure callback. Parent lineage is not
overwritten. No authorization, lock, model input, subprocess lifecycle, retry,
output or dependency semantics change was found.

## Evidence inspected

New tests directly create/read owned native run files for legacy and modern
binaries, assert unchanged bytes, and exercise missing, empty, oversized,
malformed-mode/count/year and invalid-encoding inputs. Arithmetic tests cover
rounding boundaries, floors, legacy integer strings, invalid types and alarm
overflow. Pipeline tests cover all four entry points, early failure before child
or parent mutation, unrelated-stage allowances, single-storm/batch exclusions,
missing unused workload, and fork metadata/callback retention.

## Runtime evidence disposition

Follow-up inspected the C1 structural-reader correction: hillslope block size and
owned prompt anchors now reject truncated layouts, appended years and inflated
counts. The count is checked against bounded input length before iteration.
Focused execution passed 98 tests (`/tmp/wrt-focused.log`), including direct
filesystem and new structural-rejection tests.

Inspected [retained live evidence](live_rq.json) and its
[reproducible harness](verify_live_rq.py). All four actual Redis graphs store
97,200-second continuous watershed budgets, retain fork lineage and the failure
callback, and leave unrelated stage allowances unchanged. The normal `job_info`
reader observes their children. Source SHA-256 hashes match before/after in all
four cases, including stale-controller no-prep cases. Cleanup confirms removal
of the harness's 41 disposable job records.

Graphs were deliberately not executed. No native model rerun is claimed: native
code and input writers are unchanged, and the changed persistence boundary is
the serialized RQ budget/metadata. Full-suite regression execution remains the
owner's separate package gate. No production retry, deployment or service restart
is approved by this review.
