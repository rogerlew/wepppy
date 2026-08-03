# Batch Runner WATAR implementation correctness review

## Review scope

Independent review of the implementation working tree against checkpoint
ancestor `7f69e6654`, the approved SURF-02C field matrix, the active ExecPlan,
and the generated-output acceptance record. The review covered Batch Runner
task eligibility and retry classification, WEPP prerequisites, WATAR/AshPost
execution and timestamp ownership, NoDir locking, batch-base input propagation,
generic UI integration, documentation, and regression evidence.

No production or test file was modified by this review. This artifact is the
only review-authored file.

## Initial verdict (superseded by post-fix rereview)

**FAIL.** One high-severity correctness defect would silently run batch WATAR
with the wrong fire date and initial ash depths. One medium evidence gap and one
low documentation inconsistency also remain open.

| Severity | Open |
| --- | ---: |
| High | 1 |
| Medium | 1 |
| Low | 1 |

## Findings

### COR-01 - High - Batch-base WATAR submissions do not persist the runtime inputs consumed by leaves

`wepppy/microservices/rq_engine/ash_routes.py` calculates `fire_date`,
`ini_white_ash_depth_mm`, and `ini_black_ash_depth_mm` from the submitted depth,
load, or map mode at lines 214-267. It then calls `ash.parse_inputs(payload)`,
persists `ash_depth_mode`, and returns immediately for a batch base project at
lines 269-308. `Ash.parse_inputs` does not assign any of those three runtime
values. They are assigned only by `Ash.run_ash` at
`wepppy/nodb/mods/ash_transport/ash.py:621-623`, and base-project submissions
deliberately do not call or enqueue that method.

The new leaf integration passes `ash.fire_date`,
`ash.ini_white_ash_depth_mm`, and `ash.ini_black_ash_depth_mm` to `run_ash` at
`wepppy/nodb/batch_runner.py:689-693`. For a newly configured batch base these
therefore remain the constructor values from
`wepppy/nodb/mods/ash_transport/ash.py:148-150` (`8/4`, 5 mm, and 5 mm), even
when the operator submitted different values. Load mode is affected as well:
the route computes the load-to-depth values but does not store them before its
batch return.

This violates the approved persisted-input contract and can produce
scientifically incorrect yet apparently successful batch outputs. The focused
leaf invocation test injects a pre-populated fake `Ash`, so it proves only that
the leaf reads fields, not that the supported batch configuration route ever
writes them. The generated-output acceptance likewise starts from copies of
preexisting leaves and calls `_run_watar_stage` directly; it does not exercise
route-to-base-to-clone propagation and therefore cannot close this defect.

Required action:

1. Persist the already-normalized fire date and computed initial white/black
   depths in `Ash` state before the batch-base early return, under the existing
   NoDb locking contract. Preserve an existing fire date when the optional
   request field is absent rather than inventing a new value.
2. Add route-level regressions for batch depth mode and load-derived mode that
   assert the persisted controller values, while retaining the no-enqueue
   contract. Cover map mode if its persisted fallback depths are intentional.
3. Prove that a cloned leaf receives non-default values and that
   `_run_watar_stage` passes those exact values to `Ash.run_ash`.
4. Repeat generated-output acceptance with an intentionally non-default fire
   date and depths, recording the base and cloned `ash.nodb` values.

### COR-02 - Medium - The claimed regression and staging evidence is incomplete

The SURF-02C field matrix requires explicit coverage for a missing interchange
artifact, `NODIR_LOCKED` retry/archive-form rejection on the new combined lock,
WATAR-only retry through the leaf pipeline, old-state disable/save/reload, and
leaf/finalizer failure reporting. The current focused WATAR module covers the
positive helper order, sorted lock acquisition, timestamp prerequisites,
single-storm rejection, classifier state, and in-memory post-load
normalization. It does not exercise the required negative and persistence
cases above.

The generated-output record at
`artifacts/2026-08-03_generated_output_acceptance.md:59-62` specifically claims
automated missing-interchange coverage, but the only WATAR stage test creates
all three required artifacts before the check. The acceptance harness invoked
`BatchRunner._run_watar_stage` directly rather than the complete
`run_batch_project`/leaf-worker retry boundary, and its disposable result
directories are no longer present for independent inspection.

Required action: add the contract-listed negative, persistence, and leaf-worker
regressions; correct the acceptance claims to match executable evidence; and
retain commands or compact machine-readable evidence sufficient to audit the
non-default generated run after COR-01 is fixed.

### COR-03 - Low - Ash documentation overstates directive eligibility in the UI

`wepppy/nodb/mods/ash_transport/README.md:38` says a leaf exposes `Run WATAR`
only when it contains `ash.nodb`. The implemented and approved generic UI
always lists the batch-level directive through `BatchRunner.DEFAULT_TASKS`;
`ash.nodb` controls per-leaf execution and completion eligibility, not whether
the directive is displayed. Reword the documentation so operators do not
expect the checkbox to disappear for a non-Ash base.

## Confirmed behavior

- `run_watar` is registered after both WEPP tasks and before Omni, uses the
  existing label/glyph, and is optional per leaf based on `ash.nodb`.
- Retry classification is timestamp-authoritative and excludes WATAR when the
  optional controller file is absent.
- The leaf stage checks both WEPP timestamps, rejects single-storm climate,
  calls the three approved interchange helpers in order, verifies all three
  required files, and delegates completion timestamp ownership to
  `Ash.run_ash`.
- Combined climate/landuse/watershed NoDir locks are sorted, preflighted, and
  rechecked without a nested RQ call.
- AshPost failure prevents the Ash-owned timestamp; legitimate no-data
  post-processing clears return-period state, updates the catalog, and does not
  publish normal version/docs metadata.
- The generic route snapshot and controller render/save payload include
  `run_watar`; no new endpoint or RQ edge was introduced.
- Climate base resync invalidates the downstream `run_watar` timestamp.

## Validation performed

Focused Python review gate:

```text
wctl run-pytest tests/nodb/test_batch_runner_watar.py \
  tests/nodb/mods/test_ash_transport_run_ash.py \
  tests/nodb/mods/test_ashpost_no_data.py \
  tests/rq/test_batch_rq_retry_selection.py \
  tests/weppcloud/routes/test_batch_runner_snapshot.py --maxfail=1
```

Result: **45 passed**, 8 warnings.

Focused frontend gate:

```text
wctl run-npm test -- batch_runner
```

Result: **1 suite passed, 9 tests passed**.

`git diff --check 7f69e6654` passed. Changed-file broad-exception enforcement
passed with zero new unsuppressed broad catches.

These green tests confirm the covered mechanics but do not negate COR-01 or the
missing evidence in COR-02.

## Residual risk

The combined NoDir maintenance locks and the Ash NoDb lock have the existing
six-hour TTL without renewal. A very large WATAR leaf may outlive that TTL.
The one-job-per-leaf guard reduces ordinary batch contention, but an external
writer could contend after expiry; preserve this as an explicit operational
residual risk unless a separate lock-lifecycle package addresses it.

## Post-fix rereview

### Final verdict

**PASS.** There are no unresolved high- or medium-severity correctness
findings. COR-01, COR-02, and COR-03 are resolved. One low-severity evidence
gap remains and does not block this bounded integration.

| Severity | Open |
| --- | ---: |
| High | 0 |
| Medium | 0 |
| Low | 1 |

### Finding dispositions

#### COR-01 - Resolved

`wepppy/microservices/rq_engine/ash_routes.py` now identifies batch/base
context before its early return and, under `ash.locked()`, persists the
normalized fire date when supplied, computed white/black initial depths, and
depth mode. An omitted fire date preserves the existing controller value. The
ordinary standalone path remains outside this new mutation block and retains
its previous queue contract.

The route regressions now prove:

- batch depth mode stores non-default `9/17`, `2.3`, and `1.2` values without
  enqueueing;
- batch load mode stores its computed `20.0` and `10.0` depths and mode `0`;
  and
- a standalone request with no fire date still enqueues `None` and does not
  mutate the Ash runtime input fields before its worker executes.

The generated-output record now includes a non-default leaf rerun whose Ash
log and persisted state read back `9/17`, white depth `2.3`, black depth `1.2`,
and a post-AshPost `run_watar` timestamp. Together with the route tests and the
existing deterministic base `copytree` boundary, this proves the supported
route-to-state-to-leaf consumption path without introducing alternative
science defaults or conversions.

#### COR-02 - Resolved as a release blocker

The focused WATAR suite now has executable negative coverage for:

- an interchange helper sequence that still leaves
  `totalwatsed3.parquet` absent, proving `Ash.run_ash` is not called;
- bounded retry after `NODIR_LOCKED`; and
- archive-form rejection with `NODIR_ARCHIVE_ACTIVE`.

The acceptance record's missing-artifact statement now matches those tests and
records the non-default rerun. Timestamp-based optional selection, post-load
normalization, generic route persistence, generic leaf exception propagation,
and finalizer failure reporting are compositionally covered by the focused and
existing Batch Runner suites. The remaining lack of a single test spanning all
of those generic boundaries with a WATAR-named exception is retained below as
a low coverage gap rather than a correctness blocker.

#### COR-03 - Resolved

`wepppy/nodb/mods/ash_transport/README.md` now correctly says the Batch Runner
UI always exposes the generic directive and that `ash.nodb` controls only
per-leaf execution and completion eligibility.

### Rereview validation

Executed:

```text
wctl run-pytest tests/microservices/test_rq_engine_ash_routes.py \
  tests/nodb/test_batch_runner_watar.py \
  tests/nodb/mods/test_ash_transport_run_ash.py \
  tests/nodb/mods/test_ashpost_no_data.py \
  tests/rq/test_batch_rq_retry_selection.py \
  tests/weppcloud/routes/test_batch_runner_snapshot.py --maxfail=1
```

Result: **74 passed**, 8 warnings.

The previously executed focused frontend gate remains applicable because the
post-review fixes did not change controller code: **1 suite, 9 tests passed**.

### Remaining low-severity coverage gap

There is no single regression that starts with an old serialized directive map,
disables and durably reloads `run_watar`, then injects an AshPost exception
through `run_batch_watershed_rq` and asserts failed leaf metadata/finalizer
summary. The individual generic persistence, WATAR timestamp, AshPost failure,
classifier, and finalizer components are covered and the production code adds
no WATAR-specific catch or RQ branch, so this does not indicate a current
defect. A future durability pass can add that end-to-end composition test.

The existing six-hour lock-TTL residual risk described above also remains. The
separate security review records the direct-stage versus deployed RQ worker-pool
staging gap as SEC-L1.
