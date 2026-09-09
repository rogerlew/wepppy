# Postfire Debris Flow

- Current domain specification: [specification.md](specification.md).
- Track delivery and loose ends in [implementation_roadmap.md](implementation_roadmap.md).
  Update the roadmap, specification, and affected detailed contracts together
  as implementation progresses; roadmap proposals are not accepted contracts.
- Status: offline soil, dNBR and scalar Staley numerical helpers exist; production NoDb/UI/RQ
  integration remains pending.
- Preserve accepted decisions and explicitly label proposals and unresolved inputs.
- Follow `../../AGENTS.md` and the repository contract-first standard before
  adding NoDb, UI, API, or RQ behavior. This scaffold is not a completed
  pre-implementation checkpoint.
- Implement published equations independently; do not copy or translate GPL
  pfdf code, tests, or documentation into this module.
- Reference PDF storage decisions live in `docs/pdfs/README.md`; gitignore
  publisher PDFs without established redistribution permission.
- Watershed/numerical engine package:
  [watershed/engine ExecPlan](../../../../docs/work-packages/20260908_staley_watershed_engine/prompts/completed/watershed_engine_execplan.md).
  Initial scope is one existing project watershed and outlet (ADR-0055), with
  no nested/channel assessment requirement. Accepted numerical policies are in
  [the engine contract](docs/staley2017_engine.md) and ADR-0056; future
  predictor and runtime integration remain separately scoped.
- Slope/SBS backend proposal: [docs/slope_sbs.md](docs/slope_sbs.md).
  [WBT package](../../../../docs/work-packages/20260908_staley_slope_sbs/package.md)
  is scaffolded, not executing; algorithm/support choices are not yet accepted.
