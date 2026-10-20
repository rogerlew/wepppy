# Correct MOFE Water Consumer Accounting

## Purpose / Big Picture
An OFE is an overland flow element within a modeled hillslope. Water leaving an
upper OFE can enter another OFE; it is not yet hillslope outlet discharge. Users
must see local precipitation/losses and outlet runoff/lateral flow expressed over
the same hillslope area in reports, maps, exports and Ash/WATAR inputs.

Execution was authorized on 2026-10-20. The prior scaffold-only restriction is
superseded. Physical WAT runoff is ratified at checkpoint `6e689a902`.
M1–M5 are complete; development artifact, performance and regression acceptance
is recorded in the final validation receipt.
The supplied workbook remains evidence, not permission to change WEPP physics,
source schemas, calibration or annualization.
## Progress

- [x] (2026-10-20 20:15 UTC) M0: inspect workbook formulas and complete daily data;
  trace producers, pass routing, direct and indirect consumers.
- [x] (2026-10-20 20:21 UTC) M0: retain workbook/native readback and consumer ledger;
  scaffold package, tracker, and execution plan.
- [x] (2026-10-20 20:21 UTC) M0: scoped docs lint (5 files), relative links,
  spelling previews, receipt assertions and whitespace checks pass.
- [x] M1: ratify source/field semantics, compatibility and canonical amendments;
  obtain two independent contract reviews and commit standalone checkpoint.
- [x] M2: add failing boundary tests; correct native report and daily loader.
- [x] M3: correct dashboard selected/base and Features Export field reductions.
- [x] M4: correct affected Ash/AshPost flow paths and disposition all diagnostic,
  legacy and audit-tool findings.
- [x] M5: paired native release, actual-project artifact validation, performance,
  focused/broad gates, independent correctness review and closeout.
- [x] (2026-10-20) Execution authorized; base revisions and unrelated dirt recorded.
- [x] (2026-10-20) M1 preliminary paired-source readback retained: 328,800 MOFE
  terminal days; 1,096 positive WAT / zero PASS days; no unmatched PASS dates.
- [x] (2026-10-20) Independent preliminary source and compatibility reviews invoked.
- [x] (2026-10-20) Operator selected physical WAT runoff; PASS remains AshPost
  subtraction authority. Canonical amendments and ADR-0099 prepared.
- [x] Independent review disposition and standalone checkpoint `6e689a902`.
## Surprises & Discoveries

The recent ET/Dp correction did not correct routed fields by design. A live
native-writer probe still returns P20/Q12.666667/lateral10 for a daily fixture
whose correct values are 10/8/4.5. Its ET5/Dp7 are already correct.

Both dashboard event branches sum P and Q. The daily loader's all-column area
mean feeds Q to Ash/WATAR. AshPost independently sums all QOFE volumes before
subtracting runoff for ash hills. Fixing only a displayed report would leave
these scientific consumers inconsistent.

QOFE is local-area normalized in the workbook but duplicates cumulative Q in
the current ordinary daily/hourly writers. The workbook's Last_OFE sheet is
missing its final day and its corrected summary uses rounded area factors.
Internal transfers and whole-hill outflows require distinct contracts; complete
water-budget closure also needs storage, not just annual flux arithmetic.
Execution found PASS event filtering makes it a different product from physical
terminal WAT runoff. The threshold uses internal runoff, not printed Q. See
[contract preparation](../../artifacts/20261020_contract_decision.md) and its
paired receipt. AshPost must subtract the PASS contribution present in its
watershed baseline; adopting WAT for hillslope displays does not change this.
Existing Ash result existence checks cannot distinguish old model outputs from
corrected inputs, so a post-only version bump is insufficient.
## Decision Log

2026-10-20: Operator requested corrections and a wider consumer audit, then
explicitly requested scaffolding after the audit. Deliver documentation and
read-only evidence now; implementation remains pending execution.

2026-10-20: Use actual per-row OFE areas and per-native-hill outlet topology.
Never choose a single terminal OFE after merging independent native hills into
one report feature. Do not rescale model sbrunf: pass output already converts
terminal lateral depth to volume.

2026-10-20: Keep the closed ET/Dp package immutable. Future durable rules belong
in current canonical specs and a new ADR, with historical package links only
as provenance. Resolve source semantics before a reviewed checkpoint; do not
commit guessed runoff semantics as a contract.
2026-10-20 execution: The operator requested execution of this package,
superseding scaffold-only authority. Preserve the M1 gate: source-product
selection is now an explicit pending operator question because paired output
shows physical WAT runoff and routed PASS runoff differ. Do not silently adopt
PASS as a universal replacement or reconstruct its threshold from WAT Q.
## Outcomes & Retrospective
Physical WAT runoff now propagates through native reports, daily loaders,
selected/base dashboard queries, feature exports and Ash models. AshPost
subtracts the corresponding PASS contribution, with separate model/post lineage.
Both independent final reviewers closed all high/medium findings. Native and
focused Python gates, actual replay Parquet/export/Ash readbacks and live
HTML/CSV/query/download checks pass. Complete cold-report timing meets the
single-OFE budget; the documented MOFE cold regression preserves fast cache hits.
The resumed broad gate passed 10,703 tests (126 skipped), supplementing the
previously passed disturbed matrices and final 33-test provenance run. Package
execution is complete; production deployment was not performed.
The six-year replay SIGFPE and missing contour runtime certification remain
explicit scientific evidence limits, not consumer fallback permissions.
## Context and Orientation

WEPPpy root is `/workdir/wepppy`; native Rust is `/workdir/wepppyo3`; model
source is `/workdir/wepp-forest`. Preserve existing branches and unrelated dirt.
Read root and nearest AGENTS instructions before editing each subsystem.

`wepppy/wepp/reports/hillslope_watbal.py` calls
`wepp_interchange/src/hillslope_watbal.rs` on H.wat.parquet and caches a compact
per-hill/year table. `avg_annual_watbal` exposes HTML/CSV. The separate yearly
water report reads TotalWatSed named measures. TotalWatSed named Runoff uses
H.pass runvol; its named lateral depth uses terminal WAT volume divided by area.
Raw diagnostic Q/QOFE columns are not equivalent to named Runoff.

`wepppy/wepp/interchange/hill_wat_interchange.py` provides raw rows or daily
collapsed frames. `nodb/mods/ash_transport/ash.py` and `watar_bp.py` supply those
frames to ash models. `wepp_interchange/src/ashpost.rs` later corrects watershed
streamflow using runoff from selected ash hills. The field dependency crosses
both producer and post-processing boundaries.

`static/js/gl-dashboard/data/wepp-data.js` builds selected/base event queries.
`nodb/mods/features_export/temporal_wide_materializer.py` has independent local
ET/Dp reduction and generic terminal handling. Retain exact source bindings from
`duckdb_materializer.py`, hidden dependencies from `carrier_layer_materializer.py`,
and the service's correct geometry identity alignment.

See `notes/consumer-audit.md` for the complete audited touch-point ledger.

## Plan of Work

### M1: source semantics and canonical checkpoint

Recheck repository revisions and search scope. Establish a field matrix for
P/RM/Irr, ET components/Dp, surface outlet Q, lateral outlet, raw QOFE,
UpStrmQ/SubRIn, Tile, stock/geometry columns and optional aliases. Identify each
field's spatial support, units, temporal reducer and exposed consumers. Keep
internal-transfer diagnostics distinguishable from exported fluxes.

Verify runoff against paired WAT/PASS output from supported daily/hourly model
versions, constant/variable widths and contour layouts. Reuse existing model
artifacts or isolated replay controls without changing model physics. Decide
whether each consumer should use H.pass runvol or a provenance-supported WAT
outlet expression. New dependencies require explicit absent/legacy behavior and
cache proofs; do not silently guess QOFE semantics. This source decision is an
M1 completion gate, not deferred implementation discretion.

Create `artifacts/<date>_contract_decision.md` naming base revisions and WCA IDs.
Amend `docs/schemas/hillslope-water-aggregation-contract.md`,
`output-scope-contract.md`, `report-cache-freshness-contract.md`, Features Export
`specification.md`, and affected Ash specs. The existing routed-preservation
clauses conflict with intended changes and must be explicitly replaced. Add an
ADR with operator approval from this conversation, meeting provenance attributed
to Ayush Poudel and Roger Lew without inventing meeting dates, and exact formula
changes. Re-triage security if new file/source boundaries are added. Obtain two
independent read-only reviews, resolve findings, and commit the checkpoint as a
standalone ancestor before production implementation.

Define per-field behavior for missing versus null values and nonfinite area.
Retain local-flux rules where applicable, but do not fabricate outlet zero when
the known terminal OFE is absent. Specify sparse observations, source identity,
duplicate rows and multiple native hills mapping to a target feature. Preserve
raw-mode column meanings; any public diagnostic reinterpretation needs reviewed
compatibility/version evidence.

### M2: native and daily consumers

Add independent failing tests at the real native writer and DuckDB loader.
Correct `hillslope_watbal.rs` field reducers and Python freshness/native marker
checks. Keep bounded memory and single-OFE performance. Select each native
hillslope outlet before combining mapped volumes and areas.

Correct the loader's daily projection using the agreed field matrix; do not
replace raw parsing or introduce a generic Python hydrology engine. Prove the
actual Ash/WATAR Q input is corrected and local Es/ET/Dp are unchanged. If the
source decision adds pass access, validate real missing/empty/legacy paths and
unit conversions rather than mocking that boundary.

### M3: maps and feature exports

Update both event P/Q SQL branches and the shared unavailable/difference
presentation behavior. Execute generated SQL in DuckDB with distinguishable
selected/base fixtures, then inspect actual browser values.

Extend source-aware daily materialization in Features Export for the agreed
fields before temporal reduction. Do not sum storage snapshots by accident or
silently treat all fields as fluxes. Preserve no-observation geometry, requested
empty dates, column selection, aliases, joined-source identities, year selection
and supported long/wide layouts. Version exports to invalidate old numerics.

### M4: downstream reconciliation

Fix AshPost's selected-hill runoff subtraction using verified outlet volumes.
Validate the whole Ash input, model output and correction chain with nonzero
ash and nonash hills. Assess both Ash and AshPost persisted artifact versions;
a changed loader alone does not invalidate already generated model results.

Disposition WCA-06 raw TotalWatSed Q/QOFE meanings and reader exposure. Preserve
correct named hydrology. Handle WCA-07 supported legacy R explicitly: reviewed
repair, visible unsupported-case error, or separately authorized retirement;
never silently preserve a wrong result while claiming all findings closed.
Update WCA-08 audit tool provenance checks while retaining intentional internal
transfer sums. Re-run the consumer search and record every remaining limitation.

### M5: artifacts, release and closeout

Build/test the native library, update release provenance and paired Python pin
and image source reference. Only publish/push/deploy if authorized at execution;
commit authority does not by itself authorize production rollout.

Use an isolated actual MOFE run with paired WAT/PASS and differing OFE areas.
Read fresh report Parquet/HTML/CSV, actual selected/base queries, exported ZIP
members/GeoParquet identities, and affected Ash outputs. Reconcile with an
independent daily volume oracle and pass volumes; log exact sources, hashes,
requests, year divisors and library revision. Test cold/warm/stale/historical
cache and failed publication, ordinary browse/download and existing archive
restoration. Meet existing native/report performance budgets on representative
single-OFE and MOFE sources. Obtain independent correctness review; close all
medium/high findings and update package, tracker, board and completed plan.

## Concrete Steps

Readback from `/workdir/wepppy` (requires existing virtualenv openpyxl/PyArrow):

    .venv/bin/python docs/work-packages/20261020_mofe_water_consumer_accounting/artifacts/audit_readback.py --workbook /tmp/Water_Balance_S_Shape_0.6_0.4_Corrected.xlsx --native /workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/wepp_interchange_rust.so --output /tmp/mofe-water-audit-repeat.json

The pre-fix installed writer produces the retained incorrect P/Q/lateral values;
ET/Dp remain 5/7. Preserve the original receipt when comparing a corrected build.

Future focused gates use `wctl run-pytest` on report, loader, Features Export,
Ash/WATAR, cache and generated-SQL modules; discover exact affected test names
with `rg --files tests` before invocation. Native tests use the explicit built
library via `WEPP_INTERCHANGE_TEST_BINARY`, plus
`PYO3_PYTHON=/usr/bin/python3.12 cargo test -p wepp_interchange_rust` in wepppyo3.
Use `wctl run-npm test`, `wctl run-npm lint`, then
`wctl run-pytest tests --maxfail=1` for substantive execution closeout. The dev
container previously had a wrong PLAYWRIGHT_BROWSERS_PATH; if it recurs, record
and correct it only for the affected test process, not by masking the failure.

Scaffold gates:

    wctl doc-lint --path docs/work-packages/20261020_mofe_water_consumer_accounting
    wctl doc-lint --path PROJECT_TRACKER.md
    git diff --check

## Validation and Acceptance

Input matrix: single/two/three OFEs; unequal and variable-width areas; multiple
native hills mapped to one feature; distinct daily dates and years; last OFE
missing; joined source collisions; selected fields hiding Area; source-version
QOFE variants; invalid areas and fluxes; all temporal modes and scopes.

Runtime state matrix: absent optional source; absent required source; empty
source; populated source; supported legacy source/cache; unknown normalization;
malformed or inaccessible source; pending/failed/completed generation; archived
and restored artifacts. For each field, document whether absence yields empty,
unavailable, historical-unverified access or explicit error. No silent fallback
may produce a scientifically unsupported numeric result.

The two-OFE daily fixture must yield P10, outlet Q8, lateral4.5, ET5, Dp7 mm.
Subdivide equal-state local areas without changing totals; construct independent
serial transfer tests rather than assuming routed depth subdivision invariance.
Validate unequal hillslope areas at the subsequent watershed aggregation stage.
Workbook comparison uses all 31 calendar years; app temporal behavior remains
unchanged and must be reconciled explicitly. Small residuals do not certify
closure without initial/final soil, snow and interception storage.

## Idempotence and Recovery

Scaffold/readback is repeatable and changes no project outputs. Temporary native
fixtures use a dedicated temporary directory. Preserve the original workbook and
pre-fix receipt. Future generated-output checks use isolated project copies.
Keep atomic publication and historical provenance; update only semantically
stale caches via existing mechanisms. Recovery pairs native/Python revisions
and output versions, without relabeling stale results as corrected.

## Artifacts and Notes

Retain audited source revisions, workbook digest/formulas/counts, native probe,
contract decision/reviews, regression and real-project receipts, scientific
field matrix, performance evidence and final correctness review. Do not rely on
transient console output or closed work packages as current normative authority.

## Interfaces and Dependencies

Preserve existing report/daily-loader APIs and raw interchange schemas unless
a reviewed dependency amendment requires an additive extension. Reuse owned
Rust, DuckDB, Arrow and existing browser/export facilities. No new runtime
service, dependency or framework is permitted by this plan.

Revision: 2026-10-20 execution started. M1 paired readback and preliminary
independent reviews reveal a source-product decision; operator choice is pending
before canonical amendments, ratification and checkpoint. M2-M5 remain pending.

2026-10-20 revision: physical WAT source choice approved; review findings refine
selected-field validation, source freshness, no-data states and legacy admission.

2026-10-20 implementation progress: M1 ratified in `6e689a902` (upstream schema
exception `04f1c4d26`). M2–M4 implementation is undergoing independent review;
M5 remains active. Targeted consumer/Ash/SQL suites and 987 frontend tests passed.
Review fixes address duplicate native days, uncertifiable PASS totals, historical
refresh admission and complete Ash mapping/source identity. Six-year isolated
H5 replay encountered evap.for SIGFPE in 2025; bounded five-year daily and hourly
replays completed, pending serialized consumer readback. This is a fixture/model
limitation, not evidence of consumer acceptance or authorization to alter physics.

2026-10-20 late validation: pre-read WAT fingerprints are reused only inside an
explicit Ash batch. The broad gate exposed same-tick metadata ambiguity; focused
collision/recovery tests and independent review close the resulting provenance
finding. Final native release is 54d0867, paired hash 60b8da3c77aa8465e262b8978ac173ba681d14745de7aec74392db9308c5c5eb.
Final performance, browser, export, actual Ash facade and review receipts live in
artifacts/20261020_validation.md and its sibling JSON receipts. The broad suite
resumes after retaining passed expensive disturbed matrices; see that receipt for
exact coverage and environment correction.

Final revision: M5 complete. Final independent reviews close every high/medium
finding; stubtest and docs gates pass. Full broad-gate history and combined
coverage are retained in artifacts/20261020_validation.md. The plan is archived
with original projects untouched and explicit scientific evidence limitations.
