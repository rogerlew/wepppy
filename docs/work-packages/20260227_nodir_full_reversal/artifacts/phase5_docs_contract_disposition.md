# Phase 5 Docs and Contract Disposition

## Scope Docs Rows (target_phase=5)

- `wepppy/nodb/mods/omni/README.md`:
  - Removed remaining `.nodir` wording from developer architecture/clone-flow sections.
  - Document now reflects directory-only shared-input behavior.
- `wepppy/tools/migrations/README.md`:
  - Added directory-only status banner.
  - Marked `nodir_bulk.py` as historical/retired from active migration flow.

## NoDir Schema Contract Retirement

The following schema docs are now explicitly marked archived/deprecated/historical from active contract flow:

- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/schemas/nodir_interface_spec.md`
- `docs/schemas/nodir-touchpoints-reference.md`

Each file includes an "Archived / Deprecated (Historical, 2026-02-27)" banner at the top.

## Superseded Package Prompt Retirement

Moved all markdown files from `docs/work-packages/20260214_nodir_archives/prompts/active/` to `docs/work-packages/20260214_nodir_archives/prompts/completed/` with `canceled_` prefix.

- Moved count: `9`
- Remaining files under `prompts/active/`: `0`

Note: `wctl doc-mv` failed in this environment due permission errors under `./.docker-data/postgres`; direct `mv` was used as a fallback to complete retirement.

## Tracker Surface Updates

- Updated `docs/work-packages/20260214_nodir_archives/tracker.md` to record canceled prompt retirement.
- Updated `PROJECT_TRACKER.md` NoDir Full Reversal section status/next steps to current Phase 5 execution state.
