# Roads baseline characterization

Base: `96555f2f95326350d2d7007c19327378ea831ab0`. Mapping is read-only;
runtime outcomes are recorded separately as they complete.

## Compatibility and state matrix

| Boundary/state | Preserved behavior | Existing evidence anchors |
| --- | --- | --- |
| Never enabled or no upload | Explicit enable/upload prerequisite errors; inspection must not bind parameterization | controller initial-preview, enabled and prepare tests |
| Empty/no eligible contributors | Baseline-equivalent current result when otherwise valid; no invented contributor | controller missing-discha/no-selected test; unrutted zero-contributor tests |
| Populated four-design inputs | Same routing, native role order, PASS membership and output scope | controller four routing tests; native matrix/project suites |
| Supported legacy state | Absent parameterization remains unbound on reads; first explicit save/prepare binds | controller parameterization read/save tests |
| Invalid bound state | Explicit diagnostics, authorized repair retains invalid bytes | controller reset/repair and historical-readback tests |
| Failed upload commit | Restore staged file and durable state; post-commit failure must not roll back published state | upload rollback and completion-interruption tests |
| Failed native contributor/watershed | Retain failure summaries; do not publish current outputs | segment/watershed failure tests |
| Historic output after edits | Inspectable historical result; current admission invalidated | parameterization historical readback tests |
| Hostile/aliased publication paths | Reject symlink aliases and changed/incomplete publication | historical-readback alias/corruption tests |

## Caller and dependency seams

Keep every inventoried facade method, including private writer/profile/selection/
accounting helpers called directly by tests or the native matrix. Existing tests
patch `roads.py` globals `convert_geojson_file_to_monotonic_segments`,
`make_hillslope_run`, `run_hillslope`, `make_watershed_omni_contrasts_run`, and
`run_watershed`; pass those callables explicitly when extracting consumers.
Patches of `rasterio.open`, lifecycle functions and comparison functions operate
on shared module objects and must remain visible. Keep class import identity and
all persisted keys; no collaborator object is serialized.

## Execution decomposition

At baseline, the point-source loop is lines 4422-5016 and unrutted execution is
5018-6096. Extract inner stages rather than relocating those entire loops.
Point-source input assembly (4759-4868) is cohesive; routing resolution precedes
it and native execution/record construction follows it. Unrutted candidate plans
(5197-5480), strip reconciliation (5485-5697), strip execution (5699-5912), and
remainder execution (5914-6073) have separate responsibilities. Retain summary,
publication and cleanup ordering through all stages.

## Exception inventory

Nineteen broad sites: CRS translation at 708, 905, 1139, 1146, 1643; upload rollback
at 1222 and 1251; query diagnostics at 1360 and 1365; lifecycle boundaries at 1832
and 6364; trace/native aggregation at 4554, 4912, 5772 and 5972; watershed summary
at 6311; geometry-to-candidate-error translation at 5089; silent conversion/list
mutation catches at 2304 and 5048. Verify narrow native exception types before
changing catches. Preserve cancellation rollback and per-contributor continuation.
Silent catches require explicit characterization and disposition, not blind removal.

## Runtime qualification

Ordinary `wctl run-pytest` rejects the task worktree with
`WCTL_CHECKOUT_MISMATCH`; no tests start. Use a disposable `wctl run --rm
--no-deps --pull never` container with the task worktree mounted at
`/workdir/wepppy` and the canonical `checked_test_command` nonce guard. Preserve
installed image/user and existing dependency mounts. This does not recreate or
remount a shared service. The source `/wc1/runs/cl/clogging-starch` exists; its
current-policy expectations require the separately approved reconciliation.

Quality report: `/tmp/roads-quality.pre.json` and `/tmp/roads-quality.pre.md`.
Host Python 3.14.6 has no radon support; complexity remains unmeasured here.
