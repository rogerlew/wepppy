# Integrate the explicit JSON soil source with durable provenance

## Purpose


Allow operators to select the unofficial soil service for WEPPpy while retaining
which endpoint/profile/release supplied the cached data. Preserve XML by default
and scientific soil outputs. Execute against the canonical soil-data-source-provenance
contract; this is faithful integration, not a mocked transport demonstration.

## Progress


- [x] Inspect six collection consumers, legacy transport/cache and frozen service contracts.
- [x] Author operator-authorized canonical contract and data compatibility plan.
- [ ] Complete independent reviews and commit the contract ancestor.
- [ ] Implement transport, cache identity/events, base-sidecar and NoDb selection.
- [ ] Run focused/broad tests and stub checks against the candidate checkout.
- [ ] Run externally isolated fresh-cache service builds and compare generated artifacts.
- [ ] Retain review/evidence, update tracker, commit/push task branches.

## Context and plan


Worktree: /workdir/wepppy-ssurgo-json, branch task/ssurgo-json-provenance. The shared
/workdir/wepppy checkout has unrelated edits and must remain untouched. Service
repo: /workdir/soil-data-access, branch task/wepppy-json-parity. Its runtime is
committed at 9dc2264 and local validation at ad38881; frozen legacy reference uses
WEPPpy 917708c. The current WEPPpy base only adds explicit HTTP 5xx diagnostics to
the soil module, with no changed numerical path.

Add wepppy/soils/ssurgo/source.py to validate explicit settings, perform bounded
JSON requests and persist cache identity/retrieval events. Extend collection
construction and the existing five query builders without changing default XML
helper signatures at call sites. Use the existing cache schema and numerical
builder. Create provenance sidecars alongside generated base soils. Wire the six
Soils call sites through persisted settings and namespace selected JSON cache paths.
Clear only the selected identity; leave source caches and other releases intact.

Run focused tests through wctl after verifying which checkout the container consumes.
Do not remount/recreate the shared development stack. If its mount rejects this
worktree, retain the rejection and use an isolated, already-authorized test setup
against the exact candidate checkout, recording identities explicitly. Check stubs
and run the broad suite when feasible; retain unrelated blockers honestly.

Extend the service parity runner to query the real API into empty separate caches
with candidate WEPPpy and external networking blocked. Import complete fixtures
separately with their replay release IDs. Compare records and emitted soil bytes
using only the existing Build Date/Source File exclusions; retain failures and
known legacy negatives. Verify sidecar soil hashes and cache retrieval identities.
Do not claim full NoDb/RQ/raster workflow or national source coverage from these runs.

## Validation and recovery


Use disposable scratch directories and isolated Compose project names. Never clear
production caches or delete retained volumes. Rollback selection returns to XML
and the retained original cache. Provenance mismatch fails; it is not fixed by
rewriting identity. Preserve raw diagnostics outside public artifacts. Tests must
cover real filesystem/SQLite and local HTTP boundaries, plus real generated output.

## Surprises & Discoveries


The current sidecar hardcodes USDA attribution; old rows do not have verified source
lineage. Existing _sync does not persist all-empty negative responses. JSON will
record those attempts atomically; XML behavior remains unchanged apart from additive
honest provenance. Local candidate fallback catches SsurgoRequestError/ValueError;
a distinct source-contract exception must propagate instead of silently falling back.

## Decision Log


2026-11-18: the operator explicitly requested endpoint provenance with JSON integration.
Use persisted per-project selection, SHA-256 cache namespaces, embedded identity,
and additive base-soil sidecars. Do not place server comments into scientific .sol
files or silently relabel historical rows. Require an explicit expected release so
warm-cache reuse needs no metadata request and cannot mix releases.

## Outcomes & Retrospective


Contract preparation only. No implementation or generated-output acceptance yet.
