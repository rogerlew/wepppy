# WRT-01 independent contract and security review

Reviewer: independent `timeout_contract_security` agent. Date: 2026-09-28.
Review phase: before production implementation. Verdict: approved; no blocking
findings. This approves the contract, not unimplemented runtime conformance.

Reviewed WRT-01 in `docs/schemas/wepp-run-input-contract.md`, ADR-0076, the
package/checkpoint/active plan, current pipeline enqueue and fork-failure metadata
behavior, and the runner's owned watershed input generation boundary.

## Authority and scope

The operator authorized years-plus-hillslopes scaling. The finite integer policy,
12-hour floor, preservation of larger existing pipeline allowances and explicit
platform range are consistent with that direction. Applying it only to continuous
watershed children avoids extending unrelated work. No endpoint, authentication,
serialization, scientific input or dependency-edge change is authorized here.
Subprocess cleanup, production retries and deployment remain explicitly separate.

## Admission and noninterference

Reading the fixed owned prepared run file for no-preparation is appropriate:
current NoDb settings can disagree with the artifact actually executed. The
1 MiB admission bound limits parsing resources; malformed or oversized input
must fail explicitly without rewriting or following paths named inside the file.
Required positive integral workload and positive alarm-range timeout checks must
run before the first child enqueue. Integer arithmetic avoids floating-point
rounding and overflow surprises in the workload product.

Unused workload remains unread for single-storm, hillslope-only and prep-only
paths. Integer-string legacy years and both supported prompt layouts remain
valid. Missing optional fork lineage is not corruption. Additive timeout metadata
must merge with existing lineage and retain its failure callback. These provisions
cover both valid-state usability and rejection of malformed required state.

## Resource implications and final evidence

Larger authorized workloads occupy workers longer. The formula has no newly
invented service quota; the explicit positive alarm-range limit prevents invalid
native timeout values. This is a bounded policy change, not a guarantee of
runtime or queue availability. Successful-job sampling bias is recorded in the
ADR and does not justify silently changing the approved coefficient.

Final review should verify actual bounded file reads (including oversized and
malformed files), nonintegral/nonfinite/bool workload rejection, timeout overflow,
no partial graphs, unchanged non-watershed stages, fork metadata/callback
retention, and real Redis job serialization. At least one unmocked prepared-file
read and retained before/after source hashes are required. These are planned
conformance obligations, not findings against the accepted contract.
