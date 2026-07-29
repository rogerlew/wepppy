# SURF-05 Contract Evidence Matrix

| Boundary | Contract | Executable evidence | Result |
| --- | --- | --- | --- |
| Admin render | Exact defaults, channels, token, fields, booleans, and generated bundle | Route-context tests and hostile actual render | Conforms |
| Exact submit | Normalized host/run/config/root/owner/source token and native booleans | Direct real-controller Jest | Conforms |
| Submission ownership | One handler/timer and no duplicate while request/job is active | Pending-request and repeated-import Jest; client repaired | Conforms |
| Status tables | Job and migration metadata render only as text | Hostile populated-table Jest | Conforms |
| Validation/error | Run ID required; missing auth and transport failures stay visible and retryable | Direct real-controller Jest | Conforms |
| Terminal lifecycle | Polling and stream handlers are idempotent; status refreshes; link is encoded | Direct completion/failure real-controller Jest | Conforms |
| API authorization | User token requires enqueue scope and Admin role | Dashboard route and rq-engine API tests | Conforms |
| Source token | Short-lived opaque Redis key; one-time worker consumption; no status/provenance exposure | API enqueue and worker tests | Conforms |
| Queue chain | Optional migration job depends on successful sync | RQ-engine route tests and graph check | Conforms |
| Worker/output | Safe run/config components, selected-root confinement, verification, provenance, terminal events | Run Sync and migration RQ tests | Conforms |

## Finding and Repair

The initialized dashboard accepted a second form submission while the first
request was unresolved and continued to allow submission while the accepted job
was being polled. The client now owns a synchronous submission latch, disables
the submit button, rejects duplicate dispatch, requires an accepted job ID, and
restores submission only after terminal state or request failure.

The generated controller bundle was rebuilt with the repository virtualenv and
the stale-bundle test passes.
