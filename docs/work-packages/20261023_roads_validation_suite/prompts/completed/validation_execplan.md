# Build and publish the site-derived Roads validation suite

Completed 2026-10-23: 516-case four-texture suite executed, independently reviewed,
published in Usersum and validated by the passing full repository regression.

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
- [x] Independent correctness and publication/isolation reviews approve the final implementation.
- [x] Broad regression: 11,647 passed, 131 skipped in 3,270.42 seconds; close package.

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

2026-10-23 UTC / Roger requested all four soil textures. Include clay, loam, sand
and silt throughout the 504 core combinations, with 12 additional controls.

2026-10-23 UTC / Reviewed checkpoint `fa5c40a76` retains full-upload unrutted as
a negative control and adds a separately qualified positive subset. This preserves
the observed production geometry rejection instead of silently dropping failed
profiles or claiming whole-site success. Exactly one source feature is excluded
by recorded identity; the report labels the resulting limited coverage.

## Outcomes & Retrospective


Implementation is committed at `a501c15cc`. The final source-bound matrix passes
all 516 cases covering clay, loam, sand and silt; independent aggregation checks
3,015,504 PASS days and 6,942,672 WAT OFE-days. Publication/Usersum tests pass
68 cases, and live forest HTTPS report/navigation/guide/vendor checks return 200.
The report is vendored byte-for-byte and both independent final reviews approve.
Broad repository regression passes: 11,647 passed, 131 skipped in 3,270.42 seconds
against the frozen implementation. Package closed 2026-10-23.

Full-upload additive designs pass; full-upload unrutted remains a documented
negative control because two generated upstream OFEs have nonpositive lengths.
The reviewed positive unrutted fixture removes exactly one identified upload
feature and validates one replacement plus its remainder. It does not establish
whole-upload unrutted success. Every final project check preserves all 2,383
recorded source files and 911 copied baseline files. Scientific limitations and
reproduction commands are durable in tests/roads/README.md, analysis_context.md
and docs/schemas/roads-validation-suite-contract.md.

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
native source aggregates and actual modeled area. Three additive full-upload design runs and the explicitly limited positive
unrutted subset must validate current publication, profile summaries and accounting
without changing baseline/source artifacts. Full-upload unrutted must retain its
two expected rejected upstream OFEs and publish no current receipt. Published Usersum content must match the
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

Revision note (2026-10-23): record final execution, publication and independent
reviews; record the passing frozen broad regression and close the package.
