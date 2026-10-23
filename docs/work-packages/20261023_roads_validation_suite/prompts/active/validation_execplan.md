# Build and publish the site-derived Roads validation suite

## Purpose / Big Picture


A developer can rerun Roads parameter combinations with committed site-derived
scientific inputs, and a user can read a current, provenance-backed report in
Usersum. This plan implements and executes that workflow; a scaffold alone does
not satisfy it. Follow docs/prompt_templates/codex_exec_plans.md.

## Progress


- [x] (2026-10-23 UTC) Inspect baseline suite, production builders and site evidence.
- [x] Obtain independent contract reviews and commit checkpoint `c4774cf2a`.
- [x] Build portable fixtures, 504-case profile matrix and sensitivity controls.
- [x] Run matrix and design validations; retain negative full-unrutted and qualified positive subset.
- [x] Publish report through existing Usersum vendor/nav machinery; live HTTPS links verified.
- [ ] Complete reviews, tests, evidence and closure.

## Surprises & Discoveries

2026-10-23: pilot no-traffic single-OFE runs fail because pruning plant definitions
leaves initial residue reference 2 outside the retained count1. Two-OFE pruning
also changes that reference semantically. A separately reviewed checkpoint
authorizes retaining all plants/references, without changing model defaults.



The site climate header advertises 100 years but scientific rows cover 16 years.
The site's 34 completed profiles include many very short segments. The lower
median length is approximately 2.62 m. Holding one climate common and testing
short/median/long actual segment geometry makes that variation explicit.
Usersum currently registers disturbed results as a local document; this task
explicitly requests a vendored report, so use a scoped self-repository vendor.

2026-10-23: the complete matrix found a stray trailing `k` in the paved sandy-
loam rocked-ditch soil template. Routed two-OFE parsing correctly rejected the
incomplete extra OFE pair. Remove only the non-data token; preserve every soil
parameter. This restores template grammar without a new behavior contract.

Initial full-site checks exposed two harness setup issues: unrutted requires
explicit fill/buffer feature attributes (30 m at 10% experiment controls); and
Roads deserialization initializes its log before NoDb relocates wd. The first
copies appended to the original roads log, while source scientific artifacts and
NoDb files remained unchanged. Rebase copied serialized absolute paths before
loading any controller; retain before/after source hashes including that log in
fresh final validations. Do not erase the initial diagnostic evidence.

## Decision Log


2026-10-23 UTC / Roger requested site-based parameter validation, generated report,
and Usersum vendoring/linking. Codex selects profile tests plus separate full-site
checks to keep portable numerical comparisons distinct from routing/accounting
verification. No production default/formula change is authorized or necessary.

## Outcomes & Retrospective


Implementation and focused validation complete; final source-bound matrix,
publication and broad gates remain. Record actual matrix coverage, anomalies, report identity,
publication evidence and limitations here before closure.

## Context and Orientation


Production builders are methods of Roads in wepppy/nodb/mods/roads/roads.py.
They build single, routed and replacement MOFE management/soil/slope inputs.
wepp_runner executes the existing hillslope binary; native interchange supplies
PASS/WAT values. The segment-loss-summary contract governs annualization and
profile area. tests/disturbed supplies the report/freshness pattern. Usersum
vendors.yaml, docs_manifest.yaml and nav_tree.yaml control published documents.
The canonical new suite contract is docs/schemas/roads-validation-suite-contract.md.

Use /wc1/runs/cl/clogging-starch only as a read-only source. Existing isolated
validation copies under /wc1/runs/ro are historical evidence; create fresh scratch
roots for project executions. Do not vendor serialized account/controller state.

## Plan of Work


Milestone 1 commits the canonical suite/publication contract and independent
reviews before implementing publication changes. Capture precise matrix, state,
compatibility and artifact acceptance in the checkpoint.

Milestone 2 also repairs the pilot-discovered management reference defect after
its independent canonical contract checkpoint, tests both legacy templates, and
reruns fresh cases. Historical outputs remain unchanged.

Milestone 2 creates tests/roads scientific fixtures with source hashes, a common
finite climate, deterministic short/median/long selection, a named case matrix,
and production-builder preparation. Verify actual prepared parameters and fresh
native outputs. Add invalid/empty/incomplete-source tests and a repository-only
publication freshness check. Use existing dependencies only.

Milestone 3 executes all canonical cases and bounded geometry/material controls.
Run all four designs through actual controller preparation and execution on isolated
site copies. Parse profile outputs with native readers, generate machine-readable
summaries, inspect outliers and render a concise contextual report. Retain inputs,
outputs and provenance. Fail partial matrices instead of dropping failed rows.

Milestone 4 vendors the report with the existing Usersum sync code, registers the
user-readable document and navigation link, links the Roads guide and verifies
actual rendered content. Freeze implementation before full regression to avoid
mixed-source module reloads. Final independent reviews inspect numerical scope,
provenance and publication. Update tracker/PROJECT_TRACKER, commit scoped changes
and move this plan to completed when all acceptance evidence exists.

## Concrete Steps


Work in /workdir/wepppy on the existing branch. Run focused tests through
wctl run-pytest tests/roads. Use an unused explicit basetemp for retained matrix
artifacts. Run the analyzer against that output root; write the canonical report
and provenance together. Use Usersum tooling for scoped vendor sync/index and
contract validation; do not overwrite unrelated vendor documents. Run relevant
Usersum tests and wctl doc-lint. After source freeze run wctl run-pytest tests
--maxfail=1, with installed browser assets configured if needed. Record exact
commands and results in artifacts. Commit only task files.

## Validation and Acceptance


504 complete canonical combinations and the declared sensitivity controls must
produce fresh readable outputs with exact case identities and complete calendars.
Prepared files must contain the requested factors; report formulas must match
native source aggregates and actual modeled area. Four full-project design runs
must validate current publication, profile summaries and accounting without
changing baseline/source artifacts. Published Usersum content must match the
canonical report and be reachable through its intended link. No field-accuracy,
production-deployment or original-project-repair claim is made.

## Idempotence and Recovery


Scratch outputs use new roots; existing diagnostic runs are not overwritten.
Fixture extraction is explicit and hash-checked. A partial run retains evidence
but cannot replace the current report. Report refresh includes relevant source
hashes and review; hash replacement alone cannot certify stale results.

## Artifacts and Notes


Retain compact matrix/source identities, prepared/output readback, scientific
assessment, project-run receipts, publication checks and reviews under artifacts.
Durable operating instructions live in tests/roads/README.md and the canonical
suite contract, not only this work package.

## Interfaces and Dependencies


Reuse Roads production builders, wepp_runner, owned native PASS/WAT readers,
DuckDB/PyArrow and existing Usersum vendor tooling. No new modeling code,
queue topology, external dependency or identity subsystem is introduced.
