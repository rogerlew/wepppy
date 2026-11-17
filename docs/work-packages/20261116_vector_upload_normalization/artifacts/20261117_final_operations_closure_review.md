# Final operations closure review

Date: 2026-11-17
Reviewer: independent `ops_security_control_agent` (`final_ops_review`)
Source revision: `061253c55a2a0e1cc8952143ebdf47cc40357a18`
Source tree: `41162419f05d4303873470ccd6d97501923f3760`
Exact local image: `wepppy/shape-converter:vector-upload-m2-final4`
Exact image ID:
`sha256:ec801ab0c90e595dcc1a4f58b9be52398b8073a75a72591c34149b543a73ce03`
Verdict: **REJECT M5/local receiver activation; two High and two Medium
findings remain. Continue local remediation only.**

## Review boundary

This review supersedes the operations re-review of revision `4654150c9`. It
reviews the exact committed revision and image above. Concurrent working-tree
changes appeared while the review was running, so source claims were checked
against committed blobs with `git show 061253c55:<path>`; uncommitted changes
receive no credit. This review did not modify runtime code, Redis, the shared
checkout, registry state or any production host.

Read-only inspection confirmed the local image ID and extracted parser sidecar.
The retained image archive has SHA-256
`852b13e502bf0fb913d94c9973cb43b71a4eaf54f0da118dee1cb156eab69a25`.
The final4 supply-chain artifacts parse successfully and their retained hashes
match direct readback:

- SPDX 2.3 JSON:
  `08ca9f99d6adcb94e1308e10233c0de81b8c5371ff8e35c8c5327305dff86860`;
- Grype JSON:
  `ea3f87b8a648ca036f7ca1e3055463c692423170fe335706e384d40a1a0fd556`.

The scan records 59 High, 70 Medium, 17 Low, 50 Negligible and 16 Unknown
matches. The retained qualification maps those unchanged matches to the final3
reachability and fix dispositions. This review found no new vulnerability
disposition that reopens the isolated hostile-input boundary, but final4's
source-revision claim is not authentic and therefore blocks qualification as an
exact release candidate. See `VUN-FINAL-OPS-CR-03`.

Production image publication, remote-host integration and deployment are
explicitly excluded actions. Their missing evidence is recorded as a later gate,
not treated as a failed local test and not authorized by this review.

## Closure assessment

| Control area | Disposition | Evidence and remaining gap |
| --- | --- | --- |
| Readiness identity and provenance | **Partially closed** | `check_vector_upload_readiness.py:18-80` fails closed on a missing filesystem ID/root, non-mount root, non-private scratch mode, unavailable Redis, an uninitialized ledger, malformed converter readiness, missing expected identities or binary/lock/revision mismatch. Web and rq-engine receive the same variables in production Compose (`docker-compose.prod.yml:141-147, 587-593`). The exact final4 image nevertheless reports a nonexistent source revision. See `CR-03`. |
| Redis initialization and reconciliation authority | **Partially closed** | Reservation Lua now requires `initialized=1`; a rebuild writes that marker (`vector_upload_normalization.py:128-145, 573-585`). Reconciliation renews its owner token during inventory and conditions the terminal transaction on the token (`:383-403, 479-489, 498-506, 555-586`). A real-Redis lock-theft test proves mutation stops after ownership loss. The function still accepts a descendant root for a global ledger rebuild. See `CR-01`. |
| Observation and disable thresholds | **Locally accepted** | The rollout material defines a minimum 60-minute post-canary window and immediate disable triggers for provenance mismatch, public evidence exposure, receipt/resource mismatch, ledger drift, reservations older than 15 minutes, vector-upload 5xx/507 above 1% over five minutes, sustained converter saturation and low free space (`20261117_m3_m5_validation.md:78-89`). `VECTOR_UPLOAD_BINARY_ENABLED=false` removes binary UI/server admission while leaving direct GeoJSON available. Production dashboards/queries and measured baselines remain a deployment gate. |
| Publication monotonicity and crash recovery | **Partially closed** | Roads and AgFields hold rollback snapshots through synchronous receipt commit, and accepted publication remains accepted when only Redis accounting fails (`roads.py:1163-1241`; `ag_fields.py:289-349`; `vector_upload_normalization.py:1231-1263`). Process death between authoritative replacement and receipt commit is still not recoverable from workflow authority. See `CR-02`. |
| Private archive confidentiality and access | **Closed for the normal path** | Sensitive archives are created only below mode-`0700` private bundles, regular ZIP/sidecar/receipt files are mode `0600`, symlinks are rejected, hashes and minimized actor provenance are retained, and archive creation holds a renewable project scope (`project_rq_archive.py:385-535`). Owner/root-only list, download, restore and delete paths validate canonical nested paths and sidecar/receipt/hash agreement (`fork_archive_routes.py:536-552, 623-697, 1627-1666, 1741-1813`). Browse/Files paths retain sensitive-path denial. Failure/retry accounting is not closed; see `CR-04`. |
| Project deletion and counter rebuild | **Partially closed** | Whole-project deletion holds the run scope and invokes a global committed-only rebuild after the directory is absent (`project_rq_delete.py:116-181`). Private archive delete removes the whole bundle and requests the same rebuild. A rebuild failure after irreversible deletion is not durably recoverable or idempotent. See `CR-04`. |
| Compose networking and runtime containment | **Locally accepted** | Resolved production Compose keeps binary admission off by default, routes web/rq-engine through Caddy, keeps the converter on its isolated internal network, and retains non-root, read-only, no-new-privileges, capability-drop, PID/CPU/memory and bounded scratch controls (`docker-compose.prod.yml:141-147, 476-507, 587-593`). The default generic image tag and blank production identities are fail-closed placeholders until a separately authorized deployment pins a registry digest. |
| Recovery commands and rollback | **Partially closed** | The bounded reconciliation command defaults to audit mode and requires explicit `--apply`; the runbook forbids partial evidence deletion and manual counter edits. Binary disable and application rollback include accepted resource and downstream artifact readback. Initial or recovered-ledger bootstrap must use the exact configured root and must not be allowed to rebuild from a subtree; that authority defect is `CR-01`. |

## Open High and Medium findings

| ID | Severity | Finding | Exact closure required |
| --- | --- | --- | --- |
| VUN-FINAL-OPS-CR-01 | High | **A descendant filesystem root can replace the global Redis ledger with a subtree total.** `reconcile_retention()` proves only `root.relative_to(configured_root)` (`vector_upload_normalization.py:357-376`). Yet it scans the global reservation namespace and, when no active/unverifiable item remains, deletes every global total/principal hash and writes totals computed only below the supplied `root` (`:494-586`). An operator or internal caller can therefore pass one project/run subtree, set `initialized=1`, and silently undercount evidence elsewhere. Readiness then accepts the initialized but incomplete global authority. The new project/private-delete callers happen to pass the configured root; that does not constrain the public recovery function or CLI. | Require exact canonical equality between `filesystem_root` and `VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT` for every global audit/rebuild, before lock acquisition or inventory. Keep project paths only as evidence discovered below that root. Add a test that supplies a valid descendant containing terminal receipts and proves audit/apply/rebuild fail before any receipt or Redis mutation. Retain a real-Redis test with receipts in two projects proving a full-root rebuild preserves the combined global and per-principal totals and initialized marker. Update the recovery command to show the exact configured root and require zero blocked items plus totals readback before readiness. |
| VUN-FINAL-OPS-CR-02 | High | **Process-death recovery still cannot prove or roll back authoritative workflow publication.** Preparation durably records `status=prepared` before mutation (`vector_upload_normalization.py:1452-1459`). Roads and AgFields can roll back ordinary Python exceptions while their process is alive, but SIGKILL after canonical/NoDb replacement and before `publication_commit()` leaves new authoritative state, a prepared receipt and retained backup files (`roads.py:1198-1241`; `ag_fields.py:316-349`). Omni and Batch have equivalent mutation-to-receipt gaps. Reconciliation examines only canonical size/SHA for receipts already labeled accepted; every nonterminal prepared/source state becomes `incomplete`, without consulting controller/NoDb state, workflow backups, semantic reload or downstream artifacts (`vector_upload_normalization.py:457-487`). This violates the contract's required authoritative recovery and can leave a new accepted resource paired with an indefinitely uncertain receipt. | Add a durable per-workflow recovery journal/adapter under the same project scope for Roads, AgFields, Omni run/dry-run and Batch. For stale prepared/source-stored publication intent, compare exact canonical bytes, detached authoritative controller/NoDb state and required downstream artifact readback. Atomically mark `accepted_recovered` only when all authorities agree; otherwise restore the prior snapshot when unambiguous or retain `incomplete` without deleting evidence. Inject real process termination at pre-mutation, post-canonical-replace, post-state-persist and pre/post-receipt-commit points for all workflows; start a fresh process and prove prior rollback or semantic accepted reload plus downstream artifact correctness. File existence, canonical hash and successful jobs are not sufficient. |
| VUN-FINAL-OPS-CR-03 | Medium | **Final4 carries a syntactically valid but nonexistent source revision, so readiness can authenticate false provenance.** The qualification and exact image sidecar claim `e172f9f8a11bd43e8471b96323add18af1559516`. `git cat-file` cannot resolve that object. The reviewed source revision is `e172f9f8a23c10774f87828181048c72188ba78a`, and all seven GeoParquet source hashes in the exact image sidecar match that commit byte-for-byte, including Cargo.lock SHA-256 `ce923427...748f13`. The release build gate checks only that the supplied value is 40 lowercase hexadecimal characters (`Dockerfile.shape-converter:26-30`), and readiness compares only the operator-provided string to the same sidecar string. Thus a matching expected value does not establish repository provenance. | Rebuild a new exact image from a clean, named commit and pass that real commit ID as `SHAPE_PARSER_SOURCE_REVISION`. Reject release provenance unless the revision is resolved and the sidecar source manifest matches files extracted from that commit. Read back health and both parser sidecars from the exact image; rerun exact-image unit/integration and all five real receiving-boundary equivalence tests; generate a new SBOM and fresh vulnerability scan; retain image archive hash-to-image-ID mapping. Configure readiness with the real revision and prove one-character mismatch fails. Final4 must not be published under its current provenance claim. |
| VUN-FINAL-OPS-CR-04 | Medium | **Evidence deletion can succeed irreversibly while counter repair fails, and retry then skips repair.** Private archive deletion removes the whole bundle under the project scope, releases that scope, and only then performs a global rebuild (`fork_archive_routes.py:1797-1813`). If rebuild blocks or Redis fails, the API returns 500 after deletion; retry returns 404 before reconciliation. Project deletion similarly removes the directory and then rebuilds (`project_rq_delete.py:127-181`); a rebuild exception prevents later cleanup, while a retry that finds the directory absent skips reconciliation. Tests cover successful ordering but not failure/retry. The contract also requires a root operator to inventory/export/delete a whole terminal attempt with an explicit audit (`vector-upload-normalization-contract.md:257-265`), but the only operator command audits/reconciles counters and cannot perform that lifecycle (`reconcile_vector_upload_retention.py:13-34`). These paths conservatively overcharge rather than expose bytes, but can permanently exhaust admission and leave no durable proof of the deletion/rebuild obligation. | Persist a private deletion receipt/tombstone and `rebuild_pending` obligation before irreversible removal, fsync the parent after whole-bundle/project deletion, and make every retry reconcile even when the target is already absent. Do not release the applicable authority until the deletion state is durably recorded; serialize the global rebuild and verify totals afterwards. Add root-only inventory/export/delete for one complete terminal attempt/private bundle, with hash verification and an explicit audit record; never allow partial deletion. Test Redis/rebuild failure immediately before and after removal, concurrent reservation, route retry after 404-equivalent absence, whole-project deletion retry, private restore/delete accounting, and Redis-loss rebuild. Prove eventual exact counters and preserved unrelated evidence. |

## Accepted controls and prior-finding closure

- The ledger now fails closed until a verified rebuild creates `initialized=1`.
  Reservation admission does not infer zero state from missing Redis keys.
- The reconciliation fence is renewable and owner checked during inventory,
  receipt mutation and the watched terminal ledger transaction. Symlink evidence
  blocks apply-mode rebuild rather than being counted through an alias.
- Reservation attempt paths are bound relative to the configured filesystem root,
  not a caller-selected project root.
- Private archive creation holds the same renewable run scope through scan, write
  and publication; it rechecks ownership, rejects symlinks and enforces project
  plus global retention capacity.
- Browser-originated archive and vector receipts retain minimized verified human
  provenance without cookies, session IDs, roles, raw claims or client network
  identifiers.
- Owner/root-only private archive list, verified download, restore and delete paths
  now exist. Non-owner denial and sensitive browse/Files API denial are retained.
- Production Compose supplies the same activation and expected-provenance settings
  to web and rq-engine, keeps binary admission off by default and preserves the
  Caddy/internal-network boundary.
- The local rollout document now contains a bounded observation window, numeric
  disable thresholds and a binary-only rollback that proves direct GeoJSON after
  disable before escalating to application rollback.

## Low follow-ups and later production gates

- Add a filesystem generation/epoch to the ledger bootstrap record or otherwise
  detect restoration of an old Redis snapshot whose `initialized=1` predates newer
  retained receipts. A Redis flush fails closed today; an internally consistent
  but stale restored snapshot relies on the operator rebuild procedure.
- Give each rollout threshold a named query/dashboard, owner and sampling cadence.
  Retain the query output for the full canary window. This is required before a
  production go/no-go, but no production monitoring change was authorized here.
- Record explicit deletion audit correlation and parent-directory durability in
  the operator runbook, and include private restore accounting in routine drift
  audits.
- At publication time, rerun the vulnerability scan with a fresh database, publish
  the corrected candidate by immutable registry digest, resolve production
  Compose with that digest, and verify the digest and sidecars on every target.
- Under separate deployment authorization, run readiness under both real web and
  rq-engine identities, verify the shared mount/umask/Redis/Caddy path, initialize
  or audit the ledger from the exact configured root, run all workflow canaries,
  observe for at least 60 minutes and retain disable/rollback readback.

## Control decision

Revision `061253c55` and exact image final4 are not accepted for M5 completion or
receiver activation. The correct decision is **reject**, scope-reduced to local
remediation and validation. Keep `VECTOR_UPLOAD_BINARY_ENABLED=false`; do not set
an expected final4 revision for publication, and do not treat the current
`initialized=1` marker as trustworthy if it was produced from anything other
than the exact configured filesystem root.

This decision does not claim a production failure. Publication, remote
integration and deployment were not performed and remain outside authorization.
After `CR-01` through `CR-04` close on one committed revision and a newly built
exact image with authentic source provenance, repeat independent operations and
security review. A separately authorized production rollout must then collect
the real-host parity, canary, observation, disable and recovery receipts.
