# WP12B Generated Capability Matrix Evidence

## Authority boundary

- Canonical profiles: 16 total; one Builder-exposed (`continental-us`), ten
  supported geographic bases, four overlays, and one non-applicable model
  family (`rhem`).
- Runtime normalization: stable `continental-us` serializes runtime locale
  token `us`; Tenerife composes as base `europe` plus overlay `tenerife`.
- Landcover provider: 163 exact stable/runtime identities. eMapR ends at 1984;
  1983 is not advertised.
- Climate provider: all 13 runtime descriptors remain inventoried; the
  continental-US Builder graph exposes the four supported datasets and their
  dataset-specific station/spatial adjacency.
- WEPP provider: the schema-v2 graph consumes the complete deduplicated default
  WEPP binary provider list. Every advertised binary participates in valid
  TOPAZ/single-OFE and WBT/single-OFE tuples; only `wepp_260803` participates in
  the WBT/multiple-OFE tuple.

## Generated and hostile matrix

`tests/nodb/test_locale_capability_authority.py` resolves a real Builder
selection, serializes canonical `config.cfg` bytes, reopens them with an actual
`ConfigParser`-backed reader, and validates the complete schema-v2 graph. It
also proves:

- shipped locale-token coverage and deterministic overlay order;
- exact landcover count and runtime identity;
- axis coverage without an unauthorized tuple cross-product;
- rejection of missing relation sections, unknown axes, empty and duplicate
  mandatory axes, newer schema versions, malformed provider identities, and
  orphan relation keys; and
- legacy/no-authority plus schema-v1 partial-axis compatibility.

Paired route tests prove hidden climate station/spatial methods, soil builders,
landuse methods, landcover datasets, and WEPP binaries fail before controller
mutation. Discovery tests prove controller schemas/templates, endpoint schema
aggregation, pipeline, and readiness expose only stored authority.

## Local results

Evidence was collected on 2026-08-27 at implementation ancestor `4a975657f8`
with the WP12B implementation diff applied:

- `wctl run-pytest` over every WP12B-touched test module: 533 passed;
- the narrower locale/authority/mutation/discovery subset: 220 passed;
- registry, preset snapshot, and Builder routes: 71 passed;
- `wctl run-npm lint`: passed;
- `wctl run-npm test`: 107 suites / 792 tests passed;
- `wctl run-stubtest wepppy.nodb.config_builder.schema`: passed;
- `wctl run-stubtest wepppy.nodb.project_config_capabilities`: passed;
- `wctl check-test-stubs`: passed;
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`:
  passed with net changed-file broad-catch delta -4; and
- `wctl check-rq-contracts`: endpoint inventory and route-contract checklist
  passed.
- `wctl run-pytest tests --maxfail=1`: 7,034 passed and 63 skipped in
  11 minutes 29 seconds. This includes the real GDAL SBS conversion test; no
  GDAL executable-call mock was added.
- `wctl check-test-isolation`: all five seeded suite iterations passed (42,
  123, 999, 1337, and 8,675,309). The later parallel file audit was incomplete:
  an unrelated profile-recorder test failed collection because its Flask stub
  lacked `Request`, after which the checker failed to serialize the function
  object in its JSON result. Every WP12B project-config/locale-authority test
  file reported `Isolated OK` before the checker aborted. The overall
  file-isolation audit is not claimed as passing.

## Forest result

Exact host `forest` ran revision `3e8d0d09bcf5` without an image build. The
registry exposed one Builder profile and 72 WEPP binaries. Builder run
`matted-smooth` was created and reopened with durable profile
`continental-us`, runtime locale `us`, and complete schema-v2 stored authority.
All advertised providers passed deployed presence/health checks; real GDAL,
WBT, and default watershed/hillslope WEPP executions passed. A direct invalid
landuse selection returned diagnostic HTTP 400 without state mutation. Full
transcripts and revision identities are recorded in
`20260827_forest_acceptance.md`.
