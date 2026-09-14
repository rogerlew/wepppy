# Production M3 integration tracker

Status: scaffolded; research complete, checkpoint preparation next.
Last updated: 2026-09-14 16:40 UTC.

## Task board

- [x] Record accepted common support and soil-builder isolation.
- [x] Review retained paper, current soil code and NRCS documentation.
- [x] Audit frozen three-site component totals and repeated depth intervals.
- [x] Scaffold canonical amendment, decision register, regression plan and ExecPlan.
- [ ] Inventory actual project sources and installed original THICK delivery.
- [ ] Ratify S05–S09, complete independent contract reviews and checkpoint commit.
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
inputs exist. No blocker prevents the next bounded audit.

## Notes – 2026-09-14 16:40 UTC

Scaffold only; no runtime code, live project data or shared soil files changed.
No Python/npm suites warranted for this docs-only increment. Documentation
validation passed: package (6 files), module (19 files), ADR, UI contract and
project tracker; zero errors/warnings. Root AGENTS size is 160 lines and
`git diff --check` passed. Unrelated quality reports remain
untouched. Next agent starts milestone 1 of [ExecPlan](prompts/active/execplan.md),
not M3 code edits. Closed predecessor packages remain immutable.
