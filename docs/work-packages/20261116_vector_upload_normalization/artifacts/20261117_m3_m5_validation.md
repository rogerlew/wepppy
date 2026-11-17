# M3-M5 workflow validation and rollout preparation

## Candidate and exact image

- Workflow ancestor: `9ac7cb8f6`; the exact tested successor is named by the
  final review artifacts.
- Shape-converter: `wepppy/shape-converter:vector-upload-m2-final5`, image ID
  `sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`.
- Final4 is disqualified because its claimed source revision does not exist.
- Publication and deployment: not performed.

## Direct validation

The task checkout was staged under `/tmp/vun-candidate` in the existing
`weppcloud` development container after the canonical wrapper correctly refused
the shared-checkout mount. This preserved the container's production-equivalent
identity, `/wc1`, secrets and Redis wiring while making the candidate source
unambiguous.

- Readiness, normalization, Omni, AgFields, Batch, archive/restore, project
  deletion, Roads and structural UI suite: 480 passed, 5 skipped.
- Earlier consolidated Roads, AgFields, Batch, browse, Files API and normalizer
  suite: 282 passed.
- Earlier browse regression suite: 345 passed; one unrelated configured-host
  D-Tale redirect assertion failed and is not counted green.
- Structural accessibility suite: 286 passed.
- Frontend Jest: 74 passed; ESLint passed.
- Freeze-preparation focused successor suite: 384 passed, 4 skipped. It includes
  renewable-lease fault injection, destructive global/project lock ordering,
  Omni/Batch/AgFields concurrency rollback, and signed-session provenance.

The exact final5 image ran on the isolated converter network. The common-helper
integration module passed 5 tests and read back source SHA-256, terminal receipt,
canonical geometry and properties. Separate actual HTTP receiving-boundary tests
then exercised Roads, AgFields, Omni run, Omni dry-run and Batch for semantically
equivalent GeoJSON, Shapefile ZIP, `.parquet`, and `.geoparquet` input. Those
five boundaries parsed their canonical workflow resource and compared property
equality plus Shapely geometry equality; the boundary selection passed 5 tests.
An additional real-controller suite passed 16 cases: four formats each for
Roads segment preparation, AgFields rotation-Parquet reload, Batch target
watershed artifact readback, and Omni status-report generation.
The shape-converter suite passed 315 tests while bound to the parser binaries
and sidecars copied from this exact image. The corrected final5 qualification,
fresh SBOM/scan and source-manifest proof are retained in
`20261117_m2_final5_qualification.md`.

## Failure and recovery evidence

- Receiving validation rejects unsupported geometry before replacement.
- Roads and AgFields keep their rollback snapshot through receipt commit; injected
  commit failure preserves prior canonical bytes and persisted controller state
  after detached reload. Omni build failure and Batch replacement failure preserve
  their prior accepted resource.
- Accepted publication is monotonic when Redis commit fails; accounting remains
  pending for reconciliation rather than becoming a false rejection.
- Eight real Redis reservations exhaust admission; stale reconciliation releases
  proven pre-write reservations and restores admission.
- Reconciliation blocks new reservations, renews and checks its owner token before
  every mutation, never parses retained payloads, and can rebuild global/principal
  totals from terminal receipts after Redis loss or project deletion. A real Redis
  lock-theft test proves it stops before receipt/counter mutation. Dry-run is the
  default.
- Destructive project/private-archive deletion and private restore now persist a
  deterministic filesystem and Redis rebuild obligation before mutation. New
  reservations and activation readiness fail closed until the exact-root rebuild
  is read back and the obligation is cleared. Retry after absence uses the same
  globally qualified identity.
- Sensitive archive creation renews the upload scope while scanning/writing,
  rejects symlinks, publishes only below `archives/private`, records SHA-256/mode
  metadata and verified actor provenance, and restores original/candidate/receipt
  bytes without making them public. Owner/root HTTP restore/delete and non-owner
  denial are covered. Whole-project deletion holds the same scope and rebuilds
  the ledger only after durable directory removal.
- Raw and resolved sensitive aliases are hidden and denied by browse and Files
  API paths.
- Signed Flask session cookies mint session-scoped JWTs through the actual auth
  decoder and run binding. Accepted and hostile receipts retain only the verified
  numeric human identity; quarantine events omit session IDs, email, roles, raw
  claims, and client IP. A signed non-owner session is denied token issuance.
- Unexpected terminal receipt/accounting failures stop renewable scope leases.
  Project deletion releases global maintenance if project-scope acquisition
  fails, and incoming-sensitive restore proves global-before-project ordering.

## Activation and recovery

Run `tools/check_vector_upload_readiness.py` under each production web/rq-engine
identity. It verifies the stable filesystem ID and shared root, mount/private
scratch posture, Redis authority/totals and, when binary admission is enabled,
exact converter readiness/provenance. Run
`tools/reconcile_vector_upload_retention.py --filesystem-root <root>` first in
audit mode. Resolve blocked/corrupt/nonterminal items; use `--apply` only under
operator change control. Use `--rebuild-ledger` after Redis recovery or project
deletion. Never edit counters manually or delete partial attempt contents.

`VECTOR_UPLOAD_BINARY_ENABLED=false` is the immediate binary disable. Browsers
advertise only GeoJSON and the server rejects ZIP/Parquet before converter work;
direct GeoJSON remains available. Application rollback uses the prior immutable
WEPPpy revision and converter image, followed by receipt, accepted-resource and
downstream artifact readback.

Production rollout requires separate authorization and must prove the same
canaries under real identities, mounts, Redis and Caddy/internal networks.
Use a minimum 60-minute observation window after the last production canary.
Disable binary admission immediately for any provenance/readiness mismatch,
public sensitive-path exposure, receipt/resource mismatch, nonzero ledger audit
drift, or stale reservation older than 15 minutes. Also disable when vector-upload
5xx/507 responses exceed 1% over any rolling five-minute window, converter
saturation persists for five consecutive minutes, or free space falls below the
configured 1 GiB reserve plus 5 GiB operating margin. Read back one direct
GeoJSON canary after disable; failure escalates to application rollback. Observe
ledger totals, `vector_upload_security_event_v1`, converter timeouts, free space
and private archive growth throughout the window.
