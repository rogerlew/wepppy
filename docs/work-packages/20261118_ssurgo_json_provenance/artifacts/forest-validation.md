# Forest mirror-first validation

Contract ancestor: 43c78bf95. Service runtime: 9d09f7f; full hashes, source-file hashes,
image identity and results are retained in soil-data-access/artifacts/forest.
This qualification uses the actual forest worker image, UID 1000/GID 993 and /wc1
mount, an isolated Redis/queue and the new API on wepppy-net.

## Results

- 151 focused tests passed; after review, 24 closure tests and four real
  NoDb persistence/cache-clear tests passed. These counts overlap.
- Two-module stubtest, test-stub hygiene and changed broad-exception enforcement pass.
- Broad pytest attempted: collection blocked by missing SECRET_KEY in the isolated
  test environment. No unrelated production secret or test was changed.
- Service: 36 Python tests, four Rust tests, real Compose containment/lifecycle suite.
- Official regional import: 31,841 components, 132,604 horizons, 198,812 fragments,
  233,321 textures, 10,949 restrictions and 10,945 aggregate rows.
- Independent original-file queries match exact API raw multisets for 100 Idaho
  SSURGO map units and all eight Virgin Islands STATSGO2 map units.
- Duplicate import rolls back; serving-role writes fail; readiness rejects wrong
  expected release and accepts the active release.
- Real queued builds for SSURGO 78905 and STATSGO2 1390208 (neither occurs in the
  replay caches): primary cold/warm, direct-file reference and warm fallback each
  produce 76 prepared soils. All base/prepared canonical bytes match.
- Independent readback verifies current base-soil hashes, selection/binding agreement,
  all prepared files and absence of generated soils after both-source failure.
  Cold/warm canonical hashes are retained per job; warm builds replace primary paths.
- Controlled cold XML fallback uses real verified TLS in tests. Queued fallback uses
  an independently seeded legacy cache marked historical_rows_unknown=true; it does
  not claim a successful live USDA retrieval.
- Local warm 100-MUKEY component queries (289 rows): p95 40.8 ms at concurrency one,
  48.6 ms at concurrency four, 40 requests per setting. This is regional/local
  performance evidence, not a national/public capacity claim.

## Scope and recovery

Forest soil-api and soil-db are running and healthy. Existing shared web/workers
and their source mounts/defaults remain unchanged. Exact-SHA/digest approval for
the protected Compose change is required before integration and shared-client
activation under docs/standards/integration-history-governance.md.

The release contains Idaho SSURGO and Virgin Islands STATSGO2. It relies on SDA for
other keys; an ongoing SDA outage can still fail those requests. No nationwide
coverage, full SDA compatibility, raster assignment, treatment-variant completeness
or public deployment claim is made. The earlier 501-artifact replay remains valid
under its frozen numerical environment. This new same-image comparison resolves
the bounded deployment-image question without widening canonical exclusions.

Source downloads, failed diagnostic qualification attempts and complete runtime logs
remain in ignored service data directories. No source project was modified. The
initial import was canceled when an unanalyzed COPY join plan ran slowly; adding
ANALYZE before relational checks fixed it and the previous active release survived.

## Approved activation follow-up

The operator approved the exact revision; PR #675 is merged and forest defaults
are active. See forest-activation/activation.json and live-canary.json: four actual
normal-queue jobs built/prepared both datasets, 152 final inputs match, base hashes
verify and recorded supplier is the mirror. Existing explicit selections and all
unrelated shared work are preserved. Dequeue is resumed and web/RQ/soil services
are healthy. This supersedes the pre-approval deployment status above.
