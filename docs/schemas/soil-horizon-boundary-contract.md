# Generated soil 200 mm boundary contract

Status: accepted for generated soils, 2026-10-29. Implemented and locally validated.

## Normative behavior

All generated WEPP input-soil writers must emit an explicit horizon bottom at
200 mm whenever the profile extends beyond 200 mm and lacks that boundary.
For a crossing horizon, insert an upper copy ending at 200 mm and retain the
original row as its lower copy. Change only the new depth token and declared
layer count; preserve all physical/hydraulic tokens, soil version, OFE order,
total depth and restrictive-layer values. Do not replace or average properties.
Existing 200 mm boundaries and profiles ending at or above that depth are no-ops.
Boundary normalization is idempotent and does not mutate the source object.

Capacity is selected-executable dependent: historical/undeclared binaries permit
ten input horizons; the new paired release declares 23. Standalone writers
default to ten unless explicitly given a supported capacity. If insertion would
exceed that capacity, or an earlier converter already produced more, fail explicitly before
writing the output. Do not merge layers, discard deeper material or silently
omit the required boundary. The generated-artifact owner must preserve existing
files on normalization failure.

## Scope and ownership

Python owns soil input serialization, including dataset builders, utility
serialization, prepared/MOFE files, watershed channel soils (`pw0.sol`) and Roads
templates. A single shared operation
normalizes final generated text. Existing Disturbed top-200-mm property overrides
remain separate; normalization only inserts a boundary and preserves properties.

Immutable source assets and accepted uploaded files are not rewritten. The
explicit upload-preservation serialization path remains governed by
[single user-defined inputs](single-user-defined-inputs-contract.md), including
source version, topology and explicit hydraulic values. This is an intentional
exception, not an accidental alternate generated-soil implementation.

wepppyo3 currently returns anisotropy values to Python and writes model-output
soil Parquet. Neither operation inserts model-input horizons. A future Rust
input-soil writer must meet this contract and share its artifact parity tests;
no duplicate native writer is introduced by this change.

## Scientific compatibility

Equivalent subdivision should preserve the supplied physical profile, but
`wepp_261026` has a confirmed split/unsplit response sensitivity. Standardizing
input boundaries can change runoff and sediment, particularly where contrasting
conductivity horizons cross 200 mm. Do not describe this as a numerical no-op or
a sediment-reduction fix. Existing results remain historical; new runs need new
artifact provenance. Native repair and road calibration are separate work.

See [ADR-0110](../adrs/ADR-0110-generated-soil-200mm-boundary.md) and the
[work package](../work-packages/20261029_soil_200mm_boundary_consistency/package.md).

User-facing explanation: [Soil Input File — WEPPcloud normalization at 200 mm](../../wepppy/weppcloud/routes/usersum/input-file-specifications/soil-file.spec.md#weppcloud-normalization-at-200-mm).

## Input capacity and consumption (2026-11-18)

The accepted implementation separates native input capacity `mxhzin=23` from
calculation capacity `mxnsl=10`. The current national SSURGO writer requires 21;
23 covers 22 raw horizons plus one boundary without relying on exclusions.
Calculation depth, aggregation formulas and material values remain unchanged.

Resolve `features.soil_input_capacity` from the selected matched binary pair.
Missing declarations mean ten. Declarations must be matching integers from 1
through 23 (booleans are invalid), bound to the existing source/digest identity.
Malformed or mismatched metadata fails explicitly. No date/name inference or
automatic executable substitution. No saved project selection/default changes.

Raw SSURGO serialization, prepared/Disturbed writers, multi-OFE assembly and
channel writers receive this capacity explicitly, including across worker
processes. A final execution check enforces capacity on the soil actually
consumed so switching back to a historical executable cannot silently truncate.
Uploaded soils remain under their existing admission contract and are never
normalized just to validate capacity. Input validation must not rewrite them.
Other standalone dataset/converter paths retain ten unless explicitly opted in.

Compatibility plan: keep old keyword defaults and historical binaries; add only
an optional integer sidecar field and keyword capacity arguments. No NoDb data
migration. Verify raw/prepared/consumed counts and depth/property tokens with
Puaulu and Zepol, matching role binaries and fresh output. See ADR-0148.
