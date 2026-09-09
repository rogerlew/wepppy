# Execution tracker

## Status

2026-09-09 UTC: scaffold complete; implementation, build/install, restart, model run, reviews, and publication not started.

## Task board

- [x] Record approved behavior, target environment, and read-only run/map availability.
- [x] Scaffold package, active ExecPlan, ADR, contract, and evidence checklist.
- [ ] M1: commit contract checkpoint and prepare external rollback baseline.
- [ ] M2: implement/test generic wepppyo3 aggregation and destination nodata support.
- [ ] M3: integrate shared project-grid kslast preparation and diagnostics.
- [ ] M4: build/install py312 extension and validate source-to-import provenance.
- [ ] M5: drain local work, `wctl down`, `wctl up -d`, verify new processes/imports.
- [ ] M6: run full local seductive-sabra WEPP workflow and verify outputs.
- [ ] M7: complete reviews/gates, commit and push both repositories, close package.

## Decisions

2026-09-09 UTC, user/Codex: generic Rust `default_value`, not a kslast-specific argument; finite zero/negative generic values remain valid. WEPPpy owns positive conductivity validation. Missing area uses the configured default; missing area without one is an error. Destination nodata must be explicit for this stack operation. Preserve nearest-neighbor source classes and existing hillslope-level MOFE assignment. Local stack restart plus actual model execution is mandatory evidence, not an optional smoke test.

## Compatibility and regression plan

Additive native API and run artifacts. Validate grid/CRS/masks and equal projected pixel areas before aggregation. Preserve generic stacker defaults and no-map/developed-soil behavior. Exercise ordinary and MOFE prep, partial/no coverage, all nodata, invalid values, archive roots, and reruns after grid/map/default changes. Verify all downstream soil files and fresh post-run outputs. Do not rewrite existing live tables merely to make comparisons pass.

## Risks and recovery

Restart affects other local services; wait for active local jobs to finish and verify run is quiescent. Save run outputs and controller state outside the run before mutation. Replace native shared objects atomically, never truncate mapped files. Record source and artifact hashes and validate imported paths after restart. If blocked by missing dependency, busy external job, or model failure, record evidence and leave package open rather than claim integration passed.

## Publication ledger

WEPPpy branch observed: master. wepppyo3 branch observed: main at 2c31f6c. Recheck at execution; do not switch branches. WEPPpy has unrelated dirty changes; stage only package-owned hunks. Source commit, release hash, integration job IDs, final commits, and remote tips: pending execution.
