# Active CLI runtime acceptance

2026-09-17 UTC. Development forest stack; normal authenticated browser/session
and default RQ queue. Runtime repair commit `2b00c4165`, contract ancestor
`567eacf7d`. No climate rebuild or scientific parameter change.

## Result

| Acceptance | Job | Outcome |
| --- | --- | --- |
| Disposable unchanged CLI, real WEPP materializer overlap | `fa299be5-45b0-448b-b1d1-718445c1529a` | Finished; report current after reload; five attachments verified. |
| Disposable equal-size changed bytes, restored mtime | `5bff6acb-16ad-4252-aeae-f3668c4e3509` | Superseded; previous accepted result retained. Original CLI restored afterward. |
| Named `thespian-cleanness` recovery | `0fd409ce-8e3c-480a-af2c-8a5fd571c7f8` | Finished; accepted `0c7899f7ac6f464e80e3f873a4c75fe1`; report current after reload and five attachments verified. |

The named source CLI SHA-256 remains
`884cb1660dc22d413d77547860fdbd0af2f50459eb8b3558ed3cf442dc3f1f9f`.
Its size, mtime and ctime still match the incident's current CLI. The accepted
snapshot records `ObservedPRISM`; this is the existing observed-climate owner
identity, not a climate-mode change made by this repair.

## Actual overlap and integrity boundary

A full independent 6,840,257,872-byte project copy was used at
`/wc1/runs/qa/qa-active-cli-20260917`. All 3,988 named-source files were rehashed
unchanged after copying and inspecting the clone, before named recovery.
The same `copy_input_file` implementation used by WEPP created, removed and
rematerialized `wepp/runs/pw0.cli` while native M3 predictors were running.
This is actual filesystem materializer overlap, not a second full WEPP simulation.
`live_overlap_identity.json` retains original integer nanosecond records and
proves accepted admission metadata/hash matched the pre-intervention CLI.
The mutation happened between RQ start and finish; only ctime changed.

The negative run changed one numeric byte with identical size and restored
mtime after predictor preparation started. `live_negative_identity.json`
retains changed/restored hashes, terminal status and the error trace. It did not
replace the successful overlap attempt. This exercises real stale-source refusal,
not a forced exception or mocked worker.

## Runtime parity and observability

`pre_restart_final.json`, `restart_workers.log`, `restart_web.log` and
`post_restart.json` record idle queues, restarted rq-engine/rq-worker/weppcloud,
actual worker UID 1000/GID 993/groups [993], umask 022 and existing mounts.
`runtime_code_identity.json` pins executing source bytes. A fresh coherent hash
of the 1,151,532-byte CLI took 0.00948 seconds on this worker.

Browser evidence under `browser/` records normal login, Run submission, RQ terminal
status, page reload and attachment hashes. `browser_*_records.log` additionally
verifies HTTP 200 for original/negative failure directories, status, error logs
and accepted results. Earlier successful and failed named attempts remain in
place. Canonical archive/restore regression passes in `archive_regression.log`.
No new production artifact format, storage layout or archive exclusion was added.

## Retained validation friction

The first disposable enqueue correctly rejected inherited source job associations.
The existing canonical `_reset_forked_run_job_markers` was applied only to the
copy before retry; see `runtime_reset_markers.json`. This acceptance copy needed both the existing copy and reset helpers.

Two named Run submissions received transient `job_active` before the route body
ran. Browser tracing showed recorder/startup POST activity sharing run admission.
Waiting for page mutations to settle allowed the same Run button to succeed.
No lock was deleted and no recorder/user preference was changed deliberately.
The existing selection controller already retries this specific pre-admission
response; equivalent Run handling is a separate small UX follow-up, not part of
this CLI-identity repair. Failed browser attempts remain separately named.

Focused validation: 153 tests passed; canonical archive case passed. Full-suite
completion and final reviewer evidence are recorded in the tracker at closeout.

Code-quality telemetry records the production module growing from 732 to 760
source lines for one bounded comparator; longest production function is unchanged.
The existing M1 end-to-end test grows from 111 to 144 lines to reuse its native
upload/Kf setup for three guard stages. These observe-only yellow bands are
accepted for this incident repair; separating helpers solely to change metrics
would expand its scope. See `code_quality_final.md`; changed broad-exception
enforcement passes with no added broad handlers.


## Final conformance and recovery

Commit `1003fe9ad` retains hashless legacy identity through preparation and rejects
malformed snapshot containers through the existing failure contract. Review found
and closed both issues. The legacy baseline fails before its fix; 21 targeted
preparation cases pass afterward. Final combined code passes 107 boundary cases
and two additional native hashless preparation/execution cases.

The full suite started on the main repair and completed with 8,971 passed and
99 skipped in 1,401.59 seconds. The later narrow conformance corrections are
validated by the final targeted suites above; the full suite was not restarted
for those deltas. Intermediate fixture and timestamp-quantum failures are retained.
Timestamp-race tests now force observable generation changes instead of assuming
adjacent link operations receive distinct timestamps.

After final service restarts, the actual Run button completed final job
`0c3bb451-0e7a-4814-95f5-3f1d2f219d49`, accepted attempt
`8190121c8a4b45e1952861e74d909693`, at 2026-09-17 19:13:55 UTC. The report remains
current after reload; all five attachments pass. The accepted engine fingerprints
match final source files exactly, while all admitted scientific source hashes
match the original failed attempt. See `named_recovery_identity_final.json`,
`runtime_code_identity_final.json`, `browser_named_final.log` and
`browser_named_final_records.log`. Initial acceptance evidence remains unchanged.
