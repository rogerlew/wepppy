# SURF-03 Contract Evidence Matrix

| Boundary | Contract | Executable evidence | Result |
| --- | --- | --- | --- |
| Authorized render | Exact run/config and server-owned list, mutation, project, and script URLs | Actual hostile-value render plus archive-dashboard route tests | Conforms |
| List/download | Metadata renders as text; downloads use the server URL | Direct populated/hostile real-client Jest | Conforms |
| Create | Comment is limited to 40 characters and one accepted job becomes active | Direct real-client Jest plus rq-engine archive-route tests | Conforms |
| Restore/delete | Explicit confirmation and exact listed archive name | Direct accept/decline real-client Jest plus API validation tests | Conforms |
| Mutation exclusion | Create, restore, and delete are mutually disabled during a mutation request or active archive/restore job | Direct pending-delete and active-job Jest; production client repaired | Conforms |
| Repeat execution | One create owner per console | Direct repeated-import Jest | Conforms |
| Status lifecycle | Archive channel, authoritative terminal refresh, visible failure, and restored-project link | Direct poll success/failure Jest plus route and worker tests | Conforms |
| API/enqueue | Authorized exact run, renewable session auth, stale/active-job handling, validated archive name | RQ-engine archive-route tests | Conforms |
| Worker/filesystem | Confined paths, integrity and disk checks, lock/cache safeguards, and failure triggers | Archive RQ and helper tests | Conforms |

## Finding and Repair

Restore and delete submissions did not initially disable every sibling mutation
control. A user could therefore initiate a conflicting create, restore, or
delete request before the first response established the shared active job.
The client now disables all mutation controls for either submission and
restores availability only when no active job remains. Source and served assets
are byte-identical.

The pending two-file RQ graph metadata cleanup predates SURF-03 and is excluded
from this package's change and evidence counts.
