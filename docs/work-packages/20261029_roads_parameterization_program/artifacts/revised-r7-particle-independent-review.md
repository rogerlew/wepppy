# Independent review: exact r7 particle disposition

Verdict: **accept the bounded source-supported arithmetic disposition** under the
current [adjudication contract](../../../schemas/roads-parameterization-adjudication-contract.md#defect-adjudication).
No unresolved correctness or scientific finding in the reviewed observation.
The strict EVENT fraction predicate remains failed; neither its bound nor the
historical 839/840 result changes. This is not a new default, model correction,
field-calibration claim or universal conservation certificate.

## Independently checked evidence

Reviewed raw bundle:
`/wc1/runs/ro/roads-parameterization-program-20261103/particle-observation-r7-v3`.
The [readback helper](review_revised_r7_particle.py) and
[receipt](revised-r7-particle-independent-readback.json) reproduce this review
without another native run. All 824 retention-manifest files match. A fresh
`git archive` of exact source `e0abe0581f77c6f66917e90daf8f8f429e9315c8`,
including `src` and `fpm-src`, matches the retained source archive. Installed
watershed/hill hashes match the declaration. The ordinary rebuilt binary has a
different hash from the installed binary; equivalence is established for this
case by all seven full-period output hashes, not asserted from its filename.

Both ordinary and observer executions preserve every declared input (including
runtime sidecars) and reproduce all seven retained r7 outputs exactly. Their
separate binary hashes, source-record identity, declaration, trace and output
receipts are internally consistent. Declaration SHA256:
`6ba6bc25b859fae41d53985279bccdc0d3fdab83b7fc8d9b9d97688b8b5dd789`.
Result SHA256:
`720974c4780c4225b37438c4cc8a7b51d8d8bf2a3d0cb15965d55be76175690a`.

The source diff adds only event-gated writes immediately before ENRICH class
division and after SLOSS computes its nonnegative `avsole`. ENRICH additionally
includes `cupdate.inc` to read the real shared event calendar; it makes no
assignment to that calendar. Existing model assignments, ordering and arithmetic
are unchanged. The two original source files match the pinned archive. The trace
has exactly one class observation and one final observation for 2003/day 29,
terminal OFE 3, with the normalized fractions reaching SLOSS unchanged.

## Arithmetic and strict predicate

An independent binary32 reconstruction reproduces the five positive class-load
sum and every division exactly. All loads are normal positive binary32 values.
Four nontrivial sequential additions followed by the per-class divisions give
unit-roundoff `u = 2^-24`, `gamma4 = 4u/(1-4u)` and the bound
`(gamma4 + u)/(1-gamma4) = 2.9802335177470655e-7` on the fraction-sum residual.
The exact observed excess is `2.727057517697422e-8`. This bound derives from the
observed operation sequence; it is not a replacement audit tolerance.

Re-running the unchanged version-2 strict auditor yields the same sole
`fraction_sum` flag, 163 EVENT records and 145 positive EVENT records. Each
printed fraction is within its existing individual half-last-place bound of its
observed binary32 value. Exact rational decomposition establishes that the
printed excess equals native normalization excess plus print rounding. Thus
this particular printed flag is explained by the current r7 state, without
transferring the r4 certificate from matching rounded operands. The class/bulk
mass predicate already passes unchanged.

## Disposition and limits

The issue register may close the **unexplained numerical finding** for this
exact case/event as an explained floating-point normalization/serialization
residual. It must preserve `particle_pass=false` and the historical strict audit.
No implementation correction is required by this evidence. It does not prove
complete water/sediment conservation, validate other events' internal states,
certify unrelated designs or accept any Roads parameterization.

The two earlier observation attempts remain visible: v1 failed build because
`fpm-src` was absent; v2 lacked the shared calendar binding and failed the
observation certificate. Those are experiment failures, not successful model
certificates. The v3 result supplies the missing current-source evidence.
