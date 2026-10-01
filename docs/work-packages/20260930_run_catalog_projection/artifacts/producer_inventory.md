# Producer and process inventory

Candidate inventory, 2026-09-30. Static wiring is not host acceptance. No service
has been restarted or switched to catalog mode by this execution.

## Initialization

| Process | Initialization boundary | Required staged mode |
| --- | --- | --- |
| WEPPcloud web | `wepppy/weppcloud/app.py`, after SQLAlchemy construction | postgres / timestamp_only / legacy |
| rq-engine | `wepppy/microservices/rq_engine/__init__.py`, app construction | Same |
| RQ consumers, including fork/archive | `WepppyRqWorker.__init__` and forked `perform_job` | Same; catalog before sweep eligibility |
| Scheduler | `wepppy/tools/scheduler.py:main` | Same; catalog task remains explicitly disabled |
| Supported migration runner | `run_all_migrations` initialization | Explicit deployment modes; library default disabled |
| Other standalone tools/scripts | Caller may initialize the portable observer explicitly | Disabled by default; otherwise inventory and verify |

Dev, production, worker-only and dedicated wepp3 manifests declare integration
modes. Fork/archive services receive the existing PostgreSQL secret. Dedicated
wepp3 requires an explicit job-origin host; this is candidate configuration,
not authorization to deploy wepp3. Worker-only hosts must retain their configured
job-origin PostgreSQL settings. No new credential or transport is introduced.

## Mutation coverage

| Producer | Event and authority |
| --- | --- |
| Normal Ron setters/name/scenario/map | NoDb successful atomic replacement; Ron invalidates its registered projection |
| Other NoDb controllers | Successful replacement preserves SQL last-modified mirror only |
| NoDb ancillary failure after replacement | Observer still runs in `finally`; failed replacement never notifies |
| Standalone/no database | Observer absent; no deployment import, registration or SQL mutation |
| NoDb READONLY setter | Presence mutation emits readonly event without changing timestamp semantics |
| TTL `_write_payload` | Atomic replacement emits TTL event; catalog never recalculates policy |
| ORM Run registration, owner-created run, attachment/import using Run | Mapper after-insert seeds within registration transaction; rollback removes both |
| Project fork preparation | Direct READONLY cleanup plus final metadata publication hint |
| Run sync | Registration completion emits lifecycle hint after metadata is in place |
| Archive restore | Direct file publication emits lifecycle hint before ancillary cache cleanup; real ZIP/SQL regression |
| RQ migrations | Successful migration emits lifecycle hint |
| Supported migration runner | Non-dry successful run emits lifecycle hint |
| Omni scenario/contrast clone | Direct READONLY cleanup and contrast finalizer notify portable seam |
| Omni child saves | Child projection invalidated; existing parent SQL modification mirror preserved |
| Other legacy `_pups` saves | Parent timestamp mirror retained; no child metadata projected onto parent |
| Deletion | Existing registration deletion cascades; transient source absence is not registration deletion |
| Offline edits, restored/copied trees, root movement, older nonconsumer binaries | Scheduled source reconciliation; explicit refresh after operator maintenance |

Direct SQL/bulk registration outside ORM does not emit an ORM callback; bounded
seeding finds the existing registration without inventing ownership. Every
manual file-only tool remains valid without PostgreSQL. Standalone individual
migration functions, external scripts, filesystem imports, restores and root
relocation are reconciliation producers unless their operator entry point
explicitly initializes and notifies. Do not promise their 60-second notification
target without a live mutation witness. Reconciliation does not recreate missed
historical last-modified events from old or uninitialized writers.

## Required host inventory

For each stage record host, stack/preset, process/service and revision, effective
modes, runtime UID/GID/groups/umask, approved mounts, database-origin proof,
initialization evidence and an actual file → SQL → authorized response witness.
Inventory every eligible batch consumer, including companions, independently
of hostname. Forest1 application acceptance is not companion-worker acceptance.
Old writers are permitted only as documented nonconsumers with reconciliation;
resolve separately whether workflows require their notification freshness.

Before activation, execute the connection-bound nonce protocol in canonical
section 11.1 from each eligible consumer and prove its actual source mounts.
After any relevant restart/configuration/membership change, invalidate and
repeat the affected witnesses. URI hashes and worker metadata are hints only.
