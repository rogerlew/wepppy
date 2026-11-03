# Independent native override protocol review

Reviewer: `override_protocol_review`, 2026-11-03. Current disposition: **v5 approved for 18 native calls**. Earlier v2 approval
was revoked before execution due to inherited OFE/calendar assumptions. The
chronological findings and replacement approval are retained below.

Declaration `parameterization-overrides-v1/declaration-v2.json` SHA256:
`0fcf213cf4cd0a981c5096aaa2310f2979956cad713ffcd8a8392c1704c5d79a`.
Raw root: `/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-overrides-v1`.
The exact approval and independent paired-file checks are retained there as
`execution-review.json` and `protocol-independent-input-readback.json`.

Independently verified all 110 dependency hashes and each prepared input inventory,
including native reader library and installed binary pair. Checked five native
source snapshots against both r7 source commit and release worktree. All 18 cases
were unstarted. Both contexts use loam/gravel/low traffic production-template
fixtures; no generated soil material or reserved cases are selected.

For each of 16 contrasts, only `p1.sol` changes from its context baseline and
canonical prepared input inventory. Exactly one token on the Road header changes
by the declared half/double factor. All non-road rows, management, slope, climate
and runtime sidecars remain byte-identical within context. Baselines have no
input changes. Verified concrete values: AVKE 4.05/8.1/16.2 mm/h, Ki
250000/500000/1000000, Kr 0.0000375/0.000075/0.00015, shear 1/2/4 Pa.

The maintained executor rejects extra/drifted inputs, mismatched calendar context,
repeat execution and binary drift. It retains native outputs/failures and runs
strict physical/calendar/particle checks, production summary readers and paired
event analysis. Native header consumption is source-supported; final directional
response and output claims still require independent post-execution review.
No field-calibration, universal monotonicity, fill/buffer-override sensitivity or
production persistence/UI conformance claim is supported by this protocol.

## Reproducibility finding

`declare()` currently creates a fresh root and immediately calls `dependencies()`,
which expects `native-source` already present. Therefore the protocol's standalone
`declare` command cannot bootstrap a new empty root as written. The existing
capsules and native snapshots were independently verified and are executable;
this does not invalidate their input identities. The owner must retain additive
setup/bootstrap instructions and original setup history, without modifying the
frozen v2 script or protocol. Full reproducibility closure awaits that supplement.

## Preexecution revocation

The owner identified that the inherited `prior.audit` ultimately calls an audit
that assumes three OFEs and historical climate labels. The 1-OFE fixture context
would fail after native execution. No native calls occurred. The initially written
v2 approval is preserved with `execution-review-v2-revoked.json`; v2 must not run.
The initial review missed these transitive assumptions. Review the replacement
adapter directly before approving a new declaration.

## Replacement v5 approval

**PASS for 18 native calls under v5**, declaration SHA256
`5027d7fcb802f18d5e20743d3c6e4e8c77aaa34db1347e23503c34daa32aaaab`.
`execution-review-v5.json` is the only operative approval. All prepared scientific
inputs are identical to v2; all 141 dependency hashes and each prepared input
were rechecked before any execution start. v3/v4 are unused intermediate bindings.

Reviewed the replacement adapter directly. Private particle/completeness module
instances bind terminal OFE to the actual declared role count, without changing
particle predicates. Calendar comes from actual fixture dates. It no longer calls
the historical three-OFE physical audit. LOSS/ELEMENT and EBE comparison bounds
are identical to the original accounting functions: daily/annual half-unit
0.0005 and EBE half-unit sum 0.0505, plus the existing relative term. The original
nonempty EBE-event predicate is preserved.

The physical evidence is deliberately narrower than complete water-budget
closure: finite/nonnegative raw water/sediment fields, full WAT role calendars,
actual emitted WAT areas and printed terminal sediment reconciliation. Do not
claim complete storage/cross-role water closure. Fresh declaration now stages
native snapshots and supports an exclusive `--root`, with the declared output
path matching execution. Original v2/v3/v4 script snapshots and declarations remain
retained. No source or numeric acceptance bound was changed to fit an outcome.
