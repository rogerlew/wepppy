# Execute: MOFE `.mofe.man` Synthesis Process-Pool Migration

Execute the active work package end-to-end:

- Package: `/home/workdir/wepppy/docs/work-packages/20260423_mofe_man_synthesis_process_pool/`
- Active ExecPlan: `/home/workdir/wepppy/docs/work-packages/20260423_mofe_man_synthesis_process_pool/prompts/active/mofe_man_synthesis_process_pool_execplan.md`

Requirements:
1. Migrate `.mofe.man` synthesis in `wepppy/nodb/core/landuse.py::_build_multiple_ofe` to canonical `createProcessPoolExecutor` orchestration.
2. Preserve parity with current behavior, including:
   - deterministic per-hillslope output filenames (`hill_<topaz_id>.mofe.man`)
   - segment ordering and disturbed/RAP override semantics
   - explicit error contracts (no silent mismatch/error swallowing)
3. Use canonical pool behavior:
   - spawn-first (`prefer_spawn=True`)
   - retry with fork context on `BrokenProcessPool` (`prefer_spawn=False`)
   - bounded sequential fallback only when pool failures remain `BrokenProcessPool`
   - raise non-`BrokenProcessPool` exceptions
4. Add/update tests for:
   - process-pool success path
   - spawn failure -> fork retry
   - double pool failure -> sequential fallback
   - non-pool error propagation
   - synthesis parity regressions for deterministic fixtures
5. Run benchmark/parity comparisons with isolated temp dirs (do not modify source run data), and record:
   - per-run timings
   - mean/stddev
   - percent delta
6. Save artifacts under package `artifacts/` (raw + summary + review artifacts):
   - `benchmark_raw.json`
   - `benchmark_summary.md`
   - `parity_raw.json`
   - `parity_notes.md`
   - `2026-04-23_code_review.md`
   - `2026-04-23_qa_review.md`
   - `2026-04-23_security_review.md`
7. Update package docs as living artifacts:
   - active ExecPlan sections (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`)
   - `tracker.md` with UTC timestamps
8. Close package after successful completion:
   - update `package.md` closure notes
   - move active ExecPlan to `prompts/completed/` with outcome note
   - update `PROJECT_TRACKER.md` lifecycle/status entries

Execution style:
- Proceed milestone-by-milestone without extra confirmation unless blocked by external dependency.
- Apply smallest safe contract-preserving changes first, then optimize.
- Do not modify unrelated files.
- Keep explicit failures; do not add broad exception swallowing.
- Commit and push once complete and validated.

End with a concise closure summary:
- changed files
- behavior delta
- tests run/results
- benchmark results
- review findings status
- residual risks/follow-ups
