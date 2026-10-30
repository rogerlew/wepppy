# Evaluate physical drainage assumptions across the Roads matrix

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture


Determine whether the promising buffer-drainage sensitivity is physically defensible
and generalizes beyond four selected cases. Deliver a reproducible report separating
compatibility with FSWEPP WEPP2010 from physical validation. This is scientific
surrogate discovery, not a wired production fix. No default changes are authorized.

## Progress


- [x] Source metadata and prior study reviewed; additional specimens selected before results.
- [x] (2026-10-30 UTC) Freeze inputs, source identities and physical rationale; retained two pre-execution staging failures.
- [x] (2026-10-30 UTC) Execute 1,920 native runs successfully; final reference/accounting audit running.
- [x] (2026-10-30 UTC) Execute and audit 192 additional runtime-mode bridge cases, declared before their outcomes.
- [x] (2026-10-30 UTC) Analyze all strata, hydrology, accounting and control reproduction; 600/600 controls exact.
- [x] (2026-10-30 UTC) Complete report, physical note and closeout; regression coverage 12,186 passed, 298 skipped.

## Surprises & Discoveries


The initially considered unrestricted specimen 2711250 was already the old silt
specimen. Candidate 2711254 has the same horizon properties. Both were rejected
before execution; use distinct unrestricted profile 1718494. Prior `holdout` is
already used evidence, not a new independent validation specimen.

## Decision Log


2026-10-30 UTC, Codex: freeze eight soils × five climates × four designs × two
surfaces × three traffic levels, current/source-buffer only. This tests generalization
without changing road erosion or the normalized horizon boundary. The conservative
policy is a selection of these runs, not an additional simulation or fitted model.
Identified bedrock retains current treatment in that policy; its source-buffer result
is diagnostic because soil and bedrock conductivity are not interchangeable.

## Outcomes & Retrospective


Staging also established that old `loam` and `holdout` have identical horizon and
restriction properties. Retain both historic labels for control reproduction but
report seven unique material profiles, not eight independent soils. New specimens
are distinct. Header-only timestamp drift is not material drift. Both staging
failures occurred before any new native outcomes. An explicit `freeze` command
revalidates completed staging after these checks; it refuses executed roots.

Completed 2,112 native runs and direct artifact audits. Broad positive-reference
coverage is 820/905 current, 824/905 source, 814/905 conservative policy; source fixes
17 but regresses 13 cases. UI-mode bridge coverage is 61/71 for each treatment; site
shared settings give 14/16 each. No candidate accepted. Six no-traffic new-lithic
legacy-mode cases emit negative sediment fluxes, retained as invalid budgets.
All 600 prior controls reproduce exactly. Physical calibration data remain absent.

The next study must use actual Roads runtime settings and reproduce the negative
flux under UI mode. Preserving exact runtime sidecars is part of the scientific
input contract. This package does not repair a production defect or authorize a
conductivity default. Retained artifacts and reproduction commands are in the report.

## Context and Orientation


The prior buffer study found that increasing buffer `kslast` (conductivity of the
material below the modeled soil) reduced excessive runoff and sediment in two site
cases. Existing preparation uses bare road/fill and forest buffer, with 200 mm
property-preserving subdivision. This still aliases paved/gravel and high/low traffic
in some modern inputs. `docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/experiment.py`
provides frozen preparation and runner helpers; `20261029_roads_ofe_budget/artifacts/accounting.py`
provides unequal-area water and sediment accounting. Raw data remain under `/wc1/runs/ro/`.

## Plan of Work


First retain primary USDA/NRCS physical evidence and audit exact native source commit
`b73e93b19a724d1991d341d38a18d11e742231bd`. Create `artifacts/study.py` with staging,
execution and analysis commands. Reuse five prior specimens and add generated soils
`/wc1/runs/ad/addicted-reservist/soils/{1856573,53949,1718494}.sol`.
Verify semantic profiles differ before claiming new specimens. Use Birmingham,
Denver, Flagstaff, Charleston and site climates, each 16 complete years. Use inbare,
inveg, outrut and outunrut designs; gravel/paved; high/low/none traffic.

Second run unchanged and buffer-only conductivity treatments. Source values are
1.512 mm/h for sand, 3.276 for clay and new_lowk, 0.126 for new_lithic; for loam,
silt, holdout and new_open use their deepest emitted horizon conductivity. Preserve
all other consumed properties. The mineral classification is supported by horizon
names in the generated source, not merely `type: N/A`. The no-restriction scenario
assumes soil-like continuation and remains conditional. Freeze declaration before
outcomes. Use existing rehashed WEPP2010 and modern legacy-soil references matched
by texture, geometry, management and climate; do not count reused references as fresh runs.

Third parse common report exports and runoff, complete water calendars and sparse
sediment event budgets. Report every zero-reference case separately, all positive
ratios, factor-ten successes/failures and transitions by soil, climate, design,
surface, traffic and previously unused specimens. Inspect deep percolation, surface
and lateral export, saturation and actual profile depth using owned Rust readers.
Keep accounting discrepancies explicit; never enlarge tolerances to make them pass.
No inference of particle origin or full water closure from partial budgets.

## Concrete Steps


From `/workdir/wepppy`, run staging and execution with the existing container:

    wctl exec weppcloud python docs/work-packages/20261029_roads_drainage_validation/artifacts/study.py stage
    wctl exec weppcloud python docs/work-packages/20261029_roads_drainage_validation/artifacts/study.py run
    wctl exec weppcloud python docs/work-packages/20261029_roads_drainage_validation/artifacts/analyze.py

Scratch root is `/wc1/runs/ro/roads-drainage-validation-20261029-v2`.
Staging must refuse existing destinations; execution creates per-case records with
hashes and fails explicitly on missing inputs or unsuccessful native artifacts.
Retain portable declaration, case results, summaries, physical justification and
validation evidence in this package; raw native outputs remain in scratch.

## Validation and Acceptance


Require all 1,920 expected unique cases, successful native termination, finite metrics,
16-year full daily water calendars, buffer-only material invariants and 200 mm
boundaries in actual consumed inputs. Rehash binary and reference artifacts, compare
600 current controls to prior roles outputs, retain input aliases and quantify native
sediment-accounting mismatches. A positive-reference export passes compatibility only
at 0.1–10 times WEPP2010. A broad candidate must meet this for every positive case;
zero references are reported separately, without an epsilon denominator. Aggregate
improvement alone cannot satisfy physical acceptance. Field/geology uncertainty
precludes asserting calibrated physical validity, even if all ratios pass.

Run `wctl run-pytest tests/tools/test_roads_drainage_validation.py` and a full repository
sweep (disjoint process partitions may isolate native/stub tests). Run documentation
lint on this package and changed discovery files, and `git diff --check`. Record
primary-agent self-review without implying an independent reviewer.

## Idempotence and Recovery


Never overwrite earlier studies or source projects. Keep partial failed runs and
logs; diagnose before retrying into a fresh batch. Resume may reuse only completed
records whose expected input and output hashes revalidate. Stage and run source
identities must match. No rollback of production is needed because it is unchanged.

## Artifacts and Notes


This package contains scientific hypotheses, not production policy. Its physical
note must separate primary literature, exact-source behavior, soil metadata and
inferences. The report names untested geometry, subsurface geology, road surface
conditioning, and lack of field observations as limits.

## Interfaces and Dependencies


Use `WeppSoilUtil`, owned `prep_soil`, `make_hillslope_run`, exact `wepp_261026` with
SHA256 `a6351d371030f702be5eb0d727d8e7181eeb9d60e9ddf6ce05d9616e5d759d48`, and
Rust-backed WEPP interchange. Use prior common-report parser and audited sediment
and water accounting. No native rebuild or new third-party dependency.

Revision: initial design frozen before new outcomes; 2026-10-30 UTC.

## Runtime-mode discovery and additional milestone


2026-10-30 01:59 UTC: exact `main.for:163–171` selects `ui_run` by existence of
`wepp_ui.txt`. All preceding simplified study runs omit this file. Actual Roads
`_prepare_roads_runs_workspace` copies shared files from the baseline; both source
projects and the canonical Roads fixture contain it. Therefore the simplified
matrix uses the unweighted conductivity harmonic mean and cannot establish runtime
parity with those projects. The thickness-weighted equation applies to UI mode.

Keep the frozen 1,920-run legacy-mode matrix. Add a separately declared runtime bridge
before inspecting any UI-mode results: eight specimens × five climates × rutted and
unrutted designs × gravel/high × two drainage treatments = 160 UI-only runs. Add
32 site-climate cases with all seven existing Roads fixture shared files copied
unchanged. This isolates the switch and tests the site's shared bundle without
transplanting site-specific evaporation/snow settings to other climates. Total new
native runs in this package: 2,112. No additional parameter tuning or production edit.

Run `artifacts/runtime_bridge.py stage` then `run` through `wctl exec weppcloud`.
The bridge scratch root is the main v2 root's `runtime-bridge-v1/`. Its declaration
freezes all cases, shared-file hashes and source code. Verify the UI activation
banner, all actual files, calendars, report metrics and audited budgets. Compare
bridge inputs to matching original matrix cases; only declared runtime files may
differ. Analyze every matched current/source pair, retaining accounting failures.
Production parity still requires full project orchestration; the bridge diagnoses
runtime sensitivity, and its site bundle uses the existing fixture's settings.

Revision: add bounded runtime-mode bridge because a confirmed native switch changes
the relevant equation. Earlier conductivity/10 m thickness interpretation must be
qualified by mode; no revised hypothesis is fitted to bridge outcomes.

Progress note: all 2,112 native runs completed; final full-matrix accounting audit
handles only the known additive reference audit field and two exact-hash FSWEPP
normalization intermediates. Failed preflights retained; no model outputs changed.

Final discoveries: native UI activation is controlled by a working-directory file,
not the binary filename or soil format alone. Six broader source cases contain
negative ELEMENT fluxes, including −8.436 kg/m at year 7/day 251; a zero annual
report for that year hides this invalid event. Signed diagnostics are retained
without clipping, and physical-budget acceptance remains false. Closed source
studies are immutable; this package records these new applicability limits.

Final revision, 2026-10-30 UTC: report and physical rationale complete, all declared
native work executed, accounting failures retained, no candidate accepted. Native
runtime declarations remain frozen. Analysis phase snapshots and failed preflights
explain metadata compatibility, auxiliary reference files, worker pickling and the
negative-flux discovery without modifying model outputs.
