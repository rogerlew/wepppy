# ADR-0149: Parquet CSV integration resource envelope

Status: Accepted for integration; runtime acceptance pending
Date: 2026-11-18

## Context

The standalone envelope did not account for HTTP proxy first-byte deadlines or
worker death. wepp1 has eight Uvicorn workers, three-minute culvert/batch Caddy
read timeouts, and a Gunicorn heartbeat timeout of 120 seconds. The real corpus
fits existing byte/structural ceilings; standalone Rust conversion measured less
than 20 seconds on its largest evaluated input.

## Decision

Use code-owned staging 30 seconds, child wall 120 seconds, CPU 100 seconds and
serving 600 seconds. Keep two shared slots, 512 MiB input, 2 GiB output, 1 GiB
child address space and all standalone structural ceilings. Filtered CSV matches
are capped at 2,000,000 rows, preserving the existing default. These are resource
budgets, not scientific parameter changes. No environment override is available.

Inherit the flock descriptor into the child; install a child-owned wall alarm
and race-checked parent-death SIGKILL. Reclaim fixed per-slot directories only
while holding their persistent lock. Keep slots through serving completion.

## Decision provenance

Venue: operator/Codex session, 2026-11-18 UTC. Operator Roger Lew authorized
execution, immediate cutover, fixed configuration and no fallback. Codex selected
these bounded integration parameters from the observed proxy budget and accepted
standalone envelope; independent review and exact-image acceptance are required.

## Rationale and alternatives

The staging/conversion total of 150 seconds leaves 30 seconds of proxy margin.
A heartbeat timeout alone cannot bound a single async request. An inherited lock
plus fixed directories resolves parent-death accounting without a daemon or PID
scavenging. Two slots bound staged/output payload at 5 GiB per shared root and
child address space at 2 GiB. Separate replicas add separate budgets. A finite
serving deadline prevents slow readers retaining both slots indefinitely.

## Consequences and validation

Requests exceeding these budgets fail explicitly. Prove actual request/worker
responsiveness, cross-process admission, parent death, cancellation and slow-reader
cleanup with the real image. Do not claim a CPU limit bounds an I/O-blocked orphan;
its inherited lock remains held until exit. The retained compatibility inventory
and focused resource tests must establish valid corpus conformance before cutover.
Whole-release rollback uses the canonical deployment workflow; no runtime fallback.

## Evidence

[Integration contract](../schemas/parquet-csv-integration-contract.md#integration-implementation-checkpoint)
and [active package](../work-packages/20261118_parquet_csv_wepppy_integration/package.md).


## Dictionary compatibility amendment (2026-11-18)

Implementation corpus readback found legitimate flowpath and road-event exports
rejected by the standalone100,000 dictionary-entry ceiling. A bounded scan of
all inventoried dictionary headers found a maximum125,855 entries; see
[dictionary evidence](../work-packages/20261118_parquet_csv_wepppy_integration/artifacts/dictionary-compatibility.json).
The integrated limit becomes131,072 entries. This is the smallest conventional
power-of-two bound above observed use, not an unbounded decoder setting.

All8 MiB page limits,4 GiB cumulative decode,1 GiB address space, CPU/wall limits
and two-slot accounting remain unchanged. The additional32,000-ish entries add
bounded dictionary bookkeeping within those same process/page ceilings. Require
exact-boundary and limit-plus-one tests plus real flowpath/event byte readback.
Do not silently route these valid files back to Python. Independent contract
amendment review and a documentation ancestor precede changing the source limit.
