# Soil data transport and provenance contract

Status: implemented and validated for bounded cache replay (2026-11-18 UTC). The operator requested
WEPPpy JSON integration and provenance identifying the queried soil-data server.
This contract governs SurgoSoilCollection and all six Soils collection call sites.
It is additive to NoDb persistence/concurrency and generated-soil artifact contracts.

## Mirror-first with SDA fallback

On 2026-11-18 the operator directed moving toward a mirror-first deployment default
with USDA Soil Data Access (SDA, referred to conversationally as SDMS) as fallback.
The retained SSURGO/STATSGO fixture parity is sufficient to proceed; comprehensive
geographic/live SDA comparison is deferred until recovery. This supersedes the
previous no-automatic-failover product direction. The Forest implementation section below governs the additional selection policy;
explicit-source callers retain their established transport behavior.

Deployment defaults govern new/unconfigured projects; preserve
explicit source overrides and existing artifacts. Persisted old XML settings cannot
be assumed to be implicit defaults, so migration must be deliberate. Use bounded
SDA fallback on primary connection/timeout, HTTP 429/5xx/not-ready, or missing required
map-unit components/explicit coverage misses. Optional-table absence and numerical
soil rejection do not indicate a source outage. Cache identity/corruption and
response-contract violations remain explicit failures.

Retry the whole requested collection using SDA's separate source cache before
soil construction. Never combine primary components with fallback horizons or
relabel SDA rows as mirror data. Record configured primary, attempted sources,
fallback reason/time and actual supplier alongside existing retrieval evidence and
base-soil sidecars. Return to mirror-first on the next construction without making
an outage a permanent source switch. Preserve both errors when neither source works.

The contract, ADR-0145 and independent reviews precede implementation. Controlled
HTTP/TLS tests cover fallback without relying on live SDA recovery. Deployment
activation and code validation are reported separately.

## Selection and compatibility

Without a mirror-first deployment setting, absent state uses USDA XML and legacy filenames.
Optional project settings are soil_data_endpoint, soil_data_profile, and
soil_data_release under the soils configuration section, persisted together by a
locked configure_soil_data_source method. Programmatic SurgoSoilCollection takes
corresponding keyword-only endpoint/profile/release arguments. Direct explicit-source callers do not automatically fail over. Saved identities
without a policy remain explicit; absent identity resolves project configuration
before deployment defaults. Only the known USDA endpoint supports legacy-xml; JSON
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
and response byte caps of 64 KiB for metadata and 16 MiB for POST. The smaller
metadata cap bounds amplification when the observed manifest is retained in fetch
events and base-soil sidecars; this is an explicit client profile limit, not a claim
that arbitrary larger SDA metadata is supported. Reject JSON nesting deeper than 64. Request identity encoding and reject
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

Absent settings: apply explicit project configuration, then deployment defaults.
Saved legacy identity: unchanged XML and filenames. Empty selected cache:
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

Operator usage and provenance inspection: [JSON soil source guide](../dev-notes/soil-json-source.md).

## Forest implementation contract

Environment keys SOIL_DATA_MODE=mirror-first, SOIL_DATA_ENDPOINT and SOIL_DATA_RELEASE
supply the default only when a project has no saved identity or source configuration.
Absent mode retains XML; invalid/incomplete configured mode fails explicitly. New
projects persist identity and a separate policy (explicit or mirror-first). Existing
saved identities without policy remain explicit, including saved XML defaults.
configure_soil_data_source gains fallback_to_sda=False; True requires JSON and opts
that project into mirror-first. All six consumers use one collection factory.

Each selection permits one primary and one fallback attempt. Network acquisition
has a 30-second absolute budget per source and 60 seconds overall, including DNS,
connect/TLS, metadata, all query batches, headers and bodies. No retry/backoff sleeps
apply in this mode. This does not impose a wall-time limit on modeling/local SQLite.
Explicit XML retains legacy requests behavior. Fallback XML uses bounded HTTP,
identity encoding, a 16 MiB cap, no redirects, and rejects DTD/entity declarations,
malformed XML, unexpected dataset envelopes, row columns/keys and nonfinite values.
The XML root must be NewDataSet with direct Table rows and optional XML Schema
metadata; empty NewDataSet is valid, an Error envelope is not. Nested cell elements
are rejected. Preserve query and
legacy first-row-wins/null semantics. TLS certificate failures are explicit defects.

Only availability errors (DNS resolution, any network deadline expiry including
headers/body/aggregate acquisition, or connection failure,
HTTP 429/5xx, ready=false) and missing required component MUKEYs permit SDA fallback.
Local resolver process launch failure, database/provenance corruption, wrong release,
malformed data, unexpected HTTP 4xx and numerical rejection do not. Incomplete
optional tables are normal absence. No source attempt repairs the other source cache.
A failed constructor must close its connection; committed prior batches may remain.

Selection event schema v1 contains policy, configured_primary, actual_supplier (null
on failure), selected_at and ordered attempts. Each attempt includes identity,
started_at, ended_at, outcome and a stable reason code; do not retain raw exceptions,
SQL, credentials, or arbitrary response text. Add soil_data_selection(id INTEGER
PRIMARY KEY,event TEXT NOT NULL) to the successful supplier's SQLite cache. Retain
latest selection atomically at the primary cache path plus .selection.json, including
both-source failure. Existing source/fetch metadata and scientific tables stay valid.
Warm reuse records a new selection, not a new retrieval or fabricated timestamp.
Add the exact selection event to each base-soil provenance sidecar; actual cache
binding and event supplier must agree. Direct explicit collection callers may lack
selection metadata and retain the existing sidecar contract.

Whole-collection fallback uses the canonical separate legacy cache for the same
SSURGO/STATSGO role. Successful empty SDA data remains a successful query subject to
the existing invalid-soil handling. Both-source failure raises a source-selection
error carrying structured attempts and cannot enter numerical candidate fallback.
Required states: absent default, malformed environment, saved legacy, explicit JSON,
mirror warm/cold, primary unavailable/partial, missing components, optional absence,
SDA warm/cold/empty, dual failure and malformed source/cache state. Tests must exercise
real HTTP/SQLite/filesystem and real NoDb locking, and queued forest construction must
read back final soil inputs and source sidecars. No production activation is included.

For warm fallback, actual_supplier identifies the chosen cache/transport binding,
not a retroactive claim about historical rows. Include historical_rows_unknown in
the selection event and retain that flag in the base-sidecar binding. Validate the
selection table schema and all existing events before reuse/insertion; malformed
history fails explicitly. Invalidate the previous latest-selection sidecar before
starting a new selection. Persist the selected supplier's SQLite event, then atomically
publish the latest sidecar before returning the collection. Publication failure
raises explicitly and leaves no stale latest success for the new operation; cached
retrievals/committed history may remain, but no new soil may be built from a selection
that did not finish publishing its required evidence. An absent sidecar is not success.

Selection events carry schema_version=1. Attempt outcomes are success, unavailable,
coverage_miss, or contract_error. Reason codes are selected, cache_reused,
dns_unavailable, connection_failed, deadline_exceeded, http_429, http_5xx, not_ready,
missing_components, source_contract_error, and selection_persistence_error. A successful
event has exactly one successful final attempt matching actual_supplier; failed
events have no actual_supplier. Every persisted successful event's supplier must
match its cache binding and historical-origin flag; different configured primaries may validly share an SDA
cache. Translate selection schema/SQLite/filesystem failures to SoilDataSourceError
so existing OSError/ValueError candidate handlers cannot hide provenance failure.
DNS child exit codes must distinguish remote name resolution failure from local
process failure. XML DTD/entity rejection must work for UTF-16 as well as UTF-8.

## Shared default geographic coverage

The operator requires nationwide SSURGO and STATSGO2 for the shared mirror-first
default. A regional import is qualification data, not sufficient outage coverage.
Comprehensive live SDA parity remains deferred; the actual national data must
be loaded. This clarifies the acceptance scope after the regional forest default
failed on all 22 Colorado map units in cavernous-oxygen while SDA remained down.
Release changes retain immutable identities, source-separated caches, and deliberate
migration of saved mirror pins; unrelated explicit source overrides are preserved.
