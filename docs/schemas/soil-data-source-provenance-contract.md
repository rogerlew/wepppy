# Soil data transport and provenance contract

Status: accepted operator direction, implementation pending. The operator requested
WEPPpy JSON integration and provenance identifying the queried soil-data server.
This contract governs SurgoSoilCollection and all six Soils collection call sites.
It is additive to NoDb persistence/concurrency and generated-soil artifact contracts.

## Selection and compatibility

Default absent state remains the existing USDA XML endpoint and legacy filenames.
Optional project settings are soil_data_endpoint, soil_data_profile, and
soil_data_release under the soils configuration section, persisted together by a
locked configure_soil_data_source method. Programmatic SurgoSoilCollection takes
corresponding keyword-only endpoint/profile/release arguments. No environment-global
or automatic failover selection is introduced. Legacy projects hydrate without
changes and retain XML. Only the known USDA endpoint supports legacy-xml; JSON
requires an explicit endpoint, wepppy-json-v1 profile, and immutable release ID.
Release ID is 1–128 ASCII letters/digits/dot/underscore/hyphen. Endpoint is an
absolute HTTP(S) URL ending in /Tabular/post.rest; reject userinfo, query strings,
fragments, control/whitespace and Markdown delimiter characters. Canonicalize host,
scheme and default port. Settings are operator configuration, not a browser input.

JSON file caches append a SHA-256 identity suffix derived from canonical endpoint,
profile and expected release to the legacy filename. Existing files remain intact.
The clear-cache setting affects only the selected identity. Explicit file paths
must also have matching embedded identity; renaming a file cannot bypass binding.
In-memory JSON collections have the same validation without persistent reuse.
Changing source settings does not relabel existing .sol files; rebuild explicitly.

## JSON transport and failures

Use form-urlencoded POST query plus format=JSON+COLUMNNAME, no redirects, bounded
connect/read timeouts, a 30-second absolute network deadline (including headers),
and 16 MiB response bytes on metadata and POST. Request identity encoding and reject
compressed responses before parsing; read streaming bodies under the same deadline. Batch at most 1000 sorted keys so
the service's 64 KiB query limit is respected even for long identifiers. For a
collection's first missing-data fetch, GET the same service prefix's /v1/metadata,
requiring readiness, the selected release/profile, valid code revision and a release
manifest. Record this metadata observation; it is not proof every later request
used that exact server binary. Validate the response endpoint plus profile/release
headers on every POST before cache writes. A release/profile change or malformed
response fails explicitly, including in local fallback candidate discovery; never
silently reuse another endpoint or convert transport failure into missing soil.

Table must have exactly the expected ordered columns and string/null equal-width
rows, including empty results. Empty string maps to None only in the legacy-client
adapter; use existing try_parse for other strings and current first-row-wins keys.
Do not change component selection, numerical defaults, formulas, or soil serialization.
HTTP and shape errors are explicit SoilDataSourceError exceptions, not empty tables.
Validate every MUKEY/COKEY/CHKEY cell as a nonnegative signed-64-bit base-10
integer string before conversion; reject decimal/exponent identifiers and non-finite
converted numbers. Reject response keys outside the requested set; preserve raw row order for ties.

## Durable source evidence

SQLite gains additive soil_data_source and soil_data_fetch tables. The former binds
endpoint/profile/release and records whether pre-existing rows have unknown origin.
The latter records successful retrieval timestamp, family, key/row counts, processed
record hash, and (JSON) observed response hash plus metadata/release manifest.
Commit retrieved rows, negative markers and their event in one SQLite transaction
for JSON. Empty JSON results record negative keys and an event. Failed batches must
not create positive/negative rows or successful-fetch evidence. Previously successful
batches remain valid under their pinned release. Identity initialization is serialized
with BEGIN IMMEDIATE; reject mismatches before modifying existing table contents.

Unbound populated caches are accepted only through legacy XML with historical origin
explicitly unknown. New XML retrieval events identify the configured USDA
endpoint, effective response origin when observed (otherwise unknown), and unknown release; they do not retroactively certify older rows. Warm
cache reuse makes no network request and does not advance retrieval timestamps.
The human .meta.md sidecar reports selected server/profile/release, unknown historical
origin, and actual recorded fetch counts. It must not claim a mirror is operated
by USDA or infer source family from SSURGO/STATSGO cache labels.

Invalidate any previous provenance sidecar before overwriting a base soil, including
when the new soil bytes may be identical but the source identity differs. Publish
the new sidecar atomically only after successful soil writing; propagate failures.
If overwrite=False preserves an existing soil, preserve its provenance too. Consumers
must verify the recorded soil hash before accepting sidecar evidence.

Each generated base .sol gains a separate .sol.provenance.json containing the soil
hash, MUKEY, selected component, cache-relative name, bound identity and recorded
retrieval evidence. Keep .sol text byte-compatible. These sidecars cover base soils;
subsequent treatment/preparation lineage still uses the existing source-file chain,
not an invented claim of per-request provenance in every downstream file. Validate
paired treated/prepared outputs alongside the base sidecar and cache evidence.

## State matrix and regression plan

Absent settings/legacy project: unchanged XML and filenames. Empty selected cache:
create identity and schema, fetch and retain evidence. Populated matching JSON cache:
reuse without network. Populated unknown cache selected as JSON: explicit rejection. Populated includes
negative-marker-only caches. Malformed or partially present provenance tables are
exceptional and cannot be silently rebound or repaired.
Populated XML cache: historical unknown remains visible; new fetches append evidence.
Mismatched source identity, invalid URL/release, failed metadata/headers/shape and
wrong returned keys, stale sidecar hashes, failed sidecar publication and slow-drip
or compressed/oversized bodies: exceptional input/state, fail without relabeling or mixed data.
Empty successful results: expected absence, retain negative markers and provenance.

Test all states with real SQLite and an actual local HTTP server, plus mocked error
boundaries where useful. Verify NoDb lock/persistence/reload, all six consumers,
selected-identity clearing, first-row-wins parsing and legacy XML regressions. Run
fresh-cache real Rust/PostgreSQL/JSON builds with external routing unavailable and
compare canonical soil bytes/selection/invalid outcomes against the frozen legacy
reference. Keep known source limitations and unrelated project workflow gaps explicit.
