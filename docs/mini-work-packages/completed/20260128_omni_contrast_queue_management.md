# Mini Work Package: Omni Contrast Queue Concurrency + Rebuild Hygiene
Status: Complete
Last Updated: 2026-01-28
Primary Areas: `wepppy/rq/omni_rq.py`, `wepppy/nodb/mods/omni/omni.py`, `wepppy/nodb/mods/omni/omni.pyi`, `stubs/wepppy/nodb/mods/omni/omni.pyi`

## Objective
Throttle Omni contrast execution to avoid runaway parallel WEPP jobs, clear stale contrast runs/dependencies on rebuild, and add contrast run-status markers to distinguish in-progress vs completed work.

## Scope
- Add `contrast_batch_size` property (default 6) and batch job dependencies in `run_omni_contrasts_rq`.
- Reset contrast build state on rebuild (clear `_contrast_dependency_tree`, remove `_pups/omni/contrasts/*/` run dirs).
- Ensure contrast names are replaced (not appended) across all build modes.
- Record contrast run status (`started`, `failed`, `completed`) in `wd/omni/contrasts/contrast_XXXXX.status.json` and report `in_progress` when applicable.

## Non-goals
- Changing WEPP model execution behavior.
- Adding new UI controls or dashboard changes.

## Implementation Notes
- README markers remain the success gate; status files only annotate in-progress/failed runs.
- `run_omni_contrasts_rq` skips `in_progress` contrasts to avoid duplicate work while runs are active.

## Validation
Manual checks on `/wc1/runs/wa/walk-in-obsessive-compulsive`:
1. Configure 10+ contrasts and run RQ: confirm only `contrast_batch_size` contrasts execute concurrently.
2. Build contrasts with 3 pairs, then 1 pair: confirm `_contrast_names` count shrinks and `_pups/omni/contrasts/*/` is cleaned.
3. Re-run contrasts: confirm completed ones log "up-to-date, skipping" and in-progress ones show `in_progress`.
4. Kill a contrast run mid-WEPP, re-run: failed contrast is re-queued (status flips to `failed` then `needs_run`).

## Follow-ups
- Document `contrast_batch_size` in user-facing Omni config docs if needed.
