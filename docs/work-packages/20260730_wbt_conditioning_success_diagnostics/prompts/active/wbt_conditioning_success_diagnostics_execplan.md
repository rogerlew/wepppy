# WBT Conditioning Success Diagnostics ExecPlan

This is a living ExecPlan. Maintain `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` while executing it.

## Purpose

After this plan, a successful WBT channel delineation tells an ordinary user
how much the conditioning operation raised and lowered terrain. A fill that
raises terrain by hundreds of metres is explicit in the completion summary,
while technical diagnostics remain available in a run-local JSON sidecar.

## Progress

- [x] (2026-07-30) Inspected all four fork algorithms, wrappers, WEPPpy
  dispatch, RQ completion, controllers, and existing TOPAZ diagnostics.
- [x] (2026-07-30) Measured the incident fixture across Fill, Breach, and TOPAZ.
- [ ] Commit the reviewed contract checkpoint (both independent post-fix
  reviews passed).
- [ ] Implement WBT schema and instrumentation without raster-output changes.
- [ ] Build/install the WBT binary and validate four generated sidecars.
- [ ] Implement WEPPpy validation, formatting, RQ propagation, and UI summary.
- [ ] Complete regression gates, reviews, documentation, and package closure.
- [ ] Commit and push `weppcloud-wbt`.

## Surprises & Discoveries

- The tracked incident fixture produces a direct Fill maximum raise of
  approximately 379.02 m rather than 450 m. The production observation may
  reflect a differently clipped/preprocessed DEM; the contract reports the
  actual source-to-output maximum and therefore exposes either value.
- Existing TOPAZ diagnostics are algorithm-attributed and should be evolved,
  not replaced. Comparing TOPAZ output directly with the full-precision source
  makes almost every cell appear changed because TOPAZ first quantizes to
  decimetres.
- Standard Breach with `fill_pits=true` both lowers and raises terrain; those
  effects require separate attribution.

## Decision Log

- **2026-07-30**: Use an explicit optional `--diagnostics` path on every tool.
  WEPPcloud requires it for its own runs, but standalone WBT compatibility
  remains additive.
- **2026-07-30**: Exact schema, atomicity, correlation, failure, transport,
  rollout, and rollback rules live in
  `docs/schemas/wbt-conditioning-diagnostics-contract.md`.
- **2026-07-30**: The UI initially renders a single concise paragraph. It does
  not duplicate a summary and detail block.
- **2026-07-30**: Missing or invalid diagnostics is a job error for WEPPcloud,
  because silently omitting impact data would defeat the contract.

## Plan of Work

### Milestone 1: Contract checkpoint

Amend the DOM-05 field matrix, RQ response contract, child register, and package
decision artifact. Obtain two independent read-only reviews, disposition
findings, and commit this documentation as a standalone ancestor.

### Milestone 2: WBT producer

Add a shared diagnostics writer/helper where it genuinely reduces duplication.
Instrument each algorithm at its existing mutation points so stage counts,
extrema, areas, volumes, path lengths, resolution counts, and fallback use are
authoritative. Extend both Python wrappers and end-user docs. Assert that
diagnostics do not change output raster hashes.

### Milestone 3: WEPPpy consumer

Use a fixed `dem/wbt/relief.diagnostics.json` path and per-attempt operation
id. Enforce the schema's confinement, atomicity, validation, cleanup, job-meta,
base64url trigger, polling, replay, and rollout contracts without changing
queue topology.

Both channel controllers render the same plain-language summary into the
normal status panel using text content, never raw HTML. Invalid diagnostics use
the exact controlled failure contract.

### Milestone 4: Evidence and closeout

Run WBT unit/integration tests, four fixture executions, wrapper compilation,
focused WEPPpy topo/RQ/controller tests, frontend lint/test, bundle generation,
docs lint, broad Python sanity, and changed-exception checks. Record WBT commit,
push revision, installed binary hash, validation results, and review
disposition. Move this plan to `prompts/completed/` and close the package.

## Acceptance

- Fill summary includes its maximum source-to-output raise.
- Breach summaries independently state deepest cut and any pit/residual fill.
- Least-cost summaries state low points resolved/unresolved, deepest cut,
  longest path, search distance, and fallback-fill effects.
- TOPAZ summaries state depression fills, narrow-obstruction cuts, and flat
  relief independently.
- Every success states maximum raise and maximum cut with units.
- No algorithm parameters or raster values change.

## Outcomes & Retrospective

Pending execution.
