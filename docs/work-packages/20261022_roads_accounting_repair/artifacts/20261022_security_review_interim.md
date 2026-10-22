# Roads accounting interim integration and security review

Date: 2026-10-22 UTC. Reviewer: Codex integration_contract_review.
Checkpoint ancestor: `83f7410e8`. Runtime implementation is in progress.
Disposition: **Open findings; no final security or production acceptance.**

## Scope and trust boundaries

Reviewed `wepppy/wepp/interchange/roads_accounting.py`, Roads orchestration,
`hillslope_watbal.py`, native `totalwatsed/roads.rs`, and paired publication code.
Numerical reduction receives a separate native review. The authority is the
[Roads modeled-area contract](../../../schemas/roads-water-accounting-contract.md),
including source isolation, readiness, historical-result and optional-state rules.

WEPPpy selects run-local original sources, writes a ledger, composes routing PASS,
and publishes derived reports. Baseline bytes must remain immutable. Existing
Roads RQ single-flight locking is present; no auth, endpoint or queue change was
identified. Single-flight Roads locking does not establish that baseline files
remain unchanged while they are read. Filesystem aliases and stale restored
metadata are relevant integrity boundaries even without a new public endpoint.

## Findings

| ID | Severity | Finding and evidence | Disposition |
| --- | --- | --- | --- |
| SEC-01 | High | Original `_path` confined writes only to the run root. A Roads output directory aliased to baseline was accepted; compose unlinked baseline H1.pass.dat and then failed copying it. Real scratch filesystem reproduction confirmed deletion. New `_destination` rejects the direct compose case before mutation, but controller conversion runs before regenerate's destination check. Interchange converters can therefore write through a Roads-interchange alias before rejection, especially with zero contributors and no Roads WAT dependency. | Direct compose/regenerate fix inspected and retested; controller preconversion gate still required at this snapshot. |
| SEC-02 | High | Ledger-file presence alone selected corrected behavior. Missing ledger with retained marked accounting products silently selected raw water/historical regeneration. New `has_accounting` detects retained corrected files/markers. | Fix inspected; missing-ledger route/consumer regression evidence pending. |
| SEC-03 | High | `load` checks input/product file hashes but does not bind the allocation to composed PASS, routing or products. Scratch compose of a 100 m2 source followed by a ledger-only change to represented/target area 200 m2 is accepted by load while canonical PASS still represents 100 m2. A routed/ready ledger can thus change water weighting without reconstruction. | Open: validate ledger shape and allocation invariants and bind a stable allocation identity to composition/routing/product receipts. |
| SEC-04 | High | Source geometry/header reads occur before input hashes are captured. Source replacement between these operations can bind stale areas to a newer digest. Regeneration checks sources before native production but does not recheck inputs after reading and before writing ready state. | Open: capture observations before consuming source bytes and verify unchanged inputs/ledger generation before publication/readiness. |
| SEC-05 | Medium | `_save` uses mkstemp followed by replace without mode preservation. Direct scratch inspection found new ledger mode 0600; replacement also narrows a previously shared ledger. Required report readers may use a different service identity/group. | Open: preserve existing mode and first-create umask semantics; prove real reader access under applicable worker/web identities. |
| INT-01 | Medium | Average-hillslope reports validate accounting provenance, but `TotalWatbalReport`, streamflow and return-period reads still consume scoped totalwatsed directly. Marked stale output can be accepted by yearly/daily consumers while average reporting rejects it. | Open: apply the same corrected-versus-historical admission at affected aggregate read boundaries, or resolve the contract scope explicitly. |

## Direct boundary evidence

Scratch experiments loaded the exact current Python orchestration functions
through AST extraction, with native geometry mocked only to return fixture area.
Filesystem operations, hashing, ledger serialization, alias resolution, unlink
and copying remained real. No project data or runtime code was modified.

Before the destination fix:

```text
output accepted inside baseline: True
compose raised: FileNotFoundError
original baseline still exists: False
```

After the direct destination fix:

```text
alias rejected before mutation: Roads destination alias: wepp/roads/output/interchange/totalwatsed3.parquet
baseline preserved: True
new ledger mode: 0o600
altered allocation accepted by load: 200.0
```

These experiments establish the orchestration/filesystem findings, not native
numerical correctness. The controller preconversion alias case is established
by call order and remains to receive its own direct regression test.

## Valid-state and failure coverage still required

| State | Required behavior | Review evidence |
| --- | --- | --- |
| No prior accounting, valid sources | Create ledger/products with normal reader access | Basic compose tests exist; real identity coverage pending. |
| Empty contributor manifest | Preserve baseline response and original bytes | Compose byte-parity test exists; preconversion alias test pending. |
| Populated additive/replacement ledger | Same allocation consumed by PASS, routing and both water products | UM1 execution reported by primary agent; independent artifact readback pending. |
| Historical unmarked outputs | Retain historical behavior without certifying correction | Source selection inspected; route tests pending. |
| Marked outputs with missing/changed ledger | Fail corrected admission without raw fallback | New detector inspected; full consumer matrix pending. |
| Optional sources absent/empty/partial | Preserve contracted availability/support weights | Separate native numerical review owns result validation. |
| Destination alias or input drift | Fail before corrupting baseline or claiming ready products | Direct compose alias retest passes; other findings above remain. |
| Writer failure or process interruption | Explicit non-ready state; retained source bytes and bounded residue | Native staged pair publication inspected; orchestration failure tests pending. |

## Remaining gates

Close findings with focused unmocked tests at each changed filesystem/persistence
boundary. Verify first-create and replacement permissions and immutable baseline
hashes under worker-equivalent execution. Validate derived outputs and report
readers after input/allocation changes, including equal timestamps. Retain the
separate numerical review, final independent correctness review and actual UM1
artifact chain. This interim review does not authorize deployment or in-place
historical regeneration.
