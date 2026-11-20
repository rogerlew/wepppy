# Watershed Hillslope Pass Reader Contract

## Status

- Normative contract frozen by PS-12 on 2026-05-14 for schema `2.0`
  implementation across `wepp-forest` and `wepppyo3`.
- Replaces the earlier aggregated watershed binary pass concept.
- Artifact role: in-memory watershed reader/index over hillslope binary pass
  shards.

## Decision

Process-mode watershed execution reads the hillslope binary pass files directly.
There is no durable process-mode `pass_pw0.txt` replacement and no aggregated
watershed binary pass file.

The watershed pass boundary is:

```text
hillslope binary pass shards
  -> watershed pass reader/index
  -> in-memory watershed arrays/state
  -> watershed routing
```

This removes the combiner, avoids a second disk I/O round trip, and prevents a
second serialized artifact from becoming a competing source of truth.

## Scope

The reader/index is responsible for:

- opening the full set of hillslope binary shards for a watershed run;
- validating compatible schemas, unit policies, calendars, event enums, and
  state registries;
- validating hillslope metadata against watershed expectations;
- loading per-day per-hillslope payloads into memory on demand;
- populating existing watershed arrays/state without parsing legacy text rows;
- presenting logical day metadata needed by watershed routing.

## Explicit Non-Goals

- Do not build `pass_pw0.txt` in process mode.
- Do not build an aggregated watershed binary pass file in process mode.
- Do not recompute closure-authoritative terms from rounded text.
- Do not silently fall back to `H*.pass.dat` or `pass_pw0.txt`.

## Pass Family Naming

WEPPpy/wepp_runner or any upstream run orchestration must choose the pass family
before watershed execution:

- legacy ASCII pass family: `H<hillslope_id>.pass.dat`;
- process binary pass family: `H<hillslope_id>.hbp`.

The process reader consumes `H*.hbp` shards. It may map a legacy deck entry such
as `H1.pass.dat` to `H1.hbp` during the migration window, but the durable
process-mode contract is direct `H*.hbp` selection. `H*.pass.dat.hbp` and
`H*.pass.hbp` are invalid because they preserve the obsolete text-pass surface
inside the binary-pass name. Missing or invalid translated `.hbp` shards are
fatal and must not trigger fallback to text pass files.

## Schema-Major Coexistence and Rollback

Schema-major coexistence and rollback semantics are run-scoped:

- a watershed run consumes one schema major only;
- cross-run coexistence is allowed (`1.x` runs and `2.x` runs in the same
  deployment window);
- dual-read/single-write is required before default cutover:
  - readers support `1.x` and `2.x`;
  - writers remain default `1.x` until PS-16 cutover acceptance;
- rollback disables schema `2.x` default emission while preserving dual-read;
- mixed-major shard sets are invalid in all phases.

## Shard Set Manifest

The process-mode watershed run card or runtime metadata must identify the
hillslope shard set.

Required manifest fields:

| field | type | notes |
| --- | --- | --- |
| `manifest_schema_major` | `u16` | incompatible manifest change indicator |
| `manifest_schema_minor` | `u16` | additive manifest change indicator |
| `run_id` | string | run provenance identifier |
| `nhill` | `u32` | hillslope count expected by watershed routing |
| `compatibility_id` | 32 bytes | expected schema+policy digest |
| `unit_policy_id` | string | expected numeric policy id |
| `calendar_policy_id` | string | expected calendar policy id |
| `event_enum_version` | `u16` | expected event enum version |
| `state_registry_id` | 32 bytes | expected state-registry digest |

Each hillslope entry must include:

| field | type | notes |
| --- | --- | --- |
| `hillslope_id` | `u32` | explicit one-based id |
| `path` | string | path to hillslope binary shard |
| `source_artifact_id` | 32 bytes | expected shard identity/checksum |
| `hillslope_area_m2` | scaled `i64` | expected area for routing validation |
| `nofe` | `u16` | expected OFE count |
| `max_layers` | `u16` | expected maximum state-vector layer count |

Paths are runtime configuration, not model authority. The binary shard headers
and checksums remain authoritative for payload values.

## Open/Validate Contract

`pass_reader_open_shard_set(...)` must validate before watershed routing starts:

- all required hillslope ids `1..nhill` are present exactly once;
- all shards in the run share one `schema_major`;
- every shard uses the manifest compatibility id, unit policy, calendar policy,
  event enum version, and state registry;
- all shards have compatible year tables;
- `npart` and particle metadata are consistent with watershed expectations;
- required state ids are present in each shard's state registry;
- shard checksum/identity matches the manifest entry;
- for schema `2.x`, every shard satisfies the schema `2.0` invariants in
  `docs/contracts/hillslope-binary-pass-format.md`;
- no unsupported major or higher unsupported minor schema is present.

Any failure is fatal for process-mode watershed execution.

## Logical Day Contract

For every represented `(sim_year_index, julian_day)`, the reader/index must
provide logical day metadata to watershed routing:

| field | type | notes |
| --- | --- | --- |
| `sim_year_index` | `u32` | one-based simulation year index |
| `calendar_year` | `i32` | calendar year from shard year table |
| `julian_day` | `u16` | represented day |
| `day_event_kind_max` | `u8` | max event enum across hillslopes |
| `event_count_no_event` | `u32` | number of `NO_EVENT` hillslopes |
| `event_count_subevent` | `u32` | number of `SUBEVENT` hillslopes |
| `event_count_event` | `u32` | number of `EVENT` hillslopes |

`day_event_kind_max` is routing control metadata only. It does not replace
per-hillslope event kinds.

Mixed days containing `EVENT`, `SUBEVENT`, and `NO_EVENT` are valid only when
the reader zero-fills non-applicable routing arrays before handing records to
watershed routing code.

## Read Contract

Required logical operations:

- `pass_reader_open_shard_set(manifest_path_or_run_metadata)`;
- `pass_reader_load_metadata(...)`;
- `pass_reader_load_day(sim_year_index, julian_day, hillslope_id, ...)`;
- `pass_reader_load_logical_day(sim_year_index, julian_day, ...)`;
- `pass_reader_close()`.

Function names may differ in implementation, but the roles are required.

The reader must support:

- sequential replay by day and hillslope id;
- random access by `(sim_year_index, julian_day, hillslope_id)`;
- metadata-only validation;
- selected state-vector extraction;
- first-error reporting.

## In-Memory Ownership

The reader/index may cache headers, directories, and selected day payloads in
memory. It must not materialize an aggregate pass artifact on disk as part of
the process-mode path.

Minimum required cache policy for PS-14/PS-15:

- metadata + directory + payload-block table resident per shard;
- payload block decode on demand;
- optional bounded LRU cache for decompressed blocks.

Optional stronger policy:

- full payload residency when memory budget allows.

PS-14/PS-15 validation artifacts must report benchmark evidence for the selected
policy on representative watershed runs.

## Required Invariants

- Hillslope shards are the only durable process-mode pass artifacts.
- The reader/index is a runtime adapter, not a serializer.
- One process trajectory owns every loaded row and state vector.
- Directory keys are valid under each shard's year table.
- Required process-state ids are present for every loaded record.
- Conserved values remain scaled integers until model conversion at the reader
  boundary.
- Checksum mismatches are fatal.
- Mixed schema majors in one run are fatal.
- Schema `2.x` block/day invariants are validated before routing starts.
- Legacy text is not a fallback.

## Reader Invariant Catalog

| invariant_id | invariant |
| --- | --- |
| `HBP2-R01` | `pass_reader_open_shard_set` rejects missing/duplicate hillslope ids `1..nhill`. |
| `HBP2-R02` | One run must be schema-major homogeneous. |
| `HBP2-R03` | Shard header policy fields match manifest (`compatibility_id`, unit/calendar/event/state registry ids). |
| `HBP2-R04` | Shard checksum/identity mismatches fail closed. |
| `HBP2-R05` | Unsupported major or higher unsupported minor fails closed. |
| `HBP2-R06` | Schema `2.x` shards must pass `HBP2-I01..HBP2-I14` before routing begins. |
| `HBP2-R07` | Mixed logical days (`NO_EVENT`/`SUBEVENT`/`EVENT`) require zero-fill of non-applicable routing arrays. |
| `HBP2-R08` | Missing or invalid translated `.hbp` path is fatal; no text fallback. |

## wepppyo3 Contract

`wepppyo3` reads hillslope shards independently and may read the shard-set
manifest for validation. It does not need to parse an aggregated watershed pass
file because that file does not exist in process mode.
