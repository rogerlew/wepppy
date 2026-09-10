# Execution tracker

## Status

2026-09-09 UTC: implementation, installed native release, fresh local restart, full WEPP integration and all test/review gates passed. Both repositories pushed and remote-verified; package complete.

## Task board

- [x] Record approved behavior, target environment, and read-only run/map availability.
- [x] Scaffold package, active ExecPlan, ADR, contract, and evidence checklist.
- [x] M1: commit contract checkpoint and prepare external rollback baseline.
- [x] M2: implement/test generic wepppyo3 aggregation and destination nodata support.
- [x] M3: integrate shared project-grid kslast preparation and diagnostics.
- [x] M4: build/install py312 extension and validate source-to-import provenance.
- [x] M5: drain local work, `wctl down`, `wctl up -d`, verify new processes/imports.
- [x] M6: run full local seductive-sabra WEPP workflow and verify outputs.
- [x] M7: complete reviews/gates, commit and push both repositories, close package.

## Decisions

2026-09-09 UTC, user/Codex: generic Rust `default_value`, not a kslast-specific argument; finite zero/negative generic values remain valid. WEPPpy owns positive conductivity validation. Missing area uses the configured default; missing area without one is an error. Destination nodata must be explicit for this stack operation. Preserve nearest-neighbor source classes and existing hillslope-level MOFE assignment. Local stack restart plus actual model execution is mandatory evidence, not an optional smoke test.

## Compatibility and regression plan

Additive native API and run artifacts. Validate grid/CRS/masks and equal projected pixel areas before aggregation. Preserve generic stacker defaults and no-map/developed-soil behavior. Exercise ordinary and MOFE prep, partial/no coverage, all nodata, invalid values, archive roots, and reruns after grid/map/default changes. Verify all downstream soil files and fresh post-run outputs. Do not rewrite existing live tables merely to make comparisons pass.

## Risks and recovery

Restart affects other local services; wait for active local jobs to finish and verify run is quiescent. Save run outputs and controller state outside the run before mutation. Replace native shared objects atomically, never truncate mapped files. Record source and artifact hashes and validate imported paths after restart. If blocked by missing dependency, busy external job, or model failure, record evidence and leave package open rather than claim integration passed.

## Publication ledger

WEPPpy master implementation: `9e1c48f4d`; validated evidence publication: `252bac87998a3c2a900b64bb4495f0078466e04b`. wepppyo3 main native source: `125edc1`; published release: `d6641abfe3a932826b0e161494c7eafd0ba4e8d8`. Both remote tips were verified before this documentation closeout; see artifacts/publication.json. Release hash, process identities and full job tree are recorded in artifacts. Unrelated dirty code-quality files remain untouched.

2026-09-09 UTC execution update: contract checkpoints and external backup complete. Native kernel builds; 8 Rust tests and 42 real-raster release tests pass. Shared prep/stacker targeted suite: 21 pass. M2/M3 implemented with further integration tests pending. Directory-only correction and staging rationale are in the canonical contract.

2026-09-09 UTC: M2–M5 complete. 43 native release tests and 28 project-grid/prep tests pass; both real soil workers verified for two OFEs and developed exemptions. Independent numerical, nodata conversion and path-containment findings were fixed and retested. Two authorized local restarts completed; final fresh service hashes match release_manifest.json. Full RQ job 90431b48-4138-4f28-89f6-90a5b3806f7e has completed prep and is executing hillslopes. Broad suite running; M6/M7 remain open.

2026-09-09 23:57 UTC: M6 passed. All 15 RQ jobs finished; unchanged 46-year model completed. Final oracle validates 505 hillslopes / 1259 OFEs and 25 fresh finite output tables (70,151,967 rows), zero defaulted hillslopes. Full-suite and publication gate remain open.

2026-09-10 00:01 UTC: All milestones complete. Both validated revisions pushed and remote-verified: WEPPpy 252bac87998a3c2a900b64bb4495f0078466e04b; wepppyo3 d6641abfe3a932826b0e161494c7eafd0ba4e8d8. Publication receipt: artifacts/publication.json. Final documentation closeout is pushed on the same WEPPpy branch and its tip checked at handoff.
