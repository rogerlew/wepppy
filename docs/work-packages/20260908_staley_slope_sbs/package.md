# Staley slope and SBS intersection in weppcloud-wbt

Status: scaffolded 2026-09-09 05:08 UTC; execution not started.

Implement the owned Rust terrain/burn intersection needed for M1 T, with both
WBT Python bindings, reproducible artifacts and independent reviews. Determine
and document the slope method before implementing the selected production
parameterization. This is a bounded part of roadmap stage 3, not complete M1
predictor or WEPPcloud integration.

Use the existing project watershed and resolved outlet only. Users manually
isolate suspected burned basins when creating projects. No nested assessments,
new delineation, or changes to existing routing/FVSlope behavior.

Read the [ExecPlan](prompts/active/slope_sbs_execplan.md), [tracker](tracker.md),
and [source findings and decisions](artifacts/slope_method_findings.md).
Canonical design: [slope/SBS contract](../../../wepppy/nodb/mods/postfire_debris_flow/docs/slope_sbs.md).

## Deliverables and gates

- Evidence-backed slope algorithm decision and parameterization ADR before
  executable selection; preserve uncertainty about original preprocessing.
- Registered Rust tool(s), both Python bindings, algorithm documentation and
  pinned invocation/output schema. Use existing owned dependencies.
- Slope, steep/burn intersection and coverage diagnostics; whole-project
  counts/area and M1 T when the accepted support policy allows it.
- Analytical tests, rebuilt-binary and both-binding smoke tests, three-site
  10 m/30 m sensitivity, independent correctness and security reviews.
- WEPPpy contract/roadmap handoff; no production caller, UI, RQ, binary
  installation, deployment, Soils rebuild, or network acquisition in the tool.

Security impact: **high**, because local raster paths and output publication
are new execution boundaries. Dedicated security artifact required; resolve
all medium/high findings before closure. Preserve existing source and output
files on rejected input. Correctness review must independently verify valid
workflows as well as malformed inputs.

Work spans `/workdir/weppcloud-wbt` (Rust, wrappers, fixtures and tool docs) and
`/workdir/wepppy` (canonical domain docs, evidence and handoff). The scaffold
lives in WEPPpy; WBT source and its existing generic slope defaults are unchanged.
