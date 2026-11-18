# Final operations and control review

Date: 2026-11-17
Reviewer: independent `ops_security_control_agent` (`final_ops_review`)
Source revision: `9ac7cb8f69cf5189cc80f5493e01c08c393da204`
Exact local image: `wepppy/shape-converter:vector-upload-m2-final3`
Exact image ID:
`sha256:ed4d93692add1f7cd1527ed6948353e584a213865ebcc3006b1adf84f5c62386`
Verdict: **REJECT activation and M5 acceptance; three High and three Medium
findings are open. Scope-reduce to local remediation and validation only.**

## Review boundary and evidence

This review covers receiver activation, shared Redis accounting, crash and
publication recovery, evidence/archive lifecycle, Compose networking,
observability, rollback and the retained-hostile-file operating path. It reviews
the committed tree named above, not concurrent uncommitted work. It does not
authorize or claim production deployment, image publication, remote integration,
account suspension or destructive evidence cleanup. No runtime code, container,
Redis state, shared checkout or production state was changed by this review.

The retained M2 evidence binds final3 to the image ID above, UID/GID `10001:10001`,
read-only root, dropped capabilities, no-new-privileges, 256-PID/1.5-GiB/1.5-CPU
limits, no volumes and the internal converter network. Direct readback reproduced
the retained evidence hashes:

- SPDX JSON:
  `00fad0f0e8c143c47f78b67f6a0706f3d64e0103e4fd8217b10130445799dffa`;
- Grype JSON:
  `a359b57d30d90cdbc9e98d06eb80f47a1aeeda281583f56f0de95eb26c163345`.

That evidence remains accepted for the isolated M2 image boundary. It does not
close receiver-side state, archive, recovery or activation defects in revision
`9ac7cb8f6`.

The production Compose topology is appropriately narrow: `weppcloud` and
`rq-engine` use `backend`, shape-converter uses only the internal
`shape-converter-sandbox`, and Caddy is the deliberate bridge between them
(`docker/docker-compose.prod.yml:56-77, 502-503, 850-890, 1064-1070`). Both
application services receive the same converter URL and run-filesystem settings
(`docker/docker-compose.prod.yml:141-143, 583-585`). The blank production default
for `VECTOR_UPLOAD_RUN_FILESYSTEM_ID` fails closed. These are sound foundations,
but there is no receiver activation preflight or recovery control that makes the
whole workflow safe to enable.

## Findings

| ID | Severity | Finding | Exact closure required |
| --- | --- | --- | --- |
| VUN-FINAL-OPS-01 | High | **Ordinary run archives can repackage sensitive attempts outside the protected path.** The archive worker recursively writes the run, including the new `vector_upload_attempts` roots, to `archives/<run>.<utc>.zip` (`wepppy/rq/project_rq_archive.py:303-361`). Revision `9ac7cb8f6` does not modify archive creation. The new classifier protects the live roots and `archives/private`, but not an ordinary archive (`wepppy/microservices/browse/sensitive_vectors.py:12-18, 32-40`). Public-run browse/download explicitly permits unauthenticated access before applying that classifier (`wepppy/microservices/browse/_download.py:349-373, 463-473`). An owner-created archive can therefore make retained originals, quarantined hostile bytes and receipts reachable as an ordinary public archive. | Before any release, make archive creation detect sensitive roots before walking bytes, acquire the same run retention lock and shared reservation, enforce archive/total/free-space quotas, publish the archive only below `archives/private/`, and atomically publish a mode-`0600` sidecar containing the archive SHA-256 and `contains_vector_upload_attempts=true`. Make list/download/restore/delete paths require owner/root and understand the private path without a public alias. Prove a public run cannot list, stat or download the archive or sidecar, while owner/root archive/restore preserves every original/candidate/receipt byte, mode and hash. Prove a restored quarantine remains inert. Do not work around this by omitting evidence from owner archives unless the canonical contract is explicitly changed. |
| VUN-FINAL-OPS-02 | High | **Reservation expiry permanently consumes shared capacity.** `_RESERVE_LUA` increments global `reserved` and `inflight` and principal `reserved`, then expires the only owner/amount/project record after 600 seconds (`vector_upload_normalization.py:115-131`). Commit and release both require that now-expired owner record (`:134-157`). There is no renewal, durable reservation index or reconciliation API. A crash or ambiguous operation therefore leaves counters charged but destroys the metadata required to recover them. Eight such expirations can permanently hit the global in-flight ceiling and reject every vector upload sharing the filesystem ID. The focused tests replace Redis with a fake ledger and never exercise Lua, TTL, restart or crash behavior (`tests/microservices/test_vector_upload_normalization.py:24-57, 94-261`). | Preserve enough durable owner/project/amount/state metadata to reconcile every uncertain charge; do not expire the only recovery record while aggregate counters remain charged. Implement idempotent owner-checked renew/finalize and a bounded operator/startup reconciliation path that reads receipts and descriptor-verified files under the project lock. It must release only proven pre-write reservations and conservatively commit evidence-bearing attempts. Add real disposable-Redis tests for expiry before first byte, crash after receiving/source storage/prepared publication, Redis restart/AOF replay, duplicate recovery, wrong owner, eight concurrent reservations and recovery from the global ceiling. Retain before/after ledger and receipt/file readback. |
| VUN-FINAL-OPS-03 | High | **Post-mutation failure can split accepted workflow state from the receipt and ledger, with no implemented recovery.** `publish()` performs the workflow mutation and canonical readback before deleting the candidate, persisting `accepted` and committing the Redis charge (`vector_upload_normalization.py:703-738`). Any exception before `published=True`, including accepted-receipt I/O, reservation ownership loss, Redis failure or lease-release failure, enters `finally` and calls `reject()` (`:739-743`). That can overwrite the receipt as `rejected` after the accepted resource changed and then attempt the same unavailable/lost ledger commit again (`:692-701`). The canonical `accepted_recovered`, stale `receiving`, `source_stored`, `prepared`, `incomplete` and `corrupt_attempt` recovery states have no implementation symbols in the committed runtime. | Implement the canonical recovery state machine under the same scope lock. Never rewrite a post-mutation uncertain attempt as an ordinary rejection. Recover `receiving`, `source_stored` and `prepared` without parsing/retrying; compare authoritative workflow state and exact canonical hashes; publish `accepted_recovered` only when unambiguous and otherwise `incomplete`. Reconcile the ledger in the same operation. Add failure injection at every receipt fsync/replace, candidate unlink, workflow mutation/readback, Redis commit and lease-release boundary for all four workflows. Acceptance requires semantic artifact and controller/reload readback, not only a receipt or successful request. |
| VUN-FINAL-OPS-04 | Medium | **Committed evidence accounting has no deletion, archive or filesystem-rebuild lifecycle.** The only committed-counter operation adds exact bytes (`vector_upload_normalization.py:134-145`). No runtime outside that module knows the `vector-upload-retention` ledger keys. `_tree_stats()` sees only caller-supplied live attempt roots and does not count private archives (`:433-452, 786-790`). There is no whole-attempt/private-archive export-delete command, post-durable-removal decrement, project-deletion reconciliation, or rebuild after Redis loss. Consequently authorized deletion cannot restore quota, project creation/deletion can leave permanent charges, and a rebuilt/rolled-back Redis ledger can disagree with retained bytes. | Add an audited owner-checked operator inventory/export/delete/reconcile command. Under the same project lock, it must verify terminal receipts, regular files, sidecars and hashes; durably remove only the entire attempt/private archive; then atomically decrement filesystem and actor committed counters. Add a read-only audit mode and fail closed on ledger/filesystem drift. Include private archive bytes in per-project and shared totals. Test deletion failure before and after durable removal, idempotent retry, whole-project removal, Redis loss/restore and cross-project concurrent reconciliation without quota undercount. Document recovery without suggesting manual Redis counter edits or partial artifact deletion. |
| VUN-FINAL-OPS-05 | Medium | **Authenticated browser sessions lose human provenance and principal quota attribution.** Session JWTs contain a server-signed `feature_access_principal` and, for signed-in users, `user_id` (`session_routes.py:1088-1105`). `_sanitize_auth_actor()` deliberately reduces session actors to `token_class` plus session ID (`auth.py:128-152`). AgFields and Omni then accept only `user`, `service` and `mcp` actor classes (`ag_fields_routes.py:173-187`; `omni_routes.py:209-223`), while Batch applies the same class switch directly to claims and ignores session `user_id` (`upload_batch_runner_routes.py:131-144`). Normal signed-in browser uploads in these workflows therefore become `unattributed`, share the 1-GiB bucket and cannot be correlated to the verified account for abuse review. Roads' direct Flask user path does not have this specific defect. | Derive `RetentionActor` from the already-verified canonical principal, including the signed session principal, without persisting session IDs, roles or raw claims. Record only positive canonical human account ID or bounded registered service/MCP subject. Add route-level tests for signed-in session, anonymous session, user, service and MCP identities across AgFields, Omni run/dry-run and Batch, and assert both receipt actor and ledger bucket. Preserve current authentication, scope and CSRF decisions. |
| VUN-FINAL-OPS-06 | Medium | **Activation, observability and disable/rollback controls are incomplete.** Production's blank filesystem ID is a useful stop, but no deploy/preflight code verifies one stable ID against the same `/wc1` mount and Redis authority on every web/rq-engine instance; no receiver canary exercises all workflows and reads back accepted/rejected artifacts; and no health surface reports ledger totals, stale attempts or reconciliation need. The UI unconditionally advertises binary extensions (`roads_pure.htm:55`, `ag_fields_pure.htm:137`, `omni_contrasts_pure.htm:214`, `batch_runner_pure.htm:181`). Stopping shape-converter preserves direct GeoJSON server handling but leaves binary admission visible; clearing the filesystem ID disables GeoJSON too. `scripts/deploy-production.sh` has converter-image checks but no receiver `VECTOR_UPLOAD_*` activation gate. | Add an operator-owned activation/preflight and rollout/recovery runbook. It must verify exact final3 provenance/readiness body, stable shared filesystem ID and canonical root on every participating service, common Redis ledger authority, writable/private modes under the production identity, Caddy bridge/internal converter network, quotas and clean initial reconciliation. Name canaries for Roads, AgFields, Omni run/dry-run and Batch in all supported formats, including rejected-hostile and failed-replacement cases, with semantic downstream readback. Define observation duration, ledger/security-event signals and danger thresholds. Provide an immediate binary UI/server admission disable that leaves direct GeoJSON working, plus immutable-image/application rollback and post-recovery readback. Exercise this locally without publishing or deploying; production-host proof remains separately authorized. |

## Low findings and retained gates

| ID | Severity | Finding | Required closure |
| --- | --- | --- | --- |
| VUN-FINAL-OPS-07 | Low | The bounded `vector_upload_security_event_v1` is useful and excludes filenames/tokens/sessions/IP, but it contains only attempt/project/workflow/actor/source/error-code/stage (`vector_upload_normalization.py:586-603`). It omits the contract's stable request/correlation ID, and no operator query/alert or evidence-preservation procedure was found. This weakens incident correlation even after actor attribution is repaired. | Add the existing sanitized correlation/error ID to the receipt and event, document the log query and retention boundary, and include one accepted and one quarantined event in the rollout receipt. Do not add raw file content, client IP, tokens, roles or a new permanent ban store. |
| VUN-FINAL-OPS-08 | Low | Final3 is a locally qualified image only. The retained M2 review appropriately requires a fresh publication-time vulnerability scan and production-host parity/recovery receipt. No registry digest, publication or deployed identity exists, and none was authorized here. | Preserve the local image/SBOM/scan identity as candidate evidence. At separately authorized publication/rollout, repeat the scan, pin the registry digest, resolve production Compose, and record real identities, mounts, networks, limits, readiness body, workflow canaries and rollback. This gate cannot be closed by local Docker success alone. |

## Positive controls retained

- Missing production `VECTOR_UPLOAD_RUN_FILESYSTEM_ID` causes receiver retention
  admission to fail closed before source bytes (`vector_upload_normalization.py:
  226-244`). Do not fill it until the High/Medium findings are closed.
- Redis DB 0 uses the existing authenticated authority and production Redis is
  configured with persisted AOF/RDB state (`docker/docker-compose.prod.yml:
  892-918`). Persistence is useful but is not reconciliation and cannot repair
  the TTL/counter defect.
- Complete sources are streamed to mode-`0600` files, SHA-256-bound and stored
  below mode-`0700` attempt directories. Oversize partials are removed without a
  false complete digest. Rejected complete originals emit a bounded structured
  security event.
- The live sensitive-path classifier covers exact run/Batch attempt roots,
  normalizes aliases and makes retained `.upload` files download-only. The
  finding above concerns archive creation bypassing that otherwise useful guard.
- Shape-converter remains non-root, read-only, capability-free and isolated from
  the application network except through Caddy. No Python hostile-input parser
  fallback was found or recommended.

## Control decision and recovery posture

Revision `9ac7cb8f6` is not safe to activate. The correct control decision is
**reject**, with scope reduced to local source/image remediation and validation.
The exact final3 image may remain the immutable local parser candidate, but the
receiver must not be enabled merely by setting `VECTOR_UPLOAD_RUN_FILESYSTEM_ID`.
Do not publish the image, deploy the revision, generate evidence-containing
ordinary public archives, manually edit Redis totals, delete partial provenance,
or treat a successful job/file-existence check as acceptance.

Re-review must use one new committed revision and the exact image intended for
release. It must close every High and Medium item above with real Redis crash/
expiry/restart evidence, private archive/restore and public-denial evidence,
failure-injected publication recovery, actor attribution tests, ledger lifecycle
readback and a non-deploy rollout/rollback rehearsal. Production-host integration,
publication and deployment remain separate operator decisions after that local
control gate passes.
