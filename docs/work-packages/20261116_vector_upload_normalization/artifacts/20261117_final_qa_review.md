# Final M3-M5 QA review

Date: 2026-11-17
Reviewed revision: `9ac7cb8f69cf5189cc80f5493e01c08c393da204`
Disposition: **HOLD — three High and four Medium findings require closure.**

This independent QA pass reviewed the committed M3-M5 receiver integration,
tests, retained-evidence access, Compose activation, reload/failure behavior and
downstream acceptance evidence. It did not modify runtime code. Line references
below name the reviewed revision, not concurrent remediation in the worktree.

## Validation performed

- Focused normalizer, sensitive-artifact and Batch geometry tests:
  `25 passed` in 0.34 seconds.
- Roads Flask route suite: `37 passed` in 7.67 seconds.
- Changed Roads, AgFields, Omni and Batch controller Jest suites: four suites,
  `74 passed`; focused ESLint also passed.
- Direct AgFields route execution did not complete within 60 seconds in the host
  environment and produced no test result. A second exact-revision clone run for
  the changed Omni/Batch selections also stalled for more than 90 seconds and
  was interrupted. Neither run is counted as green.
- Canonical `wctl` execution from the exact-revision clone was blocked before
  test start by Docker-socket permission. This review does not count tests from
  the shared checkout or a differently mounted container.
- `docker compose ... config --quiet` passed for development. Production config
  passed when explicit test values were supplied for required host paths; the
  default local invocation failed because `WC1_DIR` expanded to an empty bind
  source. The added production vector variables are syntactically valid, and
  the blank production filesystem ID correctly leaves retention fail-closed.

The green focused tests are useful regression checks. They are not format-
equivalence or artifact-acceptance evidence because the Redis ledger, converter
and workflow controllers are predominantly replaced with fakes.

## Findings

### VUN-QA-01 — High — Retained hostile evidence can escape the sensitive-access boundary

`wepppy/microservices/browse/_download.py:516-551` authorizes a Batch request
from the caller-supplied path but does not reclassify the resolved target. Since
the Batch path permits public-run reads, an innocently named in-root symlink to
`resources/vector_upload_attempts/...` can reach a retained original or receipt
without the Batch sensitive-evidence predicate. Attachment and `nosniff`
headers at lines 554-565 do not provide authorization.

The ordinary run archive path independently walks live attempt roots into
`archives/<run>.<timestamp>.zip` (`wepppy/rq/project_rq_archive.py:303-361`).
The classifier protects `archives/private`, not those ordinary archives
(`sensitive_vectors.py:12-18`). An ordinary archive from a public run can
therefore repackage hostile originals outside the protected namespace.

The misplaced resolved-path check also changes the explicitly excluded Culvert
handler: `_download.py:476-513` calls the Batch predicate with undefined
`batch_name`, causing a 500 for a Culvert path classified as sensitive.

**Required closure:** classify and authorize the resolved Batch target before
stat/byte delivery; remove Batch-only logic from Culvert and retain a Culvert
regression test. Route-level tests must cover direct and symlink-aliased Batch
evidence for anonymous/public, ordinary authenticated, authorized member and
root callers. Archive creation must place evidence-bearing archives and their
hash-binding sidecars below the private namespace, preserve modes and quarantine
state on restore, and prove public callers cannot list, stat or download either
artifact.

### VUN-QA-02 — High — Crash recovery can permanently exhaust shared retention admission

`vector_upload_normalization.py:115-157` increments global/principal reserved
bytes and the global in-flight count, but only the per-reservation owner record
expires. Commit and release require that owner record. Once it expires after a
crash, the aggregate counters remain charged and the metadata needed to repair
them is gone. Eight abandoned reservations can permanently reach the global
in-flight ceiling.

No runtime path implements the contract's stale `receiving`, `source_stored`,
`prepared`, `accepted_recovered`, `incomplete` or corrupt-attempt reconciliation.
The normalizer tests use `_Ledger` and `_Lease` fakes
(`tests/microservices/test_vector_upload_normalization.py:24-57`) and therefore
cannot exercise Lua atomicity, TTL, contention, restart or owner loss.

**Required closure:** implement owner-safe, idempotent ledger/receipt recovery
under the project-scope lock without parsing or retrying retained files. Preserve
enough durable reservation metadata to reconcile exact descriptor-verified
bytes. Use a disposable real Redis to prove expiry before first byte, crashes at
each receipt state, wrong-owner rejection, duplicate recovery, restart and eight
abandoned attempts followed by successful admission. Retain before/after ledger,
receipt and file readback.

### VUN-QA-03 — High — Failed replacement and reload safety are not atomic

The tests prove only validation rejection before mutation or an early dummy
registration failure. They do not cover failures after workflow bytes or state
start changing:

- Roads copies `roads.uploaded.geojson` before its locked state update
  (`wepppy/nodb/mods/roads/roads.py:1156-1179`) and has no prior-file rollback.
- AgFields replaces GeoJSON and Parquet sequentially before completing its state
  mutation (`wepppy/nodb/mods/ag_fields/ag_fields.py:291-303`).
- Omni accepts/selects the prepared upload before the real contrast build or
  dry-run report completes.
- Batch backs up the resource bytes, but not a partially mutated/persisted
  `BatchRunner` state.

`PreparedVectorUpload.publish()` terminalizes a failed mutation but provides no
workflow rollback and no implemented `prepared` recovery. A rejected request
can therefore leave new accepted bytes, mixed artifacts or new in-memory/durable
state that a fresh controller later reloads.

**Required closure:** make each complete mutation reversible or recoverable
under its existing lock. Inject failures after every file replacement, state
assignment/dump, receipt fsync/replace, Redis commit and Omni build stage. After
each failure, instantiate a fresh controller/process and prove the prior file
hashes, authoritative state and parsed downstream artifacts remain selected.

### VUN-QA-04 — Medium — All-format workflow equivalence and artifact readback are absent

The committed tests cover direct GeoJSON plus only selected mocked binary
branches: mocked GeoParquet for Roads and AgFields, direct GeoJSON only for Omni
run/dry-run, and mocked ZIP for Batch. Roads/AgFields have no Shapefile boundary
test, Omni has no binary boundary test, Batch has no GeoParquet boundary test,
and `.geoparquet` alias behavior is not proved at every receiver. No test uses
the qualified converter to compare a shared semantic fixture across all formats.

The tests also do not reload real persisted workflow state and parse the next
artifact identified by the source checkpoint:

- Roads `wepp/roads/segments/roads.inslope.monotonic.geojson`;
- AgFields `rotation_schedule.parquet` and the next field artifact;
- Omni `contrasts/build_report.ndjson` for both run and dry-run; and
- Batch `dem/target_watershed.geojson`.

**Required closure:** send one semantically equivalent fixture as GeoJSON,
Shapefile ZIP, `.parquet` and `.geoparquet` through every actual browser/API
boundary using the exact qualified image. Reload each controller from durable
state and semantically parse/compare the next consumed/generated artifact.
Retain exact revision, image digest, commands, fixture hashes and results. Mocks,
successful jobs and file existence are not acceptance evidence.

### VUN-QA-05 — Medium — Shapefile converter errors are translated as service outages

`vector_upload_normalization.py:48-55,641-647` recognizes only the new normalized
codes and discards the converter HTTP status except for 408. Existing
shape-converter codes such as `invalid_archive`, `archive_path_traversal`,
`missing_required_sidecar`, `invalid_shapefile`, `invalid_source_crs`,
`unknown_source_crs`, `reprojection_failed` and `archive_quota_exceeded` are not
mapped. Consequently ordinary malformed Shapefiles and archive-cap violations
default to receiving HTTP 503 instead of the contractual 400 or 413.

A malformed successful converter GeoJSON object can also fail `_strict_json()`
at line 876 outside the converter-output translation boundary and reach the
outer 507 persistence error at lines 943-952.

**Required closure:** translate every admitted converter code/status into the
stable receiving categories without exposing raw details, and translate invalid
successful responses to converter-unavailable rather than retention failure.
Add route tests for 400 malformed/CRS failures, 413 limits, 408 timeout, 503
unavailable/saturated responses and invalid 200 bodies for every workflow
envelope.

### VUN-QA-06 — Medium — Browser-session provenance is lost in rq-engine workflows

Session tokens contain a verified human principal and positive `user_id`, but
`rq_engine/auth.py:128-152` retains only a session ID in the request-local actor.
AgFields, Omni and Batch actor conversion recognizes `user`, `service` and `mcp`,
not a signed human session. Normal browser uploads therefore produce
`{"kind":"unattributed"}` receipts and consume the shared unattributed quota
even when a canonical account ID is available. The added tests use direct user
claims and do not cover this browser path.

**Required closure:** derive a human retention actor from the already verified
session principal while continuing to exclude session IDs, roles and raw claims
from evidence. Add actual session-token route tests for AgFields, Omni run and
dry-run, and Batch, asserting receipt actor, ledger bucket and bounded security
event fields. Preserve current authentication, scope and CSRF decisions.

### VUN-QA-07 — Medium — M5 activation, recovery and documentation evidence is incomplete

At the reviewed revision the active ExecPlan and tracker still mark M3-M5 open;
there is no retained M3-M5 validation artifact or operator rollout/recovery
runbook. Production Compose intentionally leaves
`VECTOR_UPLOAD_RUN_FILESYSTEM_ID` empty, but no preflight proves one stable ID,
canonical `/wc1` root and common Redis authority across web/rq-engine identities.
There is no canary matrix, reconciliation health signal, observation duration,
danger threshold or tested binary-only disable/rollback procedure. The UI
advertises binary formats unconditionally, so stopping shape-converter leaves a
known-unavailable choice visible.

**Required closure:** after runtime findings close, update the ExecPlan's four
living sections and `tracker.md`; retain exact candidate commands/results and a
non-deploy rollout/recovery rehearsal. The runbook must cover each workflow and
format, hostile rejection, failed replacement, artifact readback, ledger and
security-event signals, immediate binary disable while direct GeoJSON remains
available, immutable application/image rollback and post-recovery verification.
Publication, remote integration and production deployment remain separate.

### VUN-QA-08 — Low — Test seams obscure production behavior and increase maintenance cost

The shared normalizer combines Redis Lua, filesystem quotas, retained-evidence
state, converter transport, geometry validation and publication in one large
module. Receiver tests then replace its ledger/lease and most workflow
controllers with local fakes. This made tests fast, but it also allowed the
converter error map, Redis expiry, late publication and Culvert/Batch integration
defects above to remain invisible.

**Non-blocking follow-up after correctness closure:** retain the small unit
tests, but add reusable real-service fixtures for Redis, the qualified converter
and fresh-controller reload. Keep recovery and error translation as named,
narrow units so fault injection does not depend on route-specific fake classes.

## QA disposition

Revision `9ac7cb8f6` is not M3-M5 acceptable and must not be activated by setting
the production filesystem ID. Re-review one committed successor after all High
and Medium findings close. The exact local converter image can remain a candidate
artifact; this verdict does not authorize image publication, remote integration
or deployment.
