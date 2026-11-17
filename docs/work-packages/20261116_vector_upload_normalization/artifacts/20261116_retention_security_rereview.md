# Original and hostile upload retention security re-review

Date: 2026-11-16  
Reviewer: independent `retention_security_review` security reviewer  
Scope: operator-selected preservation of successful, failed and hostile vector
uploads, conversion provenance and evidence useful for later account review  
Verdict: **PASS for the M0 canonical retention checkpoint; no unresolved High or Medium findings**

## Findings

No High or Medium finding remains open in the canonical design. Runtime
implementation and M3-M5 acceptance evidence are not covered by this M0 pass.

## Closed findings

| ID | Previous severity | Closure evidence | Status |
| --- | --- | --- | --- |
| VUN-RET-SEC-01 | High | ADR-0145 caps each run/Batch scope at 50 attempts, 1 GiB sources, 1.25 GiB live attempts, 1.25 GiB private archives and 2.5 GiB combined evidence. Worst-case reservations and one 600-second project lock protect project-local admission. Cross-project capacity is separately closed by VUN-RET-SEC-06. | Closed |
| VUN-RET-SEC-02 | High | The normalization contract now requires one `authorize_sensitive_vector_artifact` decision after classification. Run access requires the current owner or root and deliberately bypasses the authenticated public-run read branch; Batch requires its existing project/group authority or root. Registered service/MCP access requires verified scope plus existing sensitive-evidence governance. Denial precedes names, stat metadata, sidecars and bytes. The upload contract, threat matrix and C24 repeat the same non-owner negative case across every browse/tool/archive surface. | Closed in contract; runtime evidence pending |
| VUN-RET-SEC-03 | Medium | Shape-converter must return the size and SHA-256 of its own complete request snapshot; the receiver transfers from its verified descriptor, rechecks identity/size and rejects a mismatch before validation, publication or an accepted receipt. | Closed in contract; runtime evidence pending |
| VUN-RET-SEC-04 | Medium | The contract uses Werkzeug `secure_filename`, a 120-ASCII-byte basename limit, no client media type, a fresh mode-0700 UUID directory, no-follow/exclusive mode-0600 files, containment/regular-file checks and flush/fsync/atomic receipt publication. Working/prepared/terminal recovery is fail-closed. | Closed in contract; runtime evidence pending |
| VUN-RET-SEC-05 | Medium | Each complete quarantined upload emits one bounded minimized security event containing verified identity, source size/hash and stable correlation fields. The contract excludes credentials, filenames, raw claims, metadata and IP, states actual log/project lifetimes and reserves account action for human-reviewed existing governance. | Closed in contract; runtime evidence pending |
| VUN-RET-SEC-06 | High | Before any attempt directory, private archive or source byte, one existing-Redis Lua admission atomically checks project, 100 GiB filesystem, 10 GiB verified-principal or 1 GiB shared-unattributed, eight in-flight and worst-case reservation bounds. The process then proves actual free space minus all reservations retains 10 GiB. Missing/mismatched filesystem identity, Redis/accounting failure or unverifiable space fails closed. Exact terminal bytes replace the reservation atomically; ambiguous crashes remain charged until receipt/file reconciliation. ADR-0145, the normalization/upload contracts, contract decision, threat matrix and C27 agree on this boundary. | Closed in contract; runtime evidence pending |

## Evidence

The proposed neutral `.upload` suffix is a useful defense against extension-based
tool selection but is not an access-control boundary. The amended contract now
requires one sensitive-root decision across generic download, HTML/JSON browse,
`aria2c.spec`, schema/representation tools and archive access, followed by one
explicit sensitive-evidence authorizer. This is the required separation from
`wepppy/microservices/rq_engine/auth.py:_authorize_user_claims`, whose ordinary
read path intentionally admits authenticated identities to public runs.

Archive creation in `wepppy/rq/project_rq_archive.py` walks all ordinary project
files and excludes only the archive output subtree and existing ephemeral
classes. This correctly preserves evidence and file modes, but the resulting ZIP
becomes another container for hostile originals. The amended private archive
root and SHA-256-bound sensitivity sidecar close the classification lifetime gap,
provided missing/mismatched sidecars fail restore and never downgrade access.

The existing authenticated actor adapters can provide canonical human account
IDs after JWT/session verification. For Flask Roads, use the authenticated active
account ID. For rq-engine routes, resolve the verified principal rather than
persisting `current_auth_actor()` session IDs or raw claims. Anonymous activity
cannot support an account ban claim. Network abuse remains operational-log scope.

The filesystem ledger is an operational quota control, not a ban or surveillance
record. Its canonical fields are limited to aggregate counters, opaque
reservation UUIDs and verified account/service identifiers. The shared
unattributed bucket deliberately avoids manufacturing an anonymous identity.
The 100 GiB filesystem and 10 GiB principal ceilings prevent project/account
multiplication; the eight-reservation and 10 GiB free-space checks close the
cross-project race before persistence. Conservative overcharging after uncertain
crashes preserves safety until operator reconciliation.

## Accepted design constraints

The review accepts these parts of the proposed direction:

- keep every complete within-limit original, including rejected bytes, instead
  of silently deleting the only user/project input;
- keep shape-converter scratch ephemeral after process-group drainage;
- use a neutral terminal suffix and never automatically retry or parse retained
  evidence;
- keep rejected normalized candidates visible but non-authoritative;
- preserve source and canonical SHA-256, parser binary provenance, stable error
  identity and verified actor identity without credentials; and
- defer any automatic ban, IP blacklist or new cross-project surveillance store.

Oversize uploads cannot produce a complete source digest or original artifact.
Deleting their partial bytes and retaining only a bounded authorized-project
receipt is correct, provided quota/free-space failures use the same cleanup and
failed-replacement guarantees. Authentication, multipart and routing failures
before a project attempt remain ordinary minimized security logs.

## Residual risk and later evidence

- Redis/ledger unavailability intentionally denies new retained uploads. That is
  a fail-closed availability cost, not a parser or quota bypass.
- An unattributed actor can exhaust the shared 1 GiB unattributed bucket and deny
  other unattributed attempts until operator recovery. The principal and global
  boundaries remain intact; no identity may be invented to avoid that tradeoff.
- Ambiguous commits can conservatively overcharge capacity until operator
  reconciliation. Recovery must never infer that absent Redis state authorizes
  bytes or automatically delete retained evidence.
- Runtime tests must still prove owner/non-owner enforcement at every named
  surface, atomic cross-project reservations, principal/global exhaustion,
  reservation recovery and byte/hash/archive readback. A contract pass is not
  runtime, image, publication or deployment acceptance.

## Checkpoint disposition

The M0 canonical retention checkpoint passes focused security re-review. The
amended contract set closes all six recorded High/Medium findings without adding
a service, queue, daemon, automatic ban or surveillance datastore. This verdict
permits the standalone contract ancestor from the retention-security perspective;
it does not certify runtime implementation. M3-M5 must still prove owner versus
authenticated non-owner public-run access, archive/restore, concurrent
cross-project quota admission, crash reconciliation and byte/hash readback before
release. Publication and deployment remain outside this verdict.
