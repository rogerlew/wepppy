# GridMET admission code QA review

Status: **PASS**, 2026-09-07 16:40 UTC. No unresolved high, medium, or low
findings. Final recheck followed the primary correctness PASS and includes
the last admission diagnostic and configuration-validation changes.

## Scope and approach

Independent secondary QA review of runtime, client propagation, tests, probe,
and operator documentation against contract checkpoint
`1b4835ca73bc67c9c84ecbb26f596aab4078e234`. Untracked implementation and test
files were included. The review uses
`docs/schemas/gridmet-redis-admission-contract.md` and the active ExecPlan as
the requirements source. No runtime files were edited by this reviewer.

The review examined ownership transitions, renewal shutdown, bounded failure
handling, retry deadlines, response lifetime, explicit disabled configuration,
process-pool propagation, and whether probe evidence can support its claims.

## Findings and resolution

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| QA-01 | Medium | `GridMetPermit.__exit__` initially checked failure before `release()` joined an in-flight renewal, allowing a renewal failure arriving during shutdown to escape the exit check. | Resolved: `admission.py` checks recorded failure after release and waits for renewal before marking the permit closed. Deterministic tests cover both successful and failed in-flight renewals. Delayed acquire replies are rejected for exhausted admission deadlines and expired conservative lease validity. |
| QA-02 | Medium | `tools/gridmet_admission_probe.py:summarize` initially compared acquisition/release counts without pairing owners, allowing unrelated or repeated completion records to support a false PASS. | Resolved: unique `(container, pid, id)` owners must match. The summary reports participating containers and supports a minimum-container requirement. File aggregation rejects mismatched namespaces. Regressions cover each case. |
| QA-03 | Low | A later `snapshot(active_ticket).waited_seconds` initially continued counting hold/transfer duration as queue wait. | Resolved: acquisition freezes the local timing record; subsequent active snapshots retain queue wait instead of adding hold time. Release removes the timing record. |

## Quality assessment

- The dedicated configuration/controller/permit module keeps Redis state out
  of client data parsing and out of process-pool arguments. Primitive frozen
  configuration and lazy connections make the ownership boundary explicit.
- Shared response and chunk helpers keep point/grid lifecycle checks aligned.
  Tests assert closure before release, release before validation and backoff,
  suppression of private query URLs, lease-loss cleanup, and one deadline
  across retries. These assertions cover externally meaningful behavior.
- Propagation changes preserve existing positional APIs and the local
  four-worker GridMET pool. Tests pickle actual submitted arguments and cover
  indirect Daymet/PRISM, SNOTEL, monthlies, and DEP NEXRAD paths.
- Real-Redis tests use fresh interpreters outside the global test Redis stub.
  Scenarios cover independent processes, FIFO, live occupancy, foreign tokens,
  policy conflicts, wait timeout, Redis outage, clock disagreement, and killed
  owners. Opt-in integration tests must be run explicitly; a default suite
  that skips them cannot establish the atomic concurrency boundary.

## Validation evidence

Reviewer-run focused command:

```bash
wctl run-pytest tests/climates/gridmet/test_admission.py tests/tools/test_gridmet_admission_probe.py --maxfail=1
```

Result at that revision: **67 passed**, two existing dependency deprecation
warnings. After subsequent admission fixes, targeted reviewer reruns passed
**4 tests** for delayed acquire and in-flight renewal, then **2 tests** for
active wait snapshots and failed context-entry cleanup. The final targeted
rerun passed **11 tests** for the strengthened public-acquire timing test,
invalid context entry, unrepresentable timing values, and terminal manual
renewal failure. Counts overlap and are not an aggregate suite total.
The implementation owner additionally reports **9 real-Redis scenarios
passed** in 153.11 seconds.
Those scenarios were inspected for atomic-boundary coverage; they were not
rerun by this reviewer.

Client/propagation, full-suite, stub, deployment, and Forest evidence belongs
in the package validation and integration artifacts. QA PASS concerns code
quality and the reviewed regression coverage; it does not assert completed
deployment or Forest acceptance.

Documentation lint, spelling preview, and the final diff check passed.

## Residual debt and non-blocking follow-ups

- The Lua protocol returns a positional tuple. Its decoding is centralized,
  and real-Redis tests exercise the actual script; keep additions to the tuple
  adjacent to its decoder and snapshot fields to avoid maintenance drift.
- The observe-only report available during review had no changed-file delta
  and no Python cyclomatic complexity data. The executor will refresh it after
  the candidate commit; manual cohesion/readability review supplies the
  current quality assessment.
- Probe sampling proves observed live-permit occupancy, with container and
  FIFO evidence recorded separately from remote transport behavior. It does
  not prove a hard upstream socket ceiling under suspension or partition.
- No new dependency, generalized Redis framework, or unrelated refactor is
  needed. Future protocol changes should extend focused failure and process
  tests before expanding abstractions.
