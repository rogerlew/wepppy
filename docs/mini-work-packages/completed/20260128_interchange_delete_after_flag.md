# Mini Work Package: Interchange Delete-After-Conversion Flag
Status: Completed
Last Updated: 2026-01-28
Primary Areas: `wepppy/nodb/core/wepp.py`, `wepppy/nodb/wepp_nodb_post_utils.py`, `wepppy/nodb/batch_runner.py`, `wepppy/wepp/interchange/*`, `wepppy/rq/wepp_rq.py`, `wepppy/nodb/mods/omni/omni.py`, `wepppy/tools/migrations/migrate_interchange.py`, `wepppy/tools/migrations/interchange.py`

## Objective
Add a run-level `[interchange] delete_after_interchange=true` flag that, when enabled, deletes the WEPP text outputs after successful Parquet conversion so runs can shed bulky raw files while keeping interchange artifacts.

## Scope
- Parse `delete_after_interchange` from run configs (default False).
- Thread the flag through **canonical interchange creation paths** only:
  - Run completion (`wepppy/nodb/core/wepp.py`)
  - Batch + culvert post utils (`wepppy/nodb/wepp_nodb_post_utils.py`, `wepppy/nodb/batch_runner.py`)
  - RQ WEPP execution (`wepppy/rq/wepp_rq.py`)
  - Omni contrast workflow (`wepppy/nodb/mods/omni/omni.py`)
  - Migration CLI (`wepppy/tools/migrations/migrate_interchange.py`) and migration runner (`wepppy/tools/migrations/interchange.py`)
- Update interchange entry points to accept the flag and delete source files only after successful parquet writes.
- Preserve safety: ignore missing sources on cleanup, and never delete unless the flag is true.
- Update WEPP run summary to use interchange row counts and remove flowpath counts (prevents zero counts after cleanup).

## Non-goals
- Changing interchange schemas or query engine behavior.
- Deleting interchange parquet outputs or other run artifacts.
- Adding background cleanup jobs beyond the conversion call path.
- Wiring the flag through secondary or legacy interchange generators (query engine auto-activation, observed workflows, interchange_rq).
- The query engine auto-activation path (`wepppy/query_engine/activate.py`) intentionally remains read-only; it should never delete raw outputs just because a consumer asked for catalog activation.

## Implementation Plan
1. **Config plumbing**
   - Add a `delete_after_interchange` accessor on `NoDbBase` using `config_get_bool("interchange", "delete_after_interchange", False)`.
   - Keep defaults conservative (False) to avoid surprises for existing runs.
2. **Interchange API updates**
   - Add `delete_after_interchange: bool = False` to the following conversion entry points:
     - `run_wepp_hillslope_interchange`
     - `run_wepp_watershed_interchange`
     - `run_wepp_watershed_tc_out_interchange`
     - Targeted helpers used directly (`run_wepp_hillslope_pass_interchange`, `run_wepp_hillslope_wat_interchange`, `run_wepp_watershed_ebe_interchange`, `run_wepp_watershed_chanwb_interchange`, `run_wepp_watershed_loss_interchange`, `run_wepp_watershed_chan_peak_interchange`, etc.)
   - After each writer completes, delete the source text file(s) that writer consumed; handle `.gz` variants where appropriate.
   - Gate existing `tc_out.txt` deletion behind the flag (currently unconditional).
3. **Callsite threading**
   - Pass `delete_after_interchange` from config into the canonical callsites only (run completion, batch/culvert post utils, `wepp_rq`, `omni`, `migrate_interchange`).
4. **Stubs/docs**
   - Update the `.pyi` signatures under `wepppy/wepp/interchange/`.
   - Extend `wepppy/wepp/interchange/README.md` to document the new flag and deletion semantics.

## Call Sites to Modify
- `wepppy/nodb/core/wepp.py:2704` (run completion)
- `wepppy/nodb/wepp_nodb_post_utils.py:40`, `wepppy/nodb/wepp_nodb_post_utils.py:78`
- `wepppy/nodb/batch_runner.py:370`, `wepppy/nodb/batch_runner.py:378`
- `wepppy/rq/wepp_rq.py:1012`, `wepppy/rq/wepp_rq.py:1064`, `wepppy/rq/wepp_rq.py:1170`
- `wepppy/nodb/mods/omni/omni.py:168`, `wepppy/nodb/mods/omni/omni.py:4453`
- `wepppy/tools/migrations/interchange.py:115`, `wepppy/tools/migrations/interchange.py:130`
- `wepppy/tools/migrations/migrate_interchange.py:134`, `wepppy/tools/migrations/migrate_interchange.py:158`
- `wepppy/wepp/interchange/hill_interchange.py:63-78`
- `wepppy/wepp/interchange/watershed_interchange.py:47-57`
- `wepppy/wepp/interchange/watershed_tc_out_interchange.py:191`
- `wepppy/weppcloud/routes/nodb_api/wepp_bp.py:498`
- `wepppy/weppcloud/templates/reports/wepp_run_summary.htm:1`

## Validation
- Run a standard watershed scenario with `delete_after_interchange=true`; verify parquet outputs exist and the source text files are removed only after conversion succeeds.
- Run a single-storm scenario; ensure optional outputs are handled and cleanup respects missing files.
- Ensure query engine activation and migrations still work when the flag is unset.
- Confirm WEPP run summary shows non-zero hillslope counts with interchange present, and that Flowpaths is removed from the summary.

## Follow-ups
- Decide whether to expose the flag in UI/config builders beyond manual cfg edits.
- Consider a safety report that logs exactly which source files were removed.
