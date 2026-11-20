# Pass Binary Serialization Guidance

## Status

- Normative guidance for PS-series binary pass implementation.
- Applies to hillslope pass shards, WEPP process-mode pass readers/writers,
  watershed shard-set readers, and `wepppyo3` binary readers.
- Complements:
  - `docs/pass-serialization-rewrite-strategy.md`
  - `docs/contracts/trajectory-ownership-contract.md`
  - `docs/contracts/pass-and-output-contracts.md`
  - `docs/work-packages/20260505-ps02-binary-pass-architecture-decision/artifacts/format_decision_record.md`

## Purpose

Define the rules that keep custom binary pass serialization portable,
inspectable, testable, and safe for closure-sensitive scientific state.

The binary pass format is a model contract, not an implementation convenience.
It replaces large rounded flat text pass artifacts in process mode and must
preserve one process trajectory across hillslope write, watershed reload, and
downstream inspection.

## Non-Negotiable Rules

1. Use explicit byte-stream layout.
2. Do not use compiler-dependent Fortran sequential unformatted records as the
   durable format.
3. Reject non-finite numeric inputs before serialization.
4. Reject scaled-integer overflow before serialization.
5. Store closure-authoritative conserved terms as scaled `int64`.
6. Store non-conserved coefficients and diagnostic reals as `f64`.
7. Put schema version, compatibility id, endian marker, dimensions, units, and
   checksums in the file.
8. Fail closed on unsupported major version, missing required fields, dimension
   mismatch, checksum mismatch, or truncated payload.
9. Never silently fall back to legacy `H*.pass.dat` or `pass_pw0.txt`.
10. Treat JSON/text sidecars as diagnostics only, never authority.
11. Define the process-state registry before implementation. A pass writer is
    not conforming until every closure-critical and downstream-readable state
    term has a stable `state_id` and reload target.

## Primitive Encoding

Unless a later schema version explicitly changes these rules:

| primitive | encoding |
| --- | --- |
| `u8` | unsigned 8-bit integer |
| `u16` | unsigned 16-bit integer |
| `u32` | unsigned 32-bit integer |
| `u64` | unsigned 64-bit integer |
| `i32` | signed 32-bit integer |
| `i64` | signed 64-bit integer |
| `f64` | IEEE-754 binary64 |
| string | `u32` byte length followed by UTF-8 bytes |
| bytes | `u32` byte length followed by raw bytes |

All multi-byte primitives use the file endian declared in the header. The PS-03
default should be little-endian unless implementation evidence justifies
otherwise. Readers must reject unknown endian markers.

Do not rely on implicit structure padding or compiler layout. Arrays are encoded
as explicit counts followed by contiguous primitive values.

## Header Requirements

Every binary pass file must start with:

- magic bytes identifying artifact kind;
- schema major and minor;
- endian marker;
- header length;
- compatibility id;
- producer metadata;
- run metadata;
- unit policy id;
- dimension block;
- header checksum or checksum-covered header region.

The reader must validate the header before attempting payload decode.

## Numeric Policy

Conserved terms use scaled `int64`:

| class | unit | scale |
| --- | --- | --- |
| depth/storage depth | meters | `1e-9 m` per count |
| volume/storage volume | cubic meters | `1e-9 m^3` per count |
| mass, if closure-authoritative | kilograms | `1e-9 kg` per count |
| geometry area | square meters | `1e-9 m^2` per count |

Encoding:

```text
stored_i64 = nint(value_si / scale)
```

Decoding:

```text
value_si = stored_i64 * scale
```

Encoding must reject:

- NaN;
- Inf;
- values outside `int64` range after scaling;
- values whose unit class does not match the field registry.

Non-conserved values may use `f64`, including:

- duration;
- time of concentration;
- alpha;
- particle diameters;
- sediment concentrations;
- particle-flow fractions;
- non-authoritative diagnostics.

## Schema Governance

Every field has:

- stable field id;
- stable name;
- type;
- unit;
- representation class;
- required/optional status;
- compatibility notes.

Version rules:

- `schema_major` changes for breaking changes;
- `schema_minor` changes for additive compatible changes;
- required-field removal or semantic change requires major increment;
- numeric scale changes for existing fields require major increment;
- optional fields require defaults or explicit nullable semantics.

Process-state vectors are governed by stable `state_id` values. Adding an
optional `state_id` is a minor change. Changing a required `state_id` meaning,
type, dimensions, or units is a major change.

PS-03 must publish the state registry before writer/reader implementation. Each
state entry must include:

- stable `state_id`;
- stable name;
- source symbol and common-block/module ownership in Fortran;
- watershed reload target symbol;
- rank and dimensions;
- unit class and numeric scale;
- representation class;
- required/optional status;
- inactive semantics for days where a process is not active;
- closure role or downstream-consumer rationale.

A file missing any required state id is invalid even if all event payload fields
decode successfully.

## Layout Evolution

The initial schema uses fixed-order top-level blocks, length-delimited strings,
and length-delimited payloads. Until PS-03 implements a block table of contents
or TLV-style field encoding, readers must reject files with a higher
`schema_minor` than they explicitly support. Optional fields may be added only
inside length-delimited payload sections that an older reader can skip by
declared byte length.

Every state-vector entry must carry its own byte length. Readers that encounter
an unknown optional `state_id` skip exactly that entry by length. Readers that
encounter an unknown required `state_id` fail closed.

## Integrity

Minimum integrity requirements:

- header validation before payload decode;
- explicit `header_crc32c`;
- per-payload CRC32C or stronger checksum;
- directory checksum;
- file footer checksum over the declared regions;
- explicit payload length and offset checks;
- hard failure on truncated reads.

Checksums are not optional in process-mode acceptance runs.

CRC32C uses the Castagnoli polynomial. Checksum fields are stored in the file
endianness and are computed over the exact serialized byte ranges declared by
the specification. A checksum field is treated as zero while computing the
checksum for a region that contains it. `file_crc32c` covers all declared file
regions from byte zero through the footer, excluding only the `file_crc32c`
field itself.

`compatibility_id` is a 32-byte SHA-256 digest over the canonical schema
manifest, numeric policy id, state registry, event enum version, calendar
policy id, and aggregation policy id where applicable. PS-03 must publish the
canonical manifest serialization used as the digest input.

## Direct Access

Readers must support:

- sequential replay in deterministic order;
- random access by `(sim_year_index, julian_day, hillslope_id)` and metadata
  lookup from `sim_year_index` to calendar year;
- metadata-only validation;
- full validation.

Directory entries must contain enough offset/length/checksum information to
load a single day/hillslope record without scanning all previous records.

## Artifact Roles

### Hillslope Binary Pass File

A hillslope binary pass file is a producer shard. It records one hillslope's
process trajectory and may be used for fixture evidence, watershed reload, and
debugging.

The set of hillslope binary pass files is the only durable process-mode pass
authority for watershed execution.

### Watershed Hillslope Pass Reader

A watershed hillslope pass reader is an in-memory reader/index over the
hillslope shard set. It validates shard compatibility, provides logical day
metadata, and loads per-day per-hillslope payloads into watershed arrays/state.

It is not a durable serialized artifact. Process-mode execution must not create
an aggregated watershed pass file as a `pass_pw0.txt` replacement.

## Sidecars

Text or JSON sidecars may exist for:

- debugging summaries;
- schema catalog extracts;
- artifact manifests;
- operator inspection.

Sidecars must not be required for process-mode execution and must not override
binary payload values.

## Best-Practice Test Vectors

PS-03 should create binary fixtures for:

- one hillslope, one day, `NO_EVENT`;
- one hillslope `SUBEVENT` with lateral flow only;
- one hillslope `SUBEVENT` with tile drainage only;
- one hillslope `EVENT` with all particle arrays populated;
- multi-hillslope mixed day: `NO_EVENT`, `SUBEVENT`, and `EVENT`;
- leap day `366`;
- legacy centurial day handling, if still supported;
- zero, tiny positive, large valid, and overflow scaled-integer cases;
- unsupported major version;
- unsupported higher minor version while TLV/block-TOC support is absent;
- bad magic;
- bad header checksum;
- bad payload checksum;
- truncated directory;
- missing required state id.

## Fortran/Rust Interoperability

Fortran writers and readers must use stream access with explicit byte writes,
not sequential unformatted records. Integer and real kinds must be mapped from
`iso_fortran_env` (`int8`, `int16`, `int32`, `int64`, `real64`) and tested
against Rust primitive decoders.

Unsigned values are represented in Fortran by signed integer kinds with explicit
range validation before serialization. Endian conversion must be explicit;
native-endian assumptions are not portable.

Scaled integer encoding must define half-scale tie behavior in PS-03 test
vectors. The initial recommendation is round-half-away-from-zero implemented
identically in Fortran and Rust, with rejection if round-trip error exceeds half
the declared scale.

Cross-language fixtures must cover:

- endian marker rejection;
- strings with zero length and non-ASCII UTF-8;
- half-scale rounding cases;
- minimum and maximum valid scaled integers;
- NaN and Inf rejection for `f64`;
- header, payload, directory, and file CRCs.

## Independent Reader Contract

`docs/work-packages/20260505-ps02-binary-pass-architecture-decision/artifacts/wepppyo3_reader_contract.md`
is a normative complement to these binary contracts. PS-03 implementations must
carry its typed error contract, validation report fields, and fixture
requirements forward into Rust reader tests.

## Common Gotchas

- Fortran sequential unformatted files include compiler/runtime record markers.
  They are not portable durable artifacts.
- Text sidecars can drift from binary payloads. Keep them diagnostic-only.
- Event days with no runoff still need process-state snapshots.
- A day-level event summary is not a substitute for per-hillslope event kind.
- Leap-year policy cannot be inferred from record count.
- Mixed numeric policy requires a complete field registry; otherwise developers
  will accidentally serialize conserved terms as `f64`.
- A converter from legacy text to binary cannot reconstruct missing process
  state unless the missing state is provided by another artifact.
- Silent fallback to text hides exactly the class of defects this campaign is
  intended to remove.
