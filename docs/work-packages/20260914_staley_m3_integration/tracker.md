# Production M3 integration tracker

Status: checkpoint `89d673c38` and isolated implementation `587c6b8de` committed;
generic preparation contract `7328a0004`, replay refinement `0792c7e59` and
reviewed local preparation/M3 increment `4b4e77733` committed. Production
integration and live acceptance remain open.
Last updated: 2026-09-14.

## Task board

- [x] Owner explicitly authorizes bounded source acquisition on 2026-09-14;
  see [authorization](artifacts/20260914_acquisition_authorization.md).
- [x] Prove network-reader controls; acquire live SDA lineage and bounded THICK
  responses. Retain failed NaN metadata receipt without activating inputs.
- [ ] Finish reviewed offline recovery, authoritative activation and live use.
- [x] Shared M1/M3 result dispatch and mask replay: independent reviews close
  legacy-model and lineage reconstruction findings; 81 focused tests pass.
- [ ] Validate production M3/M1-v2 wiring, freshness, publication and UI.
- [x] Record accepted common support and soil-builder isolation.
- [x] Review retained paper, current soil code and NRCS documentation.
- [x] Audit frozen three-site component totals and repeated depth intervals.
- [x] Scaffold canonical amendment, decision register, regression plan and ExecPlan.
- [x] Inventory actual project sources and installed original THICK delivery.
- [x] Resolve H material and prepared-local delivery; acquisition remains unapproved.
- [x] Establish NRCS support for H, quantify replacement depth policies and
  retain sixteen analytical checks and independent preliminary review findings.
- [x] Ratify S05–S09, complete independent contract reviews and checkpoint commit.
- [x] Ratify recorded-depth replacement and exact prepared-source/runtime schemas;
  both independent final contract reviews approved with findings closed.
- [ ] Implement isolated production soil derivation and prove builder parity.
- [ ] Compose M3 terrain and M1/M3 common support with exact masks.
- [ ] Complete workers, publication, freshness and coverage summaries.
- [ ] Validate real development jobs/browser/archive, full suites and reviews.
- [ ] Synchronize durable docs and archive the completed plan.

## Decisions

- **2026-09-14 — Acquisition authorized:** owner approved the recorded bounded
  source-delivery proposal. Earlier unapproved/gated statements describe prior
  checkpoints; no scope/limit expansion or shared soil/cache writes are allowed.
- **2026-09-14 — Basin-independent scope:** owner requires generic preparation
  and execution beyond `addicted-reservist`. Derive keys/extent per project;
  require multi-basin acceptance, not bespoke named-run inputs. Network
  acquisition remains a separate operational gate.
- **2026-09-14 16:40 UTC** — Owner accepted the analysis-support explanation:
  common valid cells per model; M3 ruggedness retains full-basin geometry.
- **2026-09-14 16:40 UTC** — Owner requires particular soil-building regression
  protection. Scope is a downstream reader; shared soil-building changes excluded.
- **2026-09-14 16:40 UTC** — NRCS documents exceptions to strict offline rejection.
  Retain offline semantics; ratify production policy with explicit fixture evidence.

## Risks and remaining decisions

S05–S09 in the [checkpoint](artifacts/20260914_contract_decision.md) are ratified.
Principal risks: double-counted paired horizons, misclassified component weights,
donor keys mistaken for spatial soil identity, component percentages presented as
mapped coverage, incomplete SQLite snapshots, hidden fallback or upstream writes.
Built WEPP soils alone do not prove M3 inputs exist. The actual audit found
legacy H horizons on 99.798% of basin
cells and no prepared THICK input for this basin. Strict material rules were
subsequently rejected. Documented H eligibility restores all basin thickness
cells; Cr/endpoint/pair treatment is accepted. The concrete
[source-delivery proposal](artifacts/source_delivery_proposal.md) requires
separate acquisition authority; prepared-local execution is approved.

## Notes – implementation after checkpoint

Generic local preparation now derives each basin's original keys and native
THICK window, with two distinct basin fixtures. Native terrain checks now prove
exact routed membership, not just equal area. Local primitive and composition
reviews close their findings. Post-fire module gate: 520 passed; latest results
gate: 41 passed; M3 analytical/mixed-source gate: 13 passed. Full sweep: 8,537
passed, 103 skipped (953.04 s); latest additions are covered by focused gates.
Authoritative Ron/Watershed binding, shared M3 results dispatch and
production integration remain unfinished; M1 results explicitly reject M3 inputs.
See [continuation review](artifacts/20260914_generic_implementation_review.md).

Recorded-depth derivation and snapshot extraction initially passed 49 soil tests.
Independent review found clean-WAL sidecar creation, nonfinite JSON handling and
NULL/empty replay defects; corrections retain bounded SQLite copies under visible
attempt directories. Both bounded implementation reviews now close their
medium/high findings. Cellwise primary/fallback composition and dependency
appearance checks are implemented locally. Shared builders remain untouched.
Local opt-in M1 common
support plus the v2 reader passed 79 integration/rainfall tests, including actual
WBT full/partial/disjoint support and a raw-T/common-T difference. Production
wiring, M3 composition, generated soil parity and live acceptance remain pending.
Validation: full Python sweep 8,498 passed/103 skipped; focused updated modules
153 passed, followed by 55 M1 integration passes for final reader-domain checks.
See [validation evidence](artifacts/20260914_implementation_validation.md).

## Notes – 2026-09-14 execution

Read-only [source inventory](artifacts/source_inventory.md) retains grid/key
counts, fixture policy counts, WAL core logical hashes and USGS HEAD evidence.
[ADR-0067](../../adrs/ADR-0067-staley-production-soil-policy.md) records the
proposed material/weighting delta with pending owner provenance. No new runtime
behavior or source acquisition is implemented. Independent preliminary proposal
reviews are separate from the still-pending final checkpoint reviews.
Both [preliminary reviews](artifacts/20260914_preliminary_reviews.md) completed;
the proposal now distinguishes historical provenance, defines zero eligibility
and requires bounded conditional source reads. Checkpoint signoff remains open.

## Notes – depth-policy replacement

Owner rejected strict soil rules and authorized investigation. The
[replacement assessment](artifacts/depth_policy_assessment.md) corrects missing
NRCS H guidance, compares four policies and records the recommended depth-no-R
candidate. H-only and depth-no-R yield full pre-SBS thickness availability and
mean 163.55344468875683 cm in this basin. This is not final Valid coverage or
verified collection lineage. ADR-0067 and the canonical production-M3 proposal
now record the rejection and replacement. No runtime implementation or THICK
acquisition occurred.
Both [replacement preliminary reviews](artifacts/20260914_depth_policy_reviews.md)
closed their research findings after independent rechecks. Package/ADR/canonical
proposal doc lint and `git diff --check` pass. The owner decision on exact
replacement scientific rules is the next checkpoint input.
The owner subsequently approved the replacement by “proceed.” The canonical
runtime contract fixes prepared-source delivery and additive schemas; both
[checkpoint reviews](artifacts/20260914_checkpoint_reviews.md) approve it.
Baseline soil regression: 50 passed, 5 skipped before runtime edits. No source
acquisition or production deployment is authorized.

## Notes – 2026-09-14 16:40 UTC

Scaffold only; no runtime code, live project data or shared soil files changed.
No Python/npm suites warranted for this docs-only increment. Documentation
validation passed: package (6 files), module (19 files), ADR, UI contract and
project tracker; zero errors/warnings. Root AGENTS size is 160 lines and
`git diff --check` passed. Unrelated quality reports remain
untouched. Next agent starts milestone 1 of [ExecPlan](prompts/active/execplan.md),
not M3 code edits. Closed predecessor packages remain immutable.
