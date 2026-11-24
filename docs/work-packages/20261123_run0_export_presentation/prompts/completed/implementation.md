# Extract Features Export presentation from the run blueprint

## Purpose and scope

A maintainer should be able to find the column schema reader and browser payload assembly directly. The run-page user should see the same layer catalog, defaults and discovery results. This is a faithful extraction from wepppy/weppcloud/routes/run_0/run_0_bp.py.

## Progress

- [x] 2026-11-24 05:02 UTC. Identify the contiguous Features Export helpers and their consumers.
- [x] 2026-11-24 05:04 UTC. Extract and wire the modules.
- [x] 2026-11-24 05:06 UTC. Compare the code and exercise route and rendering behavior.
- [x] 2026-11-24 05:06 UTC. Record outcomes for local integration.

## Surprises & Discoveries

The optional PyArrow imports and exception tuple live outside the export helper block. Move these with the column reader.

## Decision Log

Keep the three existing payload entry points in the route namespace. Group Parquet and README column discovery separately from catalog and profile assembly. Preserve route handlers and feature gating.

## Execution and verification

From the task checkout, move the helpers into features_export_columns.py and features_export_presentation.py beside the blueprint. Import the three entry points in the blueprint. Point helper tests at the owning module. Compare Python syntax trees with local master and run wctl run-pytest for run-page and export rendering coverage. Run the repository suite with --maxfail=1 and record any baseline failure. Commit the change and merge it through the local master worktree. Keep publication on hold.

## Outcomes & Retrospective

The three entry points remain wired through the existing feature gate. Both JSON comparisons matched. The focused run passed 456 cases with 15 skips. The repository-wide run reproduced the baseline team-route assertion. The tracker records exact receipts and payload hashes.
