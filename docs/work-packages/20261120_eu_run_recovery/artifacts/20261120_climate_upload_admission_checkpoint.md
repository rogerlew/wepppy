# Climate upload admission isolation checkpoint

Starting revision `be3ff3c8c`. The operator authorized repairs to the Climate
upload/status workflow and execution of this package. [Climate upload admission
isolation](../../../schemas/upload-endpoint-contract.md#climate-upload-admission-isolation)
specifies the bounded transport-to-worker change. The [RQ response
contract](../../../schemas/rq-response-contract.md) and [NoDb concurrency
contract](../../../schemas/nodb-persistence-concurrency-contract.md) continue
to govern admission, callbacks and locking.

The route currently writes the active filename and clears the Climate task
timestamp before checking family conflicts. A rejected same-name request can
therefore alter the previous climate or the bytes a queued job later reads.
Stage the sanitized, size-bounded file in a unique run-owned directory from
the tracked submission's admission callback. The global lifecycle and Climate
family submission guards establish admission; the filesystem staging operation
uses the normal Climate root boundary. Use a server-assigned identifier, an
exact regular-file check and existing filename restrictions in the worker.
Keep the staging root out of the active directory so a generated build cannot
erase queued bytes. Preserve ordinary authorized browsing of attempt evidence. Do not trust browser-supplied paths. A legacy in-flight
job can still read its previously submitted basename from the ordinary
Climate directory. No new route, dependency, authorization or browser
response is needed.

Normal states include no staging root, first upload, same-name replacement,
a different filename, an older queued job, and run-owned Single and Multiple
spatialization. Reject unsafe attempt tokens, traversal, symlink escape,
missing files and unsupported extensions. Bind the staging receipt to the exact run, job and basename.
Capture the assigned ID in the existing pre-conflict callback and write bytes
and receipt only in the post-conflict callback. Recover confirmed RQ commits
through existing submission recovery. Leave an uncertain preallocation or
lost-lease outcome isolated for inspection, without restoring over a possibly
newer reference. Use compatible workers before exposing the updated admission
path. Retain each failed attempt for authorized audit and retry, and remove
only the exact consumed candidate after success. Record cleanup failure
independently of a successfully applied upload. Validate before an atomic file
entry replacement and retain the active path as recorded upload provenance.
Successful validation establishes the input for publication. Rollback of
entire applied artifact generations, including PRISM revision and a failed
generated climate replacement, requires separate validation and publication
work.

Exercise both submitted names against real directories and real RQ admission.
Verify that a conflict and malformed candidate leave the active bytes and
timestamp unchanged. A pre-admission conflict keeps the prior tracked attempt;
an admitted malformed candidate reports its own worker failure. Verify ordinary
browse and archive/restore of the project-relative receipt and failed evidence. Cover existing archived root
responses, legacy worker arguments, receipt preallocation and lost-lease controls, disconnect recovery, traversal and symlink
controls, and a successful case that updates CLI, mode, and downstream
calendar. The deployment gate remains open.


## Independent review disposition

The two reviewers checked call ordering, receipt and state recovery, filesystem
containment, existing archive and browsing rules, timeout boundaries, legacy
workers, and Single and Multiple spatial modes. The ratified contract assigns a
visible project-relative attempt, binds it to the exact queued job, requires
contained nonsymlink sources and atomic replacement, and retains evidence under
an indeterminate enqueue outcome. A failed admission cannot restore over a
newer tracked reference. An admitted parse failure is still the latest job
outcome. The existing applied artifacts stay intact on pre-admission conflict
and on parse failure. The full replacement rollback remains an open obligation.

## Candidate readback

The private HTTP test used real RQ and Redis, the regular Climate worker, and
the archived event and continuous CLIs under the same `ESFANGAR.cli` filename.
An active-job conflict preserved the tracked identifier, submitted bytes and
completed Climate timestamp. The worker applied the accepted event. A later
malformed upload kept that event and its timestamp and retained its failed
candidate. The continuous replacement generated a fresh 10,957-row
`wepp_cli.parquet`; requeuing the older failed upload then left it intact.
A ZIP round trip through the archive member filters and restore collector
retained the failed input and its receipt. This was an isolated application
probe, with authorization and run discovery supplied by the fixture.

Review added a pinned checksummed file snapshot, directory-descriptor
containment, an exact worker receipt fence across both operations, and specific
handling for a timestamp or notification failure after successful application.
The focused suite covers an absent active directory, replacement of staged
bytes during application, the legacy queue signature and post-success cleanup.
Multiple still uses the existing PRISM revision path. The isolated archived
replay used Single spatial mode. The complete forest replay and
whole-generation publication recovery remain open.
