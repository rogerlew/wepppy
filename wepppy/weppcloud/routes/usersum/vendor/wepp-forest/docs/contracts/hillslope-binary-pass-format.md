# Hillslope Binary Pass Format

## Status

- Normative contract frozen by PS-12 on 2026-05-14 for schema `2.0`
  implementation across `wepp-forest` and `wepppyo3`.
- Artifact role: per-hillslope producer shard.
- Authoritative process-mode watershed execution reads the hillslope binary
  shard set directly through the watershed pass reader/index, not through an
  aggregated pass artifact or legacy text pass files.
- This contract defines two compatible artifact families under `.hbp`:
  schema `1.x` (daily raw payloads) and schema `2.x` (fixed 366-day compressed
  payload blocks).

## Scope

A hillslope binary pass file records one hillslope's process trajectory after
hillslope simulation has completed water balance, routing, `sloss`, and
`sedseg` for each represented day.

It replaces process-mode dependency on individual `H*.pass.dat` files.

## File Role

The hillslope binary pass file is used for:

- direct watershed pass reload through the shard-set reader/index;
- focused replay/debugging;
- golden fixture generation;
- `wepppyo3` inspection.

It is not a legacy text compatibility artifact and does not need byte parity
with `H*.pass.dat`.

## File Naming

Canonical process-mode hillslope binary pass files use:

```text
H<hillslope_id>.hbp
```

Examples: `H1.hbp`, `H17.hbp`.

Legacy ASCII pass files keep their existing name family:

```text
H<hillslope_id>.pass.dat
```

The binary format must not be named as a sidecar of the legacy text file. In
particular, `H1.pass.dat.hbp` and `H1.pass.hbp` are rejected naming patterns.
During migration, a reader may derive `H1.hbp` from an existing legacy deck path
`H1.pass.dat`, but upstream run orchestration should select the pass family
explicitly before WEPP execution. If derived `H1.hbp` is missing or invalid,
the reader must fail closed and must not fall back to text pass files.

## Schema Profiles

- Schema `1.x` keeps one stored payload per represented day. Day-directory
  entries carry direct payload offsets, lengths, and CRCs.
- Schema `2.x` keeps one compressed payload block per represented simulation
  year and indexes represented days into decompressed block bytes.
- Both schema families use `.hbp` and the same artifact magic. Schema major
  selects decode path.
- A single watershed shard set must be schema-major homogeneous. Mixed
  `1.x`/`2.x` shard sets are invalid.
- Cutover policy is dual-read/single-write: readers accept both schema majors
  while writer policy defaults continuous-mode emission to schema `2.x` and
  keeps single-storm emission on schema `1.x`.
- In schema `2.0`, only continuous simulation mode is supported. Single-storm
  runs remain schema `1.x` until a later `2.x` revision defines single-storm
  encoding.

## Schema `2.0` Freeze and Migration Semantics

PS-12 freezes schema `2.0` with explicit run-scoped migration behavior:

- schema-major selection is run-scoped: every shard in one watershed run must
  use one schema major;
- cross-run coexistence is allowed: one run may use `1.x` while another run
  uses `2.x`;
- dual-read/single-write policy after PS-16 cutover acceptance:
  - readers accept both schema majors;
  - writers default continuous-mode emission to schema `2.x`;
  - single-storm emission remains schema `1.x`;
- rollback is writer-policy only:
  - disable schema `2.x` default emission and continue writing `1.x` for
    continuous runs;
  - keep dual-read enabled so existing `2.x` artifacts remain readable;
  - do not build mixed-major shard sets in one watershed run.

## File Layout

Schema `1.x` layout:

```text
file_header
dimension_unit_block
hillslope_metadata_block
year_table
state_registry_block
day_directory
daily_payload_region
footer
```

Schema `2.x` layout:

```text
file_header
dimension_unit_block
hillslope_metadata_block
year_table
state_registry_block
day_directory
payload_block_table
payload_block_region
footer
```

All offsets are byte offsets from the start of file.

## Magic and Artifact Kind

Required file magic:

```text
WFPHBP01
```

Meaning: WEPP Forest Pass Hillslope Binary Pass, schema family `01`.

Required footer magic:

```text
ENDHBP01
```

`WFPHBP01` and `ENDHBP01` are frozen for schema `1.x` and `2.x`.

`01` in `WFPHBP01` is artifact-family identity, not schema major version.
Schema compatibility is controlled by `schema_major`/`schema_minor`.

## File Header

Required fields:

| field | type | required | notes |
| --- | --- | --- | --- |
| `magic` | 8 bytes | yes | artifact kind |
| `schema_major` | `u16` | yes | incompatible change indicator |
| `schema_minor` | `u16` | yes | additive-compatible change indicator |
| `endianness` | `u8` | yes | `1=little`, `2=big` |
| `header_bytes` | `u32` | yes | total header bytes |
| `compatibility_id` | 32 bytes | yes | schema+policy hash |
| `artifact_role` | `u8` | yes | `1=hillslope_shard` |
| `producer` | string | yes | binary/build identifier |
| `run_id` | string | yes | run provenance identifier |
| `created_utc` | string | yes | ISO-8601 timestamp |
| `unit_policy_id` | string | yes | numeric policy identifier |
| `state_registry_id` | 32 bytes | yes | SHA-256 digest of the canonical PS-03 state registry serialization |
| `header_crc32c` | `u32` | yes | checksum over serialized header region |

For schema `1.x` and `2.x`, `state_registry_id` is part of the fixed header,
follows `unit_policy_id`, and is covered by `header_crc32c`. Readers must
validate it against the shard-set manifest and the embedded state registry block
before loading payload state snapshots.

Schema `2.0` requires `endianness = 1` (little-endian). Writers must emit
little-endian files and readers must reject other endian markers.

## Dimension and Unit Block

Required fields:

| field | type | notes |
| --- | --- | --- |
| `hillslope_id` | `u32` | explicit one-based hillslope id |
| `nyear` | `u32` | represented simulation years |
| `begin_year` | `i32` | first climate year |
| `npart` | `u16` | particle class count |
| `nofe` | `u16` | OFE count represented in process state |
| `max_layers` | `u16` | maximum soil-layer count in process state vectors |
| `calendar_policy_id` | string | leap/centurial day policy |
| `event_enum_version` | `u16` | event enum mapping |
| `simulation_mode` | `u8` | `1=continuous`, `2=single_storm` |

## Hillslope Metadata Block

Required fields:

| field | representation | notes |
| --- | --- | --- |
| `climate_file_name` | string | preserved from current pass header semantics |
| `hillslope_area_m2` | scaled `i64`, `m^2`, scale `1e-9` | area used by watershed routing |
| `particle_diameter_m[npart]` | `f64` array | particle diameter |
| `srp` | `f64` | concentration/scenario metadata currently carried by pass header |
| `slfp` | `f64` | concentration/scenario metadata |
| `bfp` | `f64` | concentration/scenario metadata |
| `scp` | `f64` | concentration/scenario metadata |

## Year Table

One year-table entry is required for every represented simulation year.

Required fields:

| field | type | notes |
| --- | --- | --- |
| `sim_year_index` | `u32` | one-based simulation year index |
| `calendar_year` | `i32` | climate/calendar year when known |
| `days_in_year` | `u16` | represented days for this simulation year |
| `first_julian_day` | `u16` | first represented Julian day |
| `last_julian_day` | `u16` | last represented Julian day |
| `single_storm_flag` | `u8` | `1` when this entry is a single-storm subset |

Directory keys are valid only when `(sim_year_index, julian_day)` falls inside
this table. Leap-year, centurial-day, and single-storm behavior is read from
the table, not inferred from record count.

For schema `2.0`, each year-table entry is a full represented leap year:

- `days_in_year = 366`
- `first_julian_day = 1`
- `last_julian_day = 366`
- `single_storm_flag = 0`

Schema `2.0` requires `simulation_mode = 1` (continuous).

## Event Kind

Canonical enum:

| value | name | meaning |
| --- | --- | --- |
| `0` | `NO_EVENT` | no runoff/subevent routing payload, but state snapshot required |
| `1` | `SUBEVENT` | lateral/subsurface/tile/baseflow payload without full runoff event |
| `2` | `EVENT` | full runoff/sediment event payload |

Event enum values are schema-governed and versioned.

## Day Directory

One directory entry is required for every represented `(sim_year_index,
julian_day)`.

Schema `1.x` fields:

| field | type | notes |
| --- | --- | --- |
| `sim_year_index` | `u32` | one-based simulation year index |
| `calendar_year` | `i32` | actual climate/calendar year when known |
| `julian_day` | `u16` | one-based day |
| `event_kind` | `u8` | canonical enum |
| `payload_offset_bytes` | `u64` | start of payload |
| `payload_length_bytes` | `u32` | payload length |
| `payload_crc32c` | `u32` | payload checksum |

Schema `2.x` fields:

| field | type | notes |
| --- | --- | --- |
| `sim_year_index` | `u32` | one-based simulation year index |
| `calendar_year` | `i32` | actual climate/calendar year when known |
| `julian_day` | `u16` | one-based day |
| `event_kind` | `u8` | canonical enum |
| `payload_block_id` | `u32` | references `payload_block_table` entry |
| `day_in_block_index` | `u16` | zero-based day slot in the raw block (`0..365`) |
| `raw_payload_offset_in_block_bytes` | `u32` | offset to this day payload in decompressed block bytes |
| `raw_payload_length_bytes` | `u32` | decompressed daily payload length |
| `raw_payload_crc32c` | `u32` | checksum over decompressed daily payload bytes |

Directory order is deterministic: `(sim_year_index asc, julian_day asc)`.

## Payload Block Table (Schema `2.x`)

One payload-block entry is required for each represented simulation year entry
in the year table.

Required fields:

| field | type | notes |
| --- | --- | --- |
| `payload_block_id` | `u32` | zero-based block id |
| `sim_year_index` | `u32` | one-based simulation year index |
| `block_day_slot_count` | `u16` | must be `366` in schema `2.0` |
| `represented_day_count` | `u16` | represented days in this block (`days_in_year`, must be `366` in schema `2.0`) |
| `stored_block_offset_bytes` | `u64` | start of compressed block bytes |
| `stored_block_length_bytes` | `u32` | compressed length |
| `raw_block_length_bytes` | `u32` | decompressed length |
| `payload_codec` | `u8` | `1=zlib` in schema `2.0` |
| `stored_block_crc32c` | `u32` | checksum over compressed block bytes |
| `raw_block_crc32c` | `u32` | checksum over decompressed block bytes |

The schema `2.0` canonical mapping is one block per simulation year:

```text
payload_block_id = sim_year_index - 1
```

Schema `2.0` payload block table rules:

- entries are ordered by `payload_block_id` ascending;
- `payload_block_id` values are contiguous: `0..(block_count-1)`;
- `payload_codec = 1` means RFC-1950 zlib stream (DEFLATE payload, no preset
  dictionary);
- other codec ids are reserved and unsupported.

## Payload Block Region (Schema `2.x`)

The payload block region stores compressed block bytes for entries in
`payload_block_table`.

Each decompressed block is a concatenation of canonical daily payload blobs for
that block's represented days. Daily payload bytes are byte-identical to schema
`1.x` daily payloads and begin with the same daily payload common prefix.
`day_directory` provides byte-level offsets/lengths for day extraction from raw
block bytes.

For schema `2.0`, each block contains exactly 366 day payload slices in Julian
day order (`1..366`) and must decode to `raw_block_length_bytes`.

## Daily Payload Common Prefix

Every daily payload starts with:

| field | type | notes |
| --- | --- | --- |
| `sim_year_index` | `u32` | must match directory |
| `calendar_year` | `i32` | must match directory |
| `julian_day` | `u16` | must match directory |
| `event_kind` | `u8` | must match directory |
| `payload_schema_minor` | `u16` | payload-compatible additions |
| `state_snapshot_count` | `u16` | number of state vectors following event fields |

## `NO_EVENT` Payload

Required event fields:

| field | representation | legacy source context |
| --- | --- | --- |
| `baseflow_volume_m3` | scaled `i64` | `gwbfv` |
| `dissolved_storage_volume_m3` | scaled `i64` | `gwdsv` |
| `process_state_snapshot` | state vector table | required |

`NO_EVENT` does not mean no water-balance state changed. The process-state
snapshot is required.

## `SUBEVENT` Payload

Required event fields:

| field | representation | legacy source context |
| --- | --- | --- |
| `subsurface_flow_depth_m` | scaled `i64` | `sbrunf` |
| `subsurface_flow_volume_m3` | scaled `i64` | `sbrunv` |
| `tile_drainage_depth_m` | scaled `i64` | `drainq` |
| `tile_drainage_volume_m3` | scaled `i64` | `drrunv` |
| `baseflow_volume_m3` | scaled `i64` | `gwbfv` |
| `dissolved_storage_volume_m3` | scaled `i64` | `gwdsv` |
| `process_state_snapshot` | state vector table | required |

## `EVENT` Payload

Required event fields:

| field | representation | legacy source context |
| --- | --- | --- |
| `duration_seconds` | `f64` | `dur` |
| `time_of_concentration_hours` | `f64` | `tcs` |
| `overland_flow_alpha` | `f64` | `oalpha` |
| `runoff_depth_m` | scaled `i64` | `runoff(nplane)` |
| `runoff_volume_m3` | scaled `i64` | `runvol(nplane)` |
| `subsurface_flow_depth_m` | scaled `i64` | `sbrunf` |
| `subsurface_flow_volume_m3` | scaled `i64` | `sbrunv` |
| `tile_drainage_depth_m` | scaled `i64` | `drainq` |
| `tile_drainage_volume_m3` | scaled `i64` | `drrunv` |
| `peak_runoff_m3_s` | `f64` | `peakro * harea` equivalent |
| `total_detachment_kg` | scaled `i64` | `tdet` |
| `total_deposition_kg` | scaled `i64` | `tdep` |
| `sediment_concentration_kg_m3[npart]` | `f64` array | `sedcon(:,nplane)` |
| `particle_flow_fraction[npart]` | `f64` array | `frcflw(:,nplane)` |
| `baseflow_volume_m3` | scaled `i64` | `gwbfv` |
| `dissolved_storage_volume_m3` | scaled `i64` | `gwdsv` |
| `process_state_snapshot` | state vector table | required |

## Process-State Snapshot

The snapshot is a table of state vectors. Each entry has:

| field | type | notes |
| --- | --- | --- |
| `state_id` | `u16` | stable schema-governed id |
| `entry_length_bytes` | `u32` | byte length for this state-vector entry |
| `required_flag` | `u8` | `1=required`, `0=optional` |
| `representation_class` | `u8` | `1=scaled_i64`, `2=f64` |
| `unit_class` | `u16` | schema-governed unit id |
| `rank` | `u8` | number of dimensions |
| `dims[rank]` | `u32` array | explicit dimensions |
| `values` | typed array | count equals product of dims |

Initial required state families:

- soil-water storage state used by process closure;
- snow/ice/frozen-water storage state where active;
- interception/canopy/residue storage state;
- downstream-readable storage terms that participate in closure accounting.

The concrete required `state_id` registry is frozen in:

- `docs/work-packages/20260505-ps03-state-registry-mode-semantics-freeze/artifacts/state_registry.md`

Files that omit required state ids are invalid.

## Footer

Schema `1.x` fields:

| field | type | notes |
| --- | --- | --- |
| `directory_crc32c` | `u32` | checksum over day directory |
| `file_crc32c` | `u32` | checksum over declared file regions excluding this field |
| `record_count` | `u32` | must equal the sum of `days_in_year` entries in the year table |
| `footer_magic` | 8 bytes | artifact terminator |

Schema `2.x` fields:

| field | type | notes |
| --- | --- | --- |
| `directory_crc32c` | `u32` | checksum over day directory |
| `payload_block_table_crc32c` | `u32` | checksum over payload block table |
| `file_crc32c` | `u32` | checksum over declared file regions excluding this field |
| `record_count` | `u32` | must equal the sum of `days_in_year` entries in the year table |
| `block_count` | `u32` | must equal the year-table entry count |
| `footer_magic` | 8 bytes | artifact terminator |

## Required Invariants

- One record exists for every represented day.
- `NO_EVENT` records include process-state snapshots.
- Payload and directory keys must match.
- Directory keys must be valid under the year table.
- Required state ids must be present on every record.
- Conserved values are encoded as scaled integers before any text conversion.
- Non-finite values are rejected.
- Unsupported schema major versions are rejected.
- Higher schema minor versions are rejected until PS-03 implements skippable
  block/TLV evolution support.
- Checksum mismatches are rejected.
- Legacy text is not a fallback.
- Schema `2.0` uses fixed 366-day slots for every payload block.
- Schema `2.0` canonical mapping is one payload block per simulation year entry.
- Schema `2.0` year-table entries must be full leap-year ranges (`1..366`).
- Schema `2.0` `day_in_block_index` must equal `julian_day - 1`.
- Schema `2.0` payload blocks are zlib-compressed and validated by stored and
  raw CRC32C fields.
- Schema `2.0` is continuous-only: `simulation_mode` must be `1`.
- Schema `2.0` requires little-endian encoding (`endianness = 1`).
- Schema `2.0` uses fixed magic constants: header `WFPHBP01`, footer `ENDHBP01`.
- Schema `2.0` `record_count` must equal `366 * nyear`.
- Schema `2.0` `block_count` must equal `nyear`.
- Schema `2.x` day-slice bounds must satisfy
  `raw_payload_offset_in_block_bytes + raw_payload_length_bytes <= raw_block_length_bytes`.
- Schema `2.x` day-slice ranges for records that reference the same
  `payload_block_id` must not overlap.
- Schema `2.x` day-slice ranges for a payload block must cover the raw block
  without gaps when records are ordered by `day_in_block_index`.
- Schema `2.x` `payload_block_id` must reference an existing payload-block entry
  and that entry's `sim_year_index` must match the day-directory
  `sim_year_index`.
- Schema `2.x` `day_in_block_index` must be in `0..(block_day_slot_count-1)`.

## Schema `2.0` Invariant Catalog

| invariant_id | invariant |
| --- | --- |
| `HBP2-I01` | `magic = WFPHBP01` and `footer_magic = ENDHBP01`. |
| `HBP2-I02` | `schema_major = 2`, `schema_minor = 0` for schema `2.0` artifacts. |
| `HBP2-I03` | `endianness = 1` (little-endian). |
| `HBP2-I04` | `simulation_mode = 1` and year entries have `single_storm_flag = 0`. |
| `HBP2-I05` | Every year entry is fixed `days_in_year=366`, `first_julian_day=1`, `last_julian_day=366`. |
| `HBP2-I06` | `payload_block_id = sim_year_index - 1`, contiguous `0..(block_count-1)`, `block_count = nyear`. |
| `HBP2-I07` | `payload_codec = 1` (RFC-1950 zlib stream, no preset dictionary). |
| `HBP2-I08` | `record_count = 366 * nyear`; one directory entry per represented day. |
| `HBP2-I09` | `day_in_block_index = julian_day - 1` and is in `0..365`. |
| `HBP2-I10` | Day-slice offsets/lengths are bounded by `raw_block_length_bytes` and non-overlapping per block. |
| `HBP2-I11` | Day slices in a block cover decompressed block bytes without gaps in day-index order. |
| `HBP2-I12` | `stored_block_crc32c`, `raw_block_crc32c`, and `raw_payload_crc32c` all validate. |
| `HBP2-I13` | Mixed schema majors in one watershed shard set are invalid. |
| `HBP2-I14` | Missing or invalid `.hbp` shard is fatal; no fallback to legacy text pass files. |

## Reader Requirements

Readers must support:

- metadata-only validation;
- sequential replay;
- random access by `(sim_year_index, julian_day)`;
- selected state vector extraction;
- first-error reporting.
- dual decode paths for schema `1.x` and schema `2.x` under `.hbp`.
- shard-set validation that rejects mixed schema majors in one watershed run.

`wepppyo3` must be able to decode this artifact independently of Fortran.
