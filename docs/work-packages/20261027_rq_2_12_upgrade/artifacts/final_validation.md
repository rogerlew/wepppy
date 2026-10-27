# RQ 2.12 final validation ledger

Installed forest source: `b5cac8166`; dashboard sibling: `91f62b9`.
Complete isolated full suite passed. Independent correctness and security reviews are retained alongside the exact original working-tree failure attribution.

| Gate | Evidence | Result |
| --- | --- | --- |
| Installed targeted compatibility/security/consumer tests | [targeted ledger](rebuilt_targeted_validation.md) | 598 passed, zero skips |
| Real Redis/workers lifecycle | [lifecycle ledger](lifecycle_evidence.md) | 13 passed, 201.70 seconds |
| Required full repository suite on user working tree | [full log](rebuilt-full-pytest.log) | 6,810 passed, 61 skipped; one independently reproduced preexisting Roads provenance failure |
| Full suite on isolated committed migration source | [log](rebuilt-clean-full-pytest.log), [source identity](clean-full-suite-source.json), [runtime](clean-full-suite-runtime.json) | 11,948 passed, 226 skipped, 5,826 warnings; 3,304.46 seconds; Docker exit 0 |
| RQ graph | [log](rebuilt-rq-graph.log) | Pass; no queue topology changes |
| Worker and dependency stubtest | [worker](rebuilt-stubtest-worker.log), [dependencies](rebuilt-stubtest-dependencies.log) | Both pass |
| Test stub completeness | [log](rebuilt-check-test-stubs.log) | Pass |
| Changed-file broad exception enforcement | [log](rebuilt-broad-exceptions.log) | Pass; existing boundary line references refreshed |
| Code quality observability | [report](code-quality-summary.md) | Completed, observe-only |
| Installed API/model/artifact acceptance | [acceptance](acceptance_upgraded.md) | Pass, including deleted-output restoration after documented NFS recovery |
| Installed dashboard HTTP | [readback](dashboard-installed.json) | Pass |
| Runtime version/configuration | [final readback](forest_runtime_final.json) | All 17 relevant containers run RQ 2.12.0 |
| Worker pools | [final readback](rebuilt-rq-info-final.log) | 11 workers, no queued/started jobs at observation |

## Complexity and scope disposition

The observe-only report records small increases in existing worker failure and
job-listing functions: explicit tolerant-finalizer handling and status value
normalization account for these increases. The stopped-parent guard adds 16
source lines to the dependency module while retaining its transaction structure.
The longer new lifecycle test keeps actual worker orchestration, fault injection
and assertions together. These changes are within the bounded compatibility and
regression budget; no unrelated refactor is justified by telemetry. The host
report lacks radon, so Python cyclomatic complexity is unavailable; source line
and function-length observations and JavaScript metrics were collected. No
frontend implementation changed, so frontend gates are not applicable.

## Retention and limitations

Retain the disposable baseline/upgraded/cancellation projects and their receipts
for reproducibility. The protected pre-cutover Redis snapshot is gitignored,
mode 0600 under a mode 0700 directory; it is not a public artifact. Original
images are retained under rollback tags. Historical rollback proof replays
original 1.16.2 state in isolation; it does not authorize restoring stale state
over accepted work or downgrading 2.x-written Redis in place. Running 1.x work
must drain, and mixed-version workers are unsupported.

Artifact hygiene excluded environment/secret contents. Four literal shell credential-variable references in captured container command strings were additionally replaced with `[REDACTED]`; no evaluated credential values were present.

Production was not upgraded. Native webhooks were not enabled.

## Working-tree provenance failure and clean-source gate

The [independent attribution](roads_baseline_attribution.md) reproduces the same Roads source-hash mismatch under original RQ 1.16.2. The migration does not change that source. Do not refresh the staleness record for an unrelated uncommitted accessor: doing so would break the committed revision. A separate isolated full run uses the rebuilt image and read-only committed copies of all five preexisting dirty tracked files. No working-tree source, template, test or publication record is changed.

An initial continuation was deliberately interrupted before starting the isolated complete run to avoid overlapping fixtures. The existing in-process RQ signal handler translated our SIGINT into `StopRequested` in a readonly test; its 875 passes/29 skips and terminal interruption are retained in `rebuilt-full-pytest-continuation.log`, not treated as a completed or failed application acceptance run. The subsequent complete isolated suite passed, closing the migration regression gate without altering or endorsing the unrelated working-tree drift.

## Final operations and documentation

[Health readback](final_health.json) verifies web and rq-engine HTTP 200 and clean full-suite container exit 0. All 17 services remain on RQ 2.12.0; the 11 installed workers are idle with no queued or started jobs at final observation. The test one-off removed itself. [Disposable cleanup](disposable_cleanup.json) stopped only the owned Redis test container, retained its bind-mounted data, and verified shared Redis remained running; no Redis flush or volume deletion occurred.

[Documentation lint](final-doc-lint.log) covers changed guidance, contracts, indexes and the package. Final correctness/security review artifacts contain their sign-offs. The full working-tree command remains a failed invocation caused by preserved unrelated Roads edits; the clean-source full result is stated separately throughout closeout.

Source and documentation whitespace checks pass. Raw `.log` artifacts intentionally retain terminal carriage returns, trailing spaces and blank lines as execution evidence; they are excluded from formatting checks rather than rewritten.
