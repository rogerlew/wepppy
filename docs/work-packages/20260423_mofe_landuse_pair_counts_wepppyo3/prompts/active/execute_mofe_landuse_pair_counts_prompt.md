# Execution Prompt - Multi-OFE Landuse Pair-Count Optimization (WP-01)

Execute the active work package end-to-end:

- Package: `/home/workdir/wepppy/docs/work-packages/20260423_mofe_landuse_pair_counts_wepppyo3/`
- Active ExecPlan: `/home/workdir/wepppy/docs/work-packages/20260423_mofe_landuse_pair_counts_wepppyo3/prompts/active/mofe_landuse_pair_counts_wepppyo3_execplan.md`

Requirements:
1. Add a production Rust/PyO3 pair-count API in `wepppyo3.raster_characteristics` for intersecting raster key pairs.
2. Integrate WEPPpy multi-OFE landuse area computation (`Landuse.build_managements`) to use the new Rust path.
3. Preserve behavior parity for area/pct coverage semantics and explicit failure contracts.
4. Add/update wepppyo3 + WEPPpy tests for API contracts and regression/parity behavior.
5. Run benchmark/parity comparisons on these run URLs/local roots:
   - `https://wc.bearhive.duckdns.org/weppcloud/runs/moth-eaten-blackhead/disturbed9002-wbt-mofe/` -> `/wc1/runs/mo/moth-eaten-blackhead`
   - `https://wc.bearhive.duckdns.org/weppcloud/runs/objectionable-sublimate/disturbed9002_wbt/` -> `/wc1/runs/ob/objectionable-sublimate`
   - `https://wc.bearhive.duckdns.org/weppcloud/runs/cochlear-beriberi/disturbed9002-mofe/` -> `/wc1/runs/co/cochlear-beriberi`
   - `https://wc.bearhive.duckdns.org/weppcloud/runs/ordained-incentive/disturbed9002-wbt-mofe/` -> `/wc1/runs/or/ordained-incentive`
   - `https://wc.bearhive.duckdns.org/weppcloud/runs/uninsured-deformation/disturbed9002-wbt-mofe/` -> `/wc1/runs/un/uninsured-deformation`
6. Use isolated temp dirs for benchmarks/parity; do not mutate source run data.
7. Save raw + summary artifacts under package `artifacts/`.
8. Keep active ExecPlan sections up to date (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`) and update `tracker.md` with UTC timestamps.
9. Close package after successful completion:
   - update `package.md` closure notes
   - move active ExecPlan to `prompts/completed/` with an outcome note
   - update `PROJECT_TRACKER.md` lifecycle/status entries
10. Commit and push once complete and validated.

Execution style:
- Proceed milestone-by-milestone without extra confirmation unless blocked by an external dependency.
- Apply smallest safe contract-preserving change first, then optimize.
- Do not modify unrelated files; ignore `wepppy/weppcloud/routes/usersum/generated/docs_index.json` if dirty.

End with concise closure summary:
- changed files
- behavior delta
- tests run/results
- benchmark results
- residual risks/follow-ups
