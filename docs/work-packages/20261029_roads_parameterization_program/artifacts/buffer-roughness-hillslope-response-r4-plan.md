# Revision-4 whole-hillslope response to buffer roughness persistence

Status: predeclaration for independent scientific and implementation review;
no runs under this declaration have started. The active Roads program ExecPlan
remains authoritative. This is a bounded model sensitivity study, not physical
validation, a production parameter selection, or a release change.

## Why a new declaration is necessary

The [original counterfactual](buffer-roughness-counterfactual-r4-plan.md) remains
failed at its upstream-isolation gate. Its four completed preflight histories
and 32 unexecuted histories are immutable. The subsequent
[four observation-only replays](buffer-roughness-coupling-localization-r4/findings.md)
established an executed native feedback path: the buffer response changes the
equivalent-plane terminal, durations and upstream peaks; these affect persistent
rill widths and the next storm's friction, effective ALPHA and QINF response.
All four replays preserved their corresponding ordinary outputs and full state
traces exactly. That evidence explains why the original isolation expectation
is incompatible with this observed native response. It does not validate the
physical correctness of the shared-duration law or initial roughness value.

This new study asks whether the **whole-hillslope modeled response** to the same
single persistence rule improves the selected annual sediment discrepancies,
while retaining passing and opposite-direction controls. Endogenous upstream
changes are now explicitly measured responses, not failed isolation. There is
no new source rule and no retroactive acceptance of the failed campaign.

## Frozen intervention, inputs and response unit

Use the same [nine pairs and original dates](buffer-process-observation-r4/seeds.json),
all original full 16-year climates, whole legacy soil profiles, and generated
U12 `erosion_road_cap` candidate. The generated lane already contains matched
road erosion coefficients and the road's upper-200-mm conductivity conditioning;
it is not unmodified generated soil. No new values, materials, climates,
management, soil translation, geometry, date selectors or withheld cases enter.

Reuse the exact reviewed diagnostic executable SHA256
`08ad4c67150a01e7487fda677ffd2fe6d3d39e297b820bb875fbb6de13404a14`.
Copy its complete frozen source/object/include/calendar closure and build
receipts into a fresh private root, verify every hash, and do not rebuild it.
The source map and single behavioral rule from the original declaration are
unchanged: capture post-native-initialization buffer RRC once, then restore
only OFE 3 RRC after native SOIL roughness writers and before INFPAR. The
captured value is 0.1 m for this panel; it is not a newly fitted constant.
Keep all existing continuous-three-OFE, cropland, nonirrigation, buffer
no-tillage and unchanged-RRINIT guards. Road tillage stays native.

Natural roughness responses remain enabled: crust/effective conductivity,
critical shear, friction, interrill delivery, depression storage, active
thermal/melt paths, and subsequent routing/state feedback. Ridge height,
density, porosity, widths, residues and all other model states are never
directly overridden. PARAM's zero interrill delivery at the captured 100 mm
roughness remains a possible contributor; this is not a storage-only test.

The response unit is one complete modeled soil-profile history. Original target
days are bounded process illustrations, not independent experimental replicates.
Compare U1 minus O4 within each identical input profile first; compare the
legacy and generated paired responses second. Preserve full-period history and
both discrepancy directions. No tuning follows an intermediate result.

## Fresh execution and exact controls

Run **36 fresh histories** in a new
`buffer-roughness-hillslope-response-r4` private root: nine pairs, two soils,
and two modes. `O4` performs observations without an RRC assignment; `U1`
applies the existing persistence rule. Earlier histories are provenance and
comparison references only; none substitutes for a new accepted run.

First execute B1 legacy/modern in both modes (four runs). Require complete
per-run gates, pair readback and independent actual preflight review before
the remaining 32. Bind the exact runner, seeds, source/build/binary closure,
input/auxiliary files, controls, audit/parser code and loaded dependencies
before execution. Eager PyArrow initialization and a fresh-process cold-to-warm
closure test must exercise canonical audits, SOIL conversion and paired tables.
Retain every failed attempt without overwriting its evidence.

Require these unchanged exact controls:

- All 18 O4 histories reproduce all seven ordinary R4 output files exactly.
- The nine legacy and generated B5/B6/B9 U1 histories are the 12 prespecified
  null controls. Native initial and pre-restore REAL bits must prove every
  buffer restore is an identity. Require ordinary output and bounded consumer
  trace parity, and complete state parity after excluding only mode metadata.
  A violated null prediction stops interpretation; do not relabel it afterward.
- All 18 off/on pairs retain exact observed first-two-layer BD/POR and their
  recorded BDTLL/AO/BDCONS/COCA, day-count, RFCUM and management/configuration
  driver rows for all OFEs. Keep native input density and all other emitted
  core/auxiliary input bytes unchanged. This is the existing observation scope,
  not an unmeasured all-layer density claim.
- Every direct RRC change remains the declared buffer restore. Full-calendar
  state ownership, finite values, exact REAL-bit representation, initial anchor
  and scope guards remain mandatory. The six active generated histories must
  actually exercise a nonidentity restore.

Full-period road/fill WAT, ELEMENT, SOIL and native state comparisons are still
mandatory. Their differences are retained as counts, first occurrences and
maxima with complete raw paired evidence; they no longer require equality in
active U1 histories. Native RH, residue, decay coefficients, persistent width
and upstream RRC may respond through their unchanged equations. Null controls
retain exact equality. An unexplained change to a protected field or a direct
assignment outside the reviewed rule blocks the study; do not erase feedback
by imposing another state override.

## Runtime, accounting and interpretation gates

Every history must complete, retain correct UI/version/shared context and exact
ordinary/observer file inventories, pass canonical physical audits and the
unchanged versioned strict particle audit, and preserve input/source hashes
before and after execution. Coverage still includes the original bounded
owning hydrology, producer/branch, class, route and roughness-consumer traces,
plus the complete daily SOIL state contract. Missing executed branches are not
zeros. A new unexplained audit flag blocks acceptance without renormalization
or threshold changes. Independent final readback is required before pooled
interpretation.

Use the original FSWEPP2/WEPP2010 annual reference and magnitude envelope:
reference above 1 kg/year requires candidate/reference in [0.1, 10]; otherwise
candidate must be at most max(1, 10 times reference) kg/year. Exact-R4 legacy
responses are informative comparators, not replacement acceptance targets.
Report all nine pairs, including worsened, null and undefined outcomes.

The prespecified primary contrasts remain B1/B2/B3; B8 adds overprediction,
B4/B7 passing controls, and B5/B6/B9 underprediction. Call the selected-panel
response an improvement only if at least one originally failing selected
generated case recovers the original envelope, no originally passing selected
generated case regresses, and every declared gate passes. This is insufficient
for parameter promotion or a whole-matrix conclusion. Retain results for legacy
lanes under the same reference without using them to redefine those groups.

Report annual and target-day surface-water and sediment boundaries, signed net
exchange, effective conductivity, roughness/friction, critical shear, interrill
delivery and hourly returns with their actual area/time support. Keep native
pre-restore RRC in U1 distinct from the untreated O4 history. Keep local RDAT
ALPHA distinct from effective equivalent-plane QINF ALPHA if those quantities
are reused from the separate localization evidence. Do not infer tagged
particle origins, gross erosion/deposition or a storage-only cause from net
boundary quantities. Zero-denominator ratios remain undefined.

Stop after this single candidate. A null or worsening result rejects the rule
as a sufficient remedy for those outcomes; it does not authorize another fitted
roughness value. Runtime, provenance, protected-state or accounting failures
remain failures requiring source-based disposition in a separate attempt.
Any changed scientific rule, seed set, reference or gate requires a new
declaration. No production source/default, release, UI or withheld validation
changes are authorized by this research outcome.

Native classification remains `U1`,
`boundary_disposition=requires_scientific_review`. The existing native incident
`20261031_roads_buffer_roughness_counterfactual` retains the original failure,
localization and this separately declared continuation. There is no watchlist
resolution or new native-defect claim.
