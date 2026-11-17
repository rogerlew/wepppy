# M3-M5 workflow validation and rollout preparation

## Candidate and exact image

- Workflow ancestor: `9ac7cb8f6` plus the successor commit named by the final
  review artifacts.
- Shape-converter: `wepppy/shape-converter:vector-upload-m2-final3`, image ID
  `sha256:ed4d93692add1f7cd1527ed6948353e584a213865ebcc3006b1adf84f5c62386`.
- Publication and deployment: not performed.

## Direct validation

The disposable `wepppy-dev:latest` container mounted the task checkout and used
development Redis on `wepppy-net`.

- Normalization, Omni, archive/restore and structural UI suite: 455 passed.
- Earlier consolidated Roads, AgFields, Batch, browse, Files API and normalizer
  suite: 282 passed.
- Earlier browse regression suite: 345 passed; one unrelated configured-host
  D-Tale redirect assertion failed and is not counted green.
- Structural accessibility suite: 286 passed.
- Frontend Jest: 74 passed; ESLint passed.

The exact final3 image ran on the isolated converter network. Roads, AgFields,
Omni run, Omni dry-run and Batch each accepted semantically equivalent GeoJSON,
Shapefile ZIP, `.parquet`, and `.geoparquet` input. All 20 attempts read back the
retained original SHA-256, terminal receipt, canonical geometry equality and
property equality. The integration module reports 5 passed.

## Failure and recovery evidence

- Receiving validation rejects unsupported geometry before replacement.
- Roads, AgFields, Omni and Batch retain or restore the prior canonical file and
  durable state when publication/build persistence fails.
- Accepted publication is monotonic when Redis commit fails; accounting remains
  pending for reconciliation rather than becoming a false rejection.
- Eight real Redis reservations exhaust admission; stale reconciliation releases
  proven pre-write reservations and restores admission.
- Reconciliation blocks new reservations, never parses retained payloads, and
  can rebuild global/principal totals from terminal receipts after Redis loss or
  project deletion. Dry-run is the default.
- Sensitive archive creation takes the upload scope before scanning, publishes
  only below `archives/private`, records SHA-256/mode metadata, and restores
  original/candidate/receipt bytes without making them public.
- Raw and resolved sensitive aliases are hidden and denied by browse and Files
  API paths.

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
Observe ledger totals, stale reservations, `vector_upload_security_event_v1`,
converter saturation/timeouts, HTTP 5xx/507, free space and private archive
growth. Any unexplained drift, persistent reservation, receipt/resource mismatch,
public sensitive path, or converter provenance mismatch blocks activation.
