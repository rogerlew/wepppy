# Production M3 integration tracker

Status: milestone 1 contract approved; standalone ancestor commit next, implementation pending.
Last updated: 2026-09-14.

## Task board

- [x] Record accepted common support and soil-builder isolation.
- [x] Review retained paper, current soil code and NRCS documentation.
- [x] Audit frozen three-site component totals and repeated depth intervals.
- [x] Scaffold canonical amendment, decision register, regression plan and ExecPlan.
- [x] Inventory actual project sources and installed original THICK delivery.
- [ ] Resolve dominant H material/lineage and bounded source-acquisition proposal.
- [x] Establish NRCS support for H, quantify replacement depth policies and
  retain sixteen analytical checks and independent preliminary review findings.
- [ ] Ratify S05–S09, complete independent contract reviews and checkpoint commit.
- [x] Ratify recorded-depth replacement and exact prepared-source/runtime schemas;
  both independent final contract reviews approved with findings closed.
- [ ] Implement isolated production soil derivation and prove builder parity.
- [ ] Compose M3 terrain and M1/M3 common support with exact masks.
- [ ] Complete workers, publication, freshness and coverage summaries.
- [ ] Validate real development jobs/browser/archive, full suites and reviews.
- [ ] Synchronize durable docs and archive the completed plan.

## Decisions

- **2026-09-14 16:40 UTC** — Owner accepted the analysis-support explanation:
  common valid cells per model; M3 ruggedness retains full-basin geometry.
- **2026-09-14 16:40 UTC** — Owner requires particular soil-building regression
  protection. Scope is a downstream reader; shared soil-building changes excluded.
- **2026-09-14 16:40 UTC** — NRCS documents exceptions to strict offline rejection.
  Retain offline semantics; ratify production policy with explicit fixture evidence.

## Risks and remaining decisions

S05–S09 in the [checkpoint](artifacts/20260914_contract_decision.md) remain open.
Principal risks: double-counted paired horizons, misclassified component weights,
donor keys mistaken for spatial soil identity, component percentages presented as
mapped coverage, incomplete SQLite snapshots, hidden fallback or upstream writes.
Source delivery is not yet inventoried; built WEPP soils alone do not prove M3
inputs exist. The actual audit found legacy H horizons on 99.798% of basin
cells and no prepared THICK input for this basin. Strict material rules were
subsequently rejected. Documented H eligibility restores all basin thickness
cells; Cr/endpoint/pair treatment remains proposed. Resolve the concrete
[source-delivery proposal](artifacts/source_delivery_proposal.md) before
acquisition and scientific checkpoint ratification.

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
