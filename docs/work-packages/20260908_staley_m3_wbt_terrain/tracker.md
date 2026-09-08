# Tracker — Staley M3 WBT Terrain

## Quick Status

**Started / last updated**: 2026-09-08 23:30 UTC
**Phase**: Scaffold ready; awaiting fresh-agent execution
**Next milestone**: Resolve terrain contract and draft ADR
**Security impact**: high for planned CLI/path/binding changes
**Dedicated security review**: required at implementation closeout

## Task Board

- [x] Package, self-contained ExecPlan, and fresh-agent prompt scaffolded.
- [ ] M1: Inspect both repositories, settle contract, draft ADR and study protocol.
- [ ] M2: Implement and register WBT terrain tool with both bindings and fixtures.
- [ ] M3: Run rebuilt-binary and pinned reference comparisons.
- [ ] M4: Select catchments and perform 10 m/30 m sensitivity study.
- [ ] M5: Review, recommend resolution policy, promote docs, and close package.

## Decisions

- **2026-09-08 23:30 UTC** — User selected weppcloud-wbt ownership and a
  subsequent 10 m/30 m assessment. Runtime implementation is assigned to a
  fresh agent, not this scaffolding session.
- **2026-09-08 23:30 UTC** — Keep reference parity and terrain-resolution
  sensitivity separate; neither alone proves predictive validity.

## Risks and Open Questions

Relief semantics differ across paper prose and reference documentation.
The inspected reference uses weighted maximum paths and needs pinned-version
testing. Raw versus conditioned elevation may change the maximum/outlet
relationship. Suitable real catchments and complete source DEMs still need
selection. M3 soil thickness remains unresolved; the terrain study must label
fixed diagnostic soil/burn inputs rather than imply production readiness.

## Validation and Evidence

Scaffold validation (2026-09-08 23:30 UTC): documentation lint passed for all
five package files, eight module documents, and PROJECT_TRACKER.md with zero
errors/warnings. Local links and spelling previews passed for all five package
files and the two amended module documents.
No tool implementation, numeric parity, raster study, or review has run.
Future evidence belongs in [artifacts](artifacts/README.md); keep large rasters
in an isolated workspace and retain acquisition recipes and hashes.

## Handoff

Start with [start_here.md](prompts/active/start_here.md). Execute the named
ExecPlan only; unrelated active WEPPpy initiatives are outside scope. Update
this tracker and the ExecPlan after each milestone, and PROJECT_TRACKER.md when
execution begins. No known external blocker prevents initial discovery.
