# Security Review - Batch Runner WATAR Integration

## Metadata

- **Package**: `docs/work-packages/20260802_batch_runner_watar/`
- **Reviewer**: Codex independent security reviewer
- **Date**: 2026-08-03 02:48 UTC
- **Security impact**: high; dedicated review required
- **Contract ancestor**:
  `7f69e6654ec64251b278df97dd6ed1a93a238954`
- **Implementation reviewed**: uncommitted `master` working-tree diff from the
  contract ancestor, including the route persistence correction, graph
  regeneration, untracked WATAR tests, and generated-output acceptance evidence
- **Review mode**: production code read-only; this artifact is the only file
  changed by the security reviewer

## Verdict

**Pass with one low-severity staging follow-up.** There are no unresolved high
or medium security findings. The implementation adds no endpoint, auth bypass,
RQ edge, nested worker, subprocess interface, network destination, dependency,
or secret. It invokes the existing Ash/AshPost pipeline inline in the existing
authorized batch leaf job and preserves the timestamp and failure boundaries.

Two medium findings raised during review were corrected and revalidated: batch
runtime inputs are now durably stored only for batch/base submissions without
changing standalone behavior, and the canonical RQ graph was regenerated after
the existing Ash enqueue-site line moved.

The security gate may pass. Work-package closeout should either exercise a
small WATAR batch through the deployed RQ batch worker pool or explicitly
disposition SEC-L1 as accepted staging residual risk.

## Findings

| ID | Severity | Surface | Finding and exploit path | Required action and evidence | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-M1 | Medium | Scientific input integrity and authority scope | The initial implementation consumed `Ash.fire_date` and initial depths from cloned leaf state, but the supported batch-base route did not persist submitted values. Its first remediation also substituted stored/default fire date for a standalone request that omitted the field, changing excluded standalone behavior and allowing unintended expensive science instead of the prior worker failure. | Restrict durable fire date/depth persistence to batch/base context under `ash.locked()`, retain standalone enqueue arguments exactly, add depth/load mode and standalone non-regression tests, and repeat generated evidence with non-default inputs. Current code does this at `wepppy/microservices/rq_engine/ash_routes.py` lines 306-319; the review rerun passed the route regressions, and generated acceptance records `9/17`, `2.3`, and `1.2`. | Resolved |
| SEC-M2 | Medium | RQ graph provenance | Editing the existing Ash enqueue-site file initially left the generated dependency graph and catalog line metadata stale. A stale graph weakens review and incident-response evidence even when the runtime edge is unchanged. | Regenerate with `python tools/check_rq_dependency_graph.py --write` and rerun `wctl check-rq-graph`. Both graph artifacts now identify the unchanged `run_ash_rq` edge at line 327; the checker passes with 144 edges. | Resolved |
| SEC-L1 | Low | Resource containment and staging fidelity | Generated-output acceptance invoked `BatchRunner._run_watar_stage` directly and disabled Ash multiprocessing for the data-producing rerun. An authorized admin can submit a multi-leaf WATAR batch, so this evidence does not exercise deployed RQ worker-pool concurrency, cancellation, or child-process cleanup. Production limits the exposure to four batch workers and six Ash processes per active leaf, and the integration adds no queue fan-out, so this is not a medium release blocker. | Run one small disposable WATAR batch through the normal RQ batch submission/worker path and record job-tree/process-bound evidence, or record operator acceptance of this bounded staging gap. Evidence: `artifacts/2026-08-03_generated_output_acceptance.md` lines 12-25; `docker/docker-compose.prod.yml` lines 605 and 628; `Ash.run_ash` caps its pool at `min(NCPU, len(args))`. | Open |

Open findings: high **0**, medium **0**, low **1**.

## Threat Model and Surface Review

### Authorization, session, and CSRF

No new route was added. The existing rq-engine Run Batch endpoint still
requires JWT scope `rq:enqueue` and the `admin` role. The existing Ash endpoint
still requires `rq:enqueue` plus `authorize_run_access` before resolving a run
or parsing inputs. The Flask directive mutation remains Admin-only and uses the
established session/CSRF boundary. `run_watar` is one boolean entry in the
existing generic directive mapping and creates no standalone request field or
bypass path.

Evidence:

- `wepppy/microservices/rq_engine/batch_routes.py` lines 51-60 and 80-94
- `wepppy/microservices/rq_engine/ash_routes.py` lines 179-196
- `wepppy/weppcloud/routes/batch_runner/batch_runner_bp.py` lines 381-400
- `tests/microservices/test_rq_engine_batch_routes.py::test_run_batch_requires_admin_role`

### Run scope, paths, and worker inputs

The new leaf stage receives no request payload. It loads `ash.nodb` from the
resolved leaf directory and consumes persisted fire date and depths. Composite
run IDs retain separator, slash, backslash, null-byte, and dot-component checks.
Required interchange artifacts are fixed filenames below
`wepp.wepp_interchange_dir`; no user-controlled shell string, command, dynamic
import, or new external path is introduced.

The existing Ash route now stores already-normalized runtime inputs only when
`run_group == "batch"` or the request is explicitly a base-project context.
Missing fire date preserves the prior stored value. These fields and
`ash_depth_mode` are changed within `ash.locked()`, so successful exit uses the
canonical atomic NoDb dump path. Non-batch requests retain the original setter
and enqueue arguments, including `None` for an omitted fire date.

Evidence:

- `wepppy/weppcloud/utils/helpers.py` lines 223-245 and 280-300
- `wepppy/microservices/rq_engine/ash_routes.py` lines 306-337
- `wepppy/nodb/batch_runner.py` lines 641-700
- `tests/microservices/test_rq_engine_ash_routes.py` lines 116-140 and 159-230
- `tests/nodb/test_batch_runner_watar.py::test_run_watar_stage_repairs_interchange_and_uses_persisted_inputs`

### Ordering, locking, persistence, and data integrity

WATAR requires both WEPP timestamps, rejects single-storm climates, runs the
three approved interchange helpers, and explicitly checks all three required
files before Ash execution. The combined NoDir helper deduplicates and sorts
`climate`, `landuse`, and `watershed`, preflights archive form before locking,
rechecks after acquiring all locks, releases partial acquisitions through
`ExitStack`, and retries only bounded `NODIR_LOCKED` failures. Ash retains its
own NoDb lock and existing output cleanup behavior.

`Ash.run_ash` invokes `AshPost.run_post` before writing `run_watar`. Exceptions
are not swallowed by Batch Runner, so failed WATAR or catalog/post-processing
work leaves the timestamp absent and flows into existing leaf failure metadata
and finalizer behavior. Climate resync invalidates WATAR. Timestamp-only retry
adds no artifact walk or attacker-driven filesystem amplification during
classification.

Evidence:

- `wepppy/nodb/batch_runner.py` lines 199-237, 657-700, and 1015-1056
- `wepppy/nodb/mods/ash_transport/ash.py` lines 856-869
- combined lock retry, archive rejection, and missing-artifact tests in
  `tests/nodb/test_batch_runner_watar.py`
- AshPost failure and no-data regressions under `tests/nodb/mods/`
- `tests/rq/test_batch_rq_retry_selection.py::test_final_batch_complete_publishes_failure_summary`

### Queue, cancellation, and resource use

WATAR runs synchronously inside the existing one-job-per-leaf boundary; there
is no nested `run_ash_rq`, deferred WATAR job, or new finalizer dependency. The
active-batch preflight remains authoritative for duplicate batch submissions.
The regenerated graph confirms that the existing standalone `run_ash_rq` edge
is unchanged and that no Batch Runner WATAR edge was added.

Ash multiprocessing is inherited and capped by `WEPPPY_NCPU`; production batch
workers configure four RQ workers with `WEPPPY_NCPU=6`. This bounds, but does
not eliminate, CPU and memory pressure from an authorized large batch. SEC-L1
records the remaining staging evidence gap.

### Secrets, logging, egress, and supply chain

The diff adds no secrets, credentials, environment variables, packages, HTTP
clients, network destinations, or shell execution. New log and exception text
contains task names and run-scoped artifact paths only and uses preexisting
batch log/status surfaces. Catalog publication and Redis timestamping remain
existing Ash/AshPost behavior.

## Independent Validation

The reviewer ran the focused Python security/correctness surface after the
final persistence and lock-test corrections:

    wctl run-pytest tests/microservices/test_rq_engine_ash_routes.py tests/nodb/test_batch_runner_watar.py tests/nodb/mods/test_ash_transport_run_ash.py tests/nodb/mods/test_ashpost_no_data.py tests/rq/test_batch_rq_retry_selection.py tests/microservices/test_rq_engine_batch_routes.py tests/weppcloud/test_batch_runner_endpoints.py tests/weppcloud/routes/test_batch_runner_snapshot.py --maxfail=1

Result: **93 passed**.

    wctl run-npm test -- batch_runner

Result: **1 suite, 9 tests passed**.

    wctl check-rq-graph

Result: **pass; 144-edge RQ dependency graph artifacts are current**.

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref 7f69e6654

Result: **pass; two changed production Python files, zero new unsuppressed broad
handlers**.

`git diff --check 7f69e6654` passed. A targeted diff scan found no new secret,
credential, authorization, shell, subprocess, HTTP, or network literals.

## Residual Risk and Containment

- SEC-L1 remains open at low severity.
- Ash route configuration remains a sequence of separately locked mutations
  (`parse_inputs`, optional raster persistence, then batch runtime inputs).
  Concurrent authorized configuration submissions could interleave at those
  boundaries. This is inherited route behavior rather than an authorization
  bypass; the normal UI issues one submission, and each durable write remains
  lock-protected and stale-write checked.
- Ash and NoDir work retains the repository's existing six-hour lock TTL
  without renewal. A very large leaf may outlive that TTL. One-job-per-leaf
  selection reduces ordinary contention, but abrupt worker termination or an
  external writer remains an operational risk boundary.
- Expensive work remains intentionally available to authenticated admins. The
  active-batch guard, batch queue, worker-pool sizing, Ash process cap, and
  timestamp retry boundary provide containment.
- Rollback is to disable `run_watar` and revert the bounded integration while
  preserving generated Ash artifacts for diagnosis.

## Sign-off

- **Security reviewer**: Codex independent security reviewer - pass, 2026-08-03
- **Unresolved release-blocking findings**: none
- **Operator risk acceptance required**: only if SEC-L1 is not closed with a
  normal RQ worker-pool staging run before package closeout
