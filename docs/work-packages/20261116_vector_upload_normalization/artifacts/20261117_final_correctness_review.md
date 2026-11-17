# Final M3-M5 correctness review

## Review identity and verdict

- Candidate revision: `9ac7cb8f69cf5189cc80f5493e01c08c393da204`
- Scope: M3-M5 receiving integration for Roads, AgFields, Omni run/dry-run,
  and Batch Runner
- Reviewer disposition: **HOLD**
- Unresolved findings: **2 High, 6 Medium, 1 Low**

The revision has useful pre-publication geometry checks, complete-original
SHA-256 capture, converter digest reconciliation, and narrowly scoped route
tests. It does not yet satisfy the ratified recovery, failed-replacement,
provenance, archive, or artifact-readback acceptance contracts. The two High
findings can leave admission accounting permanently wedged or leave a rejected
request with newly published workflow bytes/state.

## Findings

### High 1: expired/crashed reservations permanently consume the global in-flight limit

`wepppy/microservices/vector_upload_normalization.py:115-156` increments the
aggregate `reserved` and `inflight` counters, then gives only the per-reservation
owner key a 600-second TTL. Both finalization scripts require that live owner
key. When the key expires after a crash, `_COMMIT_LUA` and `_RELEASE_LUA` can no
longer decrement the aggregate counters. The same module has no stale-attempt or
ledger reconciliation path: `_tree_stats()` at lines 433-452 only counts files,
and `prepare_vector_upload()` at lines 753-953 never transitions stale
`receiving`, `source_stored`, or `prepared` receipts to `incomplete` or
`accepted_recovered`. In particular, the ambiguous failure branches at lines
939-947 deliberately leave reservations outstanding without any later repair
mechanism.

Impact: `_GLOBAL_INFLIGHT_LIMIT` is 8. Eight hard failures or expired attempts
can leave `inflight == 8` permanently even after every reservation owner key has
expired, rejecting all later vector uploads. Reserved byte totals also remain
inflated. This violates the canonical requirement to retain uncertain charges
only until receipt/file recovery reconciles them and to release stale receiving
reservations.

Required fix:

1. Add owner-safe reconciliation under the project-scope lock for stale
   `receiving`, `source_stored`, `prepared`, invalid-receipt, and missing-owner
   states.
2. Make reservation recovery atomically reconcile aggregate and principal
   counters exactly once, using persisted reservation identity and measured
   descriptor-verified bytes.
3. Terminalize receipts as `incomplete` or `accepted_recovered` according to the
   ratified state machine; never parse or retry their payloads during recovery.
4. Add real Redis/Lua tests for process death, owner-key expiry, restart, corrupt
   attempt directories, and eight consecutive abandoned attempts followed by a
   successful new reservation.

### High 2: publication failure is not atomic with workflow bytes/state

`PreparedVectorUpload.publish()` calls the workflow mutation before receipt
finalization (`wepppy/microservices/vector_upload_normalization.py:703-743`), but
neither it nor the routes can restore all workflow bytes and NoDb state when a
late mutation step fails. There is also no recovery implementation to resolve
the resulting `prepared` ambiguity.

Concrete paths include:

- Roads calls `roads_lifecycle.retain()`, copies the replacement to
  `roads/roads.uploaded.geojson`, and only then enters the NoDb persistence lock
  (`wepppy/nodb/mods/roads/roads.py:1156-1179`). A lock/dump failure can leave
  the new upload in place and prior derived state retained/invalidated while the
  HTTP request and normalization receipt are rejected. The Roads lifecycle
  failure handler does not restore `roads.uploaded.geojson`.
- AgFields replaces `fields.WGS.geojson` and `rotation_schedule.parquet` before
  the locked NoDb state update has completed
  (`wepppy/nodb/mods/ag_fields/ag_fields.py:253-303`). Failure on the second
  replace or persistence leaves a mixed or replaced accepted resource.
- Omni marks the prepared upload accepted while `_parse_inputs_with_prepared_upload()`
  returns (`wepppy/microservices/rq_engine/omni_routes.py:775-808`), before
  `build_contrasts()` or `build_contrasts_dry_run_report()` runs at lines
  1014-1025 and 1157-1168. A later build failure returns 400/500 but can leave
  the new selected path/state and an `accepted` receipt.
- Batch backs up only the resource file
  (`wepppy/microservices/rq_engine/upload_batch_runner_routes.py:262-293`).
  `BatchRunner.register_geojson()` mutates `_geojson_state` under its persistence
  lock (`wepppy/nodb/batch_runner.py:1120-1153`); a failure after assignment can
  restore the old file while leaving new in-memory or partly persisted state.
  The current failure test injects an exception before any state mutation, so it
  does not exercise this case.

Impact: a failed replacement can change the accepted source, selected input,
derived-resource consistency, or reloaded NoDb state. That is the central
failed-replacement safety invariant of this package.

Required fix: treat the complete workflow mutation and its semantic readback as
the publication boundary. Under the existing mutation lock, preserve the prior
resource and authoritative state, perform all replacements/build steps, read
back the exact downstream state, then terminalize the receipt. On failure,
restore both bytes and state, or leave a recoverable `prepared` receipt that an
implemented reconciliation path can prove as `accepted_recovered` versus
`incomplete`. Add injected failures after each file replacement, after state
assignment, during NoDb dump, and during Omni build; then construct a fresh
controller instance and prove old bytes/state/artifacts remain authoritative.

### Medium 1: receiving-validation rejection omits normalized-candidate provenance

The candidate is written and hashed at
`wepppy/microservices/vector_upload_normalization.py:888-889`, but the receipt is
not updated with `candidate_path`, `candidate_size`, `candidate_sha256`, converter
request ID, or parser provenance until after the receiving validator succeeds at
lines 897-910. If the validator rejects otherwise valid normalized output, the
outer handler writes a rejected receipt at lines 916-931 without those fields.
The candidate file remains, but an investigator cannot bind it to the receipt or
converter provenance.

This is directly contrary to the contract for normalization-success /
receiving-validation-failure attempts. Persist candidate hash/size and sanitized
converter provenance before invoking workflow validation, then transition the
receipt to rejected with an accurate receiving-validation enforcement stage.
Extend the rejection test to assert exact source, candidate, converter, and
parser hashes, not only candidate-file existence.

### Medium 2: verified browser-session users are recorded as unattributed

`_sanitize_auth_actor()` retains only `session_id` for session tokens and drops
their verified `user_id` (`wepppy/microservices/rq_engine/auth.py:128-152`).
AgFields and Omni then recognize only token class `user`, `service`, or `mcp`
(`ag_fields_routes.py:173-187`; `omni_routes.py:209-223`). Batch receives the
original session claims but similarly recognizes no session user
(`upload_batch_runner_routes.py:131-144`). A signed browser-session token with a
verified positive `user_id` therefore writes `{"kind":"unattributed"}` even
though the contract requires the canonical human account ID.

Preserve a bounded, server-verified positive user ID in the request-local actor
for authenticated sessions, while continuing to exclude session IDs from the
artifact receipt. Add tests for an owner browser session, an anonymous public
session, a direct user JWT, and service/MCP actors across the rq-engine routes.

### Medium 3: direct Omni GeoJSON working-byte reservation is under-sized

`prepare_vector_upload()` reserves `endpoint_max_bytes + 32 MiB + receipt` for
every format (`wepppy/microservices/vector_upload_normalization.py:772-779`), but
direct GeoJSON permits a candidate as large as the full endpoint maximum at lines
861-863. Omni's endpoint maximum is 100 MiB. One worst-case direct upload can
therefore retain approximately 100 MiB of original plus 100 MiB of candidate
while reserving only approximately 133 MiB. Across the eight-upload global
in-flight ceiling this understates working use by approximately 544 MiB and
weakens both free-space and shared-ledger admission.

Compute the reservation from the detected format before ledger admission:
direct GeoJSON needs the endpoint-sized source and candidate allowances; binary
formats need the reviewed normalized-output ceiling. Test exact reservation
amounts and concurrent free-space/accounting behavior for each format.

### Medium 4: M3-M5 format-equivalence, reload, and downstream artifact acceptance is absent

The added route tests do not meet the ExecPlan's acceptance rule that mocks,
successful jobs, and file-existence checks are insufficient:

- Roads covers direct GeoJSON and a mocked GeoParquet response, but not a real
  Shapefile ZIP conversion or fresh-controller reload and Roads segment artifact
  parse (`tests/weppcloud/routes/test_roads_bp.py:374-516`).
- AgFields covers direct GeoJSON and a mocked GeoParquet response, but not a real
  Shapefile conversion, fresh NoDb reload, or semantic readback of the generated
  rotation-schedule Parquet and next downstream field artifact
  (`tests/microservices/test_rq_engine_ag_fields_routes.py:271-382`).
- Omni run/dry-run only covers direct GeoJSON with a dummy controller; no binary
  format crosses the converter, no persisted controller is reloaded, and no
  real build report/downstream artifact is parsed
  (`tests/microservices/test_rq_engine_omni_routes.py:1202-1367`).
- Batch covers direct GeoJSON and a mocked Shapefile conversion, but no real
  GeoParquet conversion, fresh `BatchRunner` reload, or generated
  `dem/target_watershed.geojson` readback
  (`tests/microservices/test_rq_engine_upload_batch_runner_routes.py:143-414`).

Run each of GeoJSON, Shapefile ZIP, and GeoParquet through each actual receiving
boundary with the exact candidate converter image. Reload authoritative state
from disk in a fresh process/controller and semantically parse the next consumed
or generated artifact: Roads segments, AgFields rotation schedule/field
artifacts, Omni build report, and Batch target watershed. Include failed
replacement against a real accepted resource for every workflow and format.

### Medium 5: private archive/restore preservation required by the contract is not implemented or proved

The revision adds live-path browse classification, but contains no archive
creation/restore integration for vector attempt roots, no `archives/private/`
sensitivity sidecar binding the archive SHA-256, and no mode-preservation or
restore tests. Repository search at the reviewed revision finds
`vector_upload_attempts` only in route roots and the live browse classifier; it
finds no `contains_vector_upload_attempts` archive marker.

Implement the canonical private owner archive path and sidecar under the same
retention lock/quota. Prove byte-for-byte original, candidate, receipt, mode, and
quarantine-state preservation after restore; prove anonymous/non-owner denial
before archive name/stat/sidecar/bytes disclosure. A restored attempt must never
be parsed or automatically retried.

### Medium 6: terminal receipt and accepted workflow can disagree when reservation commit fails

`PreparedVectorUpload.publish()` writes `status=accepted`, removes the candidate,
and persists the receipt before it commits the Redis reservation
(`wepppy/microservices/vector_upload_normalization.py:725-737`). If the owner key
expired or Redis fails at commit, the `finally` path calls `reject()` at lines
739-743 even though the workflow mutation and accepted receipt publication have
already happened. `reject()` can then overwrite the receipt as rejected, or fail
again while leaving the workflow accepted and accounting uncertain. There is no
terminal reconciliation path to repair either outcome.

Resolve this together with High 1/High 2: define a monotonic receipt transition
and idempotent recovery protocol around workflow readback and exact-byte ledger
commit. Never downgrade a durably accepted receipt to rejected merely because
accounting finalization failed; retain it as a recoverable state until the
authoritative resource/state and reservation are reconciled.

### Low 1: Roads `.json` admission and the endpoint contract disagree

The shared normalizer admits both `.geojson` and `.json`
(`wepppy/microservices/vector_upload_normalization.py:46-47`), and Roads now uses
that shared admission. The Roads row in
`docs/schemas/upload-endpoint-contract.md` lists `.geojson`, Shapefile ZIP, and
GeoParquet but not `.json`. Either retain Roads' historical `.geojson`-only
surface or amend the endpoint contract and user help with the intentional
additional suffix. Add a route contract test for the chosen behavior.

## Validation performed

Static review compared the committed implementation and added tests against:

- `docs/schemas/vector-upload-normalization-contract.md`
- `docs/schemas/upload-endpoint-contract.md`
- M3-M5 and Validation/Acceptance in the active ExecPlan
- workflow mutation and reload implementations for Roads, AgFields, Omni, and
  Batch Runner

The canonical focused command was attempted from the task worktree:

```text
wctl --project-dir /tmp/wepppy-vector-upload-normalization run-pytest \
  tests/microservices/test_vector_upload_normalization.py -q
```

No candidate tests started: the wrapper correctly detected that the running
`weppcloud` container mounted another checkout and exited with
`WCTL_CHECKOUT_MISMATCH`. A supplemental host-venv attempt also did not collect
tests because that environment lacks `python_multipart` and cannot access the
required Redis endpoints. Neither attempt is counted as candidate validation.

## Closure criteria

Do not accept M3-M5 or proceed to rollout/publication/deployment on this
revision. Re-review a committed successor after:

1. reservation and receipt recovery is implemented and tested with real Redis;
2. all four workflows have rollback/recovery-safe publication and fresh-reload
   failure injection;
3. rejected normalized candidates retain complete digest/provenance evidence;
4. verified browser-session actors are attributed correctly;
5. per-format reservation sizing and private archive/restore are implemented;
6. exact-image, all-format, actual-boundary downstream artifact readback is
   retained for every workflow; and
7. the candidate checkout is mounted into the test container so canonical test
   results are demonstrably from the reviewed revision.
