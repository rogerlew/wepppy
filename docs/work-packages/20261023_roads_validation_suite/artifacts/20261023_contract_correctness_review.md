# Independent Roads validation contract correctness review

Date: 2026-10-23. Reviewer: `accounting_contract_review`.
Starting revision: `a7ea23927`. Runtime and tests reviewed read only; this review
artifact is the reviewer's only edit.

## Disposition

**Approved for the contract checkpoint. No unresolved high or medium finding.**
Reviewed canonical contract SHA-256:
`10a8b6bc977066e3c156c13566dfffbef7e9a97cb6c1e808f323e5a6acf05e4e`.
Also reviewed the package, active ExecPlan and contract-decision artifact.
Approval establishes the proposed test/report contract, not successful execution
or scientific validation of outputs that have not yet been generated.

## Findings resolved before approval

- Production geometry fidelity: the contract now specifies OFE orders, the
  existing unrutted parity/clamp helper, requested versus emitted dimensions,
  clipping disclosure and native WAT area. Calling slope writers alone with
  original segment dimensions would bypass production preprocessing. Profile
  parity is explicitly separate from full-project strip allocation.
- Full-project effectiveness: each of the four design checks must execute
  nonzero completed profiles with the requested design and correct additive or
  replacement accounting. Explicit feature design replacement prevents existing
  attributes from overriding defaults; skipped/no-op runs cannot satisfy this gate.
- Experimental completeness: reference geometry and 12 named one-factor controls
  are pinned before execution. The canonical matrix is
  3 geometries × 4 soils × 2 surfaces × 3 traffic states × 7 arrangements = 504;
  with controls, require 516 distinct declared profile cases.

## Scientific and implementation assessment

Annual detachment, native signed deposition, profile export and water volumes
follow the existing segment-summary contract: all execution years and zero-event
days, native PASS measures, and stationary full-profile WAT area. Mixed profiles
cannot be labeled road-prism detachment, buffer-specific delivery or watershed
outlet yield. Required calendar/finite-value checks and rejection of incomplete
matrices prevent selecting only successful or erosive cases.

Read-only source inspection confirmed 34 completed distinct site segments. The
selected shortest/lower-median/longest lengths are approximately 0.008610547,
2.620462868 and 583.190110376 m. The shortest is a segmentation/precision stress
case: slope-file rounding, native area precision and unrutted geometry clamps
can materially alter effective dimensions. Report those transformations and
avoid interpreting cross-arrangement differences as pure design effects.
Variability describes model, factor and calendar differences, not independent
field replicates or calibration uncertainty.

Use the actual production selector mapping as well as its writers. In
`wepppy/nodb/mods/roads/roads.py:5232`, unrutted replacement resolves its soil
template using `design="outslope_rutted"` before applying OFE order (3,1,2) or
(3,1,2,3). Passing the literal unrutted design to that resolver would seek absent
paved templates. Preserve this existing mapping; do not create replacement
parameter formulas; the final canonical contract now states this mapping.
Traffic and rock-fragment controls need prepared soil and
management readback because their effects differ among OFEs.

The fixture/provenance requirements are adequate: finite committed scientific
inputs, actual climate duration, binary/native/builder/analyzer identities,
generated input/output hashes and repository-only report freshness checks.
The source-selected binary and actual climate years must be recorded explicitly;
an implicit model upgrade or reliance on the legacy 100-year header is invalid.
Four isolated actual controller runs remain required acceptance evidence even
when the optional local-project test skips on ordinary developer machines.

## Evidence limits

Feasibility and anomaly assessment remain execution gates, especially tiny areas,
clipped grade controls and unrutted replacement eligibility. A failing case must
retain diagnostics and prevent current-report publication; this checkpoint does
not authorize quietly changing the matrix or production model to make it pass.
Independent implementation review must reconcile summary values with generated
PASS/WAT, verify all case identities, and inspect the four project receipts.
Usersum containment, access and rendered publication are covered by the separate
publication/security review. No original-project mutation is authorized.
