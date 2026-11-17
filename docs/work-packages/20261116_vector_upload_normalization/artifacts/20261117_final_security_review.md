# Final security review: vector upload normalization

Date: 2026-11-17
Reviewer: independent `final_security_review` security gate
Reviewed revision: `9ac7cb8f69cf5189cc80f5493e01c08c393da204`
Verdict: **HOLD — one High and three Medium findings remain open**

## Findings

| ID | Severity | Status | Finding |
| --- | --- | --- | --- |
| SEC-FINAL-01 | High | Open | Ordinary project archives copy retained originals and receipts into a publicly downloadable ZIP. |
| SEC-FINAL-02 | Medium | Open | The Files JSON API does not reapply sensitive-path authorization to resolved symlink targets. |
| SEC-FINAL-03 | Medium | Open | Expired/crashed Redis reservations and stale receipts have no reconciliation path. |
| SEC-FINAL-04 | Medium | Open | Authenticated human session uploads are recorded as `unattributed`. |
| SEC-FINAL-05 | Low | Open | The receiving service buffers an unbounded converter HTTP response before validating it. |

### SEC-FINAL-01 — ordinary archives disclose retained upload evidence

Severity: **High**
Impact: confidentiality loss of hostile/original upload bytes, source hashes,
actor identifiers and failure diagnostics; the neutral `.upload` suffix does
not protect bytes once they are inside an ordinary ZIP.

Exploit path:

1. A complete within-limit upload is retained below one of the four
   `vector_upload_attempts` roots.
2. `wepppy/rq/project_rq_archive.py:27-64` excludes only `archives/` and three
   transaction files. The archive walk at lines 328-356 therefore copies every
   retained original, candidate and receipt into the ZIP.
3. The output is written as `archives/<runid>.<timestamp>.zip` at lines
   312-318, not below `archives/private/`, and no hash-bound sensitivity sidecar
   is created.
4. `wepppy/microservices/browse/sensitive_vectors.py:12-18` classifies only
   `archives/private`, so the resulting ordinary ZIP is treated as public
   project content. `wepppy/microservices/browse/_download.py:349-473` permits
   anonymous reads for public runs and applies the sensitive check only to the
   ZIP's ordinary path.
5. The established behavior is explicit in
   `tests/microservices/test_dedicated_download_service.py:69-88`, which expects
   an unauthenticated public-run request for `archives/result.zip` to return the
   archive bytes. The `aria2c.spec` inventory likewise includes ordinary ZIPs
   because its raw/resolved classifier at `_download.py:792-821` cannot see the
   ZIP members.

This directly contradicts the contract at
`docs/schemas/vector-upload-normalization-contract.md:279-323`, which requires
owner/root-only archive access, `archives/private/`, a mode-0600 hash-bound
sidecar and a public export that omits all sensitive roots. The earlier M0
retention review specifically identified the ordinary archive walk and made its
pass conditional on those runtime controls; revision `9ac7cb8f6` did not add
them.

Required closure:

- Apply the shared sensitive classifier during archive planning before member
  bytes are opened. A public archive must omit all four sensitive roots.
- Store any evidence-bearing owner archive under `archives/private/`; create a
  mode-0600 sidecar binding the archive SHA-256 and
  `contains_vector_upload_attempts=true`. Missing or mismatched sidecars must
  fail closed.
- Require current run owner/root authority for private run archives and existing
  Batch project/group authority for Batch evidence; ordinary public-run access
  must never inherit private-archive authority.
- Restore only after sidecar/hash verification, preserve evidence bytes and
  modes, and never parse, normalize or enqueue retained uploads during restore.
- Add readback tests that inspect ZIP members, bytes, modes and hashes, then
  prove owner/root access and anonymous plus authenticated non-owner denial
  after live attempts are present and after they are removed.

### SEC-FINAL-02 — Files API resolved-alias authorization bypass

Severity: **Medium**
Impact: an authenticated public-run non-owner can enumerate retained attempt
names, receipt/candidate names, sizes, timestamps and symlink targets through an
innocently named in-root alias. Direct download has a second resolved-path check,
so this finding does not establish raw-byte disclosure through that route.

`wepppy/microservices/browse/files_api.py:917-926` authorizes the raw request
subpath. Its symlink walk at lines 220-261 permits symlinks whose target is
inside an allowed run root. Lines 1042-1067 validate general resolved-path
containment/hidden-path policy, but never call `is_sensitive_vector_path` on the
resolved relative path. Listing exclusion at lines 602-615 and 863-875 is based
only on `sensitive_child_names(rel_path)`. Consequently, a path such as `alias`
resolving to `roads/vector_upload_attempts` has no sensitive child name and is
listed normally. Root listings can also emit the alias and its safe target at
lines 460-470 before any sensitive-target decision.

The dedicated sensitive-artifact tests cover direct names and `aria2c`/download
aliases, but do not exercise `/files/<alias>` or a sensitive symlink entry in a
Files API parent listing.

Required closure:

- Before listing, stat metadata or payload construction, classify both the raw
  path and `realpath` relative to every allowed root; require the same run
  owner/root predicate on either match.
- Omit unauthorized symlink entries whose resolved target is sensitive, rather
  than returning an alias name or target. Apply the same rule to `meta=true`.
- Add authenticated non-owner public-run tests for directory and file aliases,
  parent/group-root aliases, encoded/case variants and concurrent target
  replacement. Assert denial occurs before names or stat metadata are returned.

### SEC-FINAL-03 — Redis reservation and receipt recovery is absent

Severity: **Medium**
Impact: availability and quota-integrity failure. Crashes can permanently deny
new vector uploads; loss/reset of Redis accounting can instead undercount global
and principal evidence across projects.

The reserve script in
`wepppy/microservices/vector_upload_normalization.py:115-131` increments global
`reserved` and `inflight` and principal `reserved`, then gives only the
per-reservation hash a 600-second expiry. Commit and release at lines 134-156
require that hash and its owner. When the hash expires, the counters remain but
neither script can decrement them. After eight such failures, line 122 rejects
every later upload at the global in-flight ceiling. Conversely, a Redis data
loss/restart removes committed accounting while retained filesystem evidence
remains.

The runtime contains no stale-attempt or ledger reconciliation implementation:
there is no producer of contract statuses `accepted_recovered` or `incomplete`,
and the only reservation-prefix use is reserve/commit/release in this module.
The tests at `tests/microservices/test_vector_upload_normalization.py:24-55`
replace the ledger and lease with in-memory stubs; they do not exercise Lua,
expiry, crash points, restart, stale receipts or recovery. This falls short of
the required lifecycle at
`docs/schemas/vector-upload-normalization-contract.md:234-275`.

Required closure:

- Preserve enough owner/principal/project/amount state to reconcile after the
  600-second lease expires; do not expire the only record needed to repair the
  aggregate counters.
- Under the project scope lock, terminalize stale `receiving`, `source_stored`
  and `prepared` receipts exactly as the contract specifies, without parsing or
  retrying hostile input. Reconcile exact descriptor-verified bytes atomically
  with the aggregate ledger.
- Detect a missing/reset/corrupt filesystem-ledger epoch and fail closed until
  counters are rebuilt from bounded receipts/files; do not silently start from
  zero.
- Either renew the owner-bound scope lease during bounded work or prove and
  enforce a deadline below its TTL. Ownership loss must not permit a concurrent
  publisher.
- Test process death at every receipt state, reservation-key expiry, Redis
  restart, corrupt/missing receipt directories and eight concurrent abandoned
  reservations. Prove both recovery of availability and preservation of older
  evidence/accepted state.

### SEC-FINAL-04 — verified human sessions lose actor provenance

Severity: **Medium**
Impact: retained evidence cannot support the requested account-level abuse
review, and all ordinary session uploads share the 1 GiB `unattributed` quota
bucket. One authenticated user can exhaust that shared bucket and deny other
session users while leaving no account identifier in the security event.

Session tokens are minted with a verified `feature_access_principal` and, when
available, `user_id` at
`wepppy/microservices/rq_engine/session_routes.py:1088-1105`. However,
`wepppy/microservices/rq_engine/auth.py:147-152` sanitizes the current actor to
only `token_class=session` plus `session_id`. The AgFields and Omni adapters at
`ag_fields_routes.py:173-187` and `omni_routes.py:209-223` accept human IDs only
for `token_class=user`, so they correctly avoid persisting the forbidden session
ID but return `unattributed`. Batch receives the verified claims directly but
also rejects `token_class=session` in
`upload_batch_runner_routes.py:131-144`. Roads correctly uses the authenticated
Flask account ID.

Required closure:

- Add one server-authoritative retention-actor resolver that maps a verified
  human `feature_access_principal` (or canonical positive verified `user_id`) to
  `{kind: human, user_id: <positive id>}` for both `user` and authenticated
  `session` tokens.
- Preserve bounded registered service/MCP subjects; leave genuinely anonymous
  or unverifiable identities `unattributed`. Never persist session IDs, tokens,
  roles, raw claims, email addresses or client IP.
- Use the same resolved actor for receipts, structured security events and the
  principal quota bucket. Add route-level tests for human session, user,
  service, MCP and anonymous/unverifiable cases across AgFields, Omni run/dry-run
  and Batch.

### SEC-FINAL-05 — converter response has no receiving-side byte cap

Severity: **Low**
Impact: a compromised or badly misconfigured internal converter/proxy can make
the receiving web/RQ process buffer an arbitrarily large or indefinitely
dribbled response. The public upload does not control the converter URL, so this
is not a direct public SSRF or redirect exploit.

`wepppy/microservices/vector_upload_normalization.py:606-640` uses the trusted
environment URL and correctly sets `allow_redirects=False`, connect/read
timeouts, a verified no-follow source descriptor and source rehashing. Requests
still buffers the whole response before `response.json()`, without a response
`Content-Length`/streaming cap or absolute response deadline. The qualified
shape-converter bounds canonical output, which reduces likelihood but does not
make the receiver robust to an unhealthy trust peer.

Required hardening:

- Stream the response with an explicit maximum derived from the canonical
  GeoJSON cap plus bounded envelope overhead; reject an oversize declared or
  observed body before JSON decoding.
- Enforce an absolute wall deadline in addition to per-read timeout and continue
  to reject redirects. Retain the current exact source/canonical digest and
  provenance checks.

## Controls reviewed without a new finding

- Retained originals use a neutral `.upload` suffix, exclusive/no-follow mode-
  0600 writes, mode-0700 attempt directories, complete-source SHA-256 and
  descriptor identity verification. Oversize partials are removed and never
  receive a misleading complete digest.
- Parser dispatch is extension-gated with no permissive Python fallback.
  Accepted artifacts remain canonical `.geojson`; converter output is strictly
  decoded and then revalidated by the receiving workflow before publication.
- The converter URL is deployment configuration, not request input; redirects
  are disabled. No user-controlled SSRF path was found.
- Shape-converter starts the Rust CLI in a new session, applies CPU/address-space/
  file-size/open-file limits, drains the full process group on timeout or
  repeated cancellation, bounds and strictly validates IPC, and revalidates the
  parser binary/sidecar before emitting provenance. Source and canonical hashes
  are reconciled at the receiver.
- Roads remains behind the existing Flask authorization decorator and global
  CSRF middleware. RQ-engine routes retain their JWT scopes, run authorization
  and feature-access checks. No Culvert upload path was added.
- Direct download, HTML browse, schema, D-Tale, GDAL and `aria2c.spec` have raw
  and/or resolved sensitive-path controls. The Files API and archive container
  exceptions are the findings above.

## Validation evidence

Direct task-worktree validation used
`PYTHONPATH=/tmp/wepppy-vector-test-deps:. /workdir/wepppy/.venv/bin/pytest` and
passed 37 focused tests:

```text
tests/microservices/test_sensitive_vector_artifacts.py
tests/microservices/test_vector_upload_normalization.py
tests/shape_converter/unit/test_geoparquet_input.py
37 passed
```

The review also traced all changed upload routes, the shared classifier, browse/
download/tool surfaces, project archive creation/restoration, Redis Lua state,
session actor derivation, converter handoff/provenance, Rust process lifecycle
and relevant contract clauses. No live deployment, image publication or
production action was performed.

## Gate disposition

Revision `9ac7cb8f6` is **not security-acceptable for package closeout or
rollout**. SEC-FINAL-01 through SEC-FINAL-04 require code and regression-test
closure followed by independent security re-review. SEC-FINAL-05 is a Low
defense-in-depth item and may be tracked separately if the package owner records
that disposition. Production publication and deployment remain outside this
review.
