# Generated-output acceptance

Date: 2026-08-03 UTC

## Scope and safety

Acceptance used disposable reflink copies of two existing development batch
leaves under `/wc1/batch/watar-acceptance.W3oCwi/`. The source leaves were read
only. Their NoDb `wd` fields were rewritten to the disposable paths, and only
the disposable copies and isolated RedisPrep run IDs were mutated.

The production method exercised was
`BatchRunner._run_watar_stage`; both copies began with non-null
`run_wepp_hillslopes` and `run_wepp_watershed` timestamps and the required
`H.pass.parquet`, `H.wat.parquet`, and `totalwatsed3.parquet` inputs. Logs showed
the interchange repair/validation step before `running WATAR and AshPost`.

## Data-producing leaf

The disposable copy of `victoria-ca-2026-sbs/Sooke18` contained three burned
hillslopes. The first stdin-driven attempt exposed the expected Python spawn
limitation for scripts without a filesystem `__main__`; it failed before model
completion and left `run_watar` unset. The acceptance rerun disabled Ash's
process pool only for this harness invocation; it exercised the same production
Batch Runner stage, Ash model, AshPost, catalog, and timestamp code paths.

Observed results:

- `run_watar` timestamp: `1785724394`, written only after AshPost completed.
- Per-hillslope outputs: `ash/H1_ash.parquet`, `H2_ash.parquet`, and
  `H3_ash.parquet`, with their diagnostic plots.
- AshPost outputs: all five current parquet datasets, `post/README.md`, and
  `post/ashpost_version.json` version `1.0`.
- Catalog `generated_at`: `2026-08-03T02:33:14.019418+00:00`; the catalog listed
  all three hillslope parquet files, the version manifest, and all five post
  datasets.

## Legitimate no-data leaf

The disposable copy of `durability_test/OR-194` contained eight unburned
hillslopes. The normal production stage completed without per-hillslope Ash
data.

Observed results:

- `run_watar` timestamp: `1785724172`.
- `AshPost` return-period, cumulative-return-period, and burn-class-return-period
  state were all null.
- `ash/post/ashpost_version.json` and `ash/post/README.md` were absent, as were
  normal AshPost datasets.
- Catalog `generated_at`: `2026-08-03T02:29:32.774021+00:00`; the refreshed
  catalog retained `ash.nodb` and `ashpost.nodb` and contained no generated Ash
  dataset entries.

## Retry and compatibility evidence

The staging failure before AshPost completion demonstrated timestamp gating:
the subsequent run started with `run_watar` absent and executed WATAR again.
Automated tests provide deterministic selection coverage for completed versus
missing WATAR timestamps, optional exclusion without `ash.nodb`, old directive
map normalization, missing WEPP prerequisites, missing interchange artifacts,
single-storm rejection, AshPost failure, and climate invalidation.

No RQ enqueue site or dependency edge changed, so the existing single leaf job
remains the job-tree ordering boundary. `wctl check-rq-graph` reported the graph
artifacts current.

## Non-default persisted-input rerun

After the independent correctness review identified missing batch-base runtime
input persistence, the route was fixed and covered with depth-mode and
load-derived-mode request tests. A new disposable copy of
`victoria-ca-2026-sbs/Sooke18` was then persisted with the intentionally
non-default depth-mode values used by that route and passed through the
production Batch Runner WATAR stage.

The leaf log recorded
`Ash::run_ash(fire_date='9/17', ini_white_ash_depth_mm=2.3,
ini_black_ash_depth_mm=1.2)`. All three hillslopes and AshPost completed, and
the resulting state read back as fire date `9/17`, white depth `2.3`, black
depth `1.2`, with `run_watar` timestamp `1785725025`. This closes the
non-default leaf-consumption gap; the route tests separately prove that the
same normalized fields are persisted without enqueueing a batch-base job.
