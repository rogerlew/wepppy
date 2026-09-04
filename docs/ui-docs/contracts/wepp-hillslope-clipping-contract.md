# WEPP Hillslope Clipping Contract

## Status

Accepted contract pending implementation as part of
`docs/work-packages/20260904_mofe_hillslope_clipping/`.

## Purpose

This contract defines how the WEPP advanced option `Clip hillslopes` changes
generated hillslope slope files. A slope file describes one representative
hillslope and may contain one or more overland flow elements (OFEs). An OFE is
a contiguous slope segment with its own length and profile.

## User Controls

The `clip_hillslopes` boolean enables or disables clipping during ordinary WEPP
input preparation. The `clip_hillslope_length` value is expressed in meters and
is the maximum permitted length of each OFE.

The rq-engine `run-wepp` operation accepts the established request spelling
`hillslope_clip_length` and compatibility alias `clip_hillslope_length`; both
set the same persisted `Watershed.clip_hillslope_length` value. When both are
present, `hillslope_clip_length` remains authoritative unless its extracted
value is `None` (including JSON null or an all-empty collection), in which case
the compatibility alias is used. A scalar empty string does not trigger alias
fallback and produces no update. Request parsing remains
backward compatible: values are parsed with Python integer conversion; absent,
empty, boolean, and non-numeric values do not update the persisted length.
Finite fractional numeric values retain the established integer-conversion
behavior. Numeric NaN and strings `"nan"`, `"inf"`, and `"-inf"` produce no
length update. Numeric positive or negative infinity retains the pre-existing
exceptional synchronous `OverflowError` behavior and does not enqueue;
repairing that broader parser defect is outside this package. A parsed zero or
negative value may be persisted by compatibility paths, but is invalid runtime
state when clipping is enabled.

## Generated Slope-File Behavior

When `clip_hillslopes` is false, preparation copies each source slope geometry
without length clipping.

When `clip_hillslopes` is true, preparation applies the following behavior to
both single-OFE and multiple-OFE slope files:

1. Each OFE whose original length is greater than
   `clip_hillslope_length` is shortened to exactly that value.
2. Each OFE at or below the configured value keeps its original length.
3. The point count, normalized distance coordinates, slopes, aspect, format
   version, OFE count, and optional 2023-format starting elevation remain
   unchanged.
4. The slope file's shared width is multiplied by the ratio of original total
   OFE length to clipped total OFE length. Therefore shared width multiplied by
   total OFE length, the representative hillslope area, remains unchanged.

For a single-OFE file this is the existing area-preserving behavior. For a
multiple-OFE file the configured limit applies per OFE, not to the combined
hillslope length. A five-OFE slope file may therefore remain longer than the
configured value in total even though every individual OFE satisfies the
limit.

## Validation and Failure Behavior

Preparation requires a finite, positive effective clip length when clipping is
enabled. A persisted zero, negative, NaN, or infinity is invalid runtime state.
The existing `run-wepp` request remains accepted and enqueued for request
compatibility, but asynchronous preparation fails with `ValueError`; polling
reports terminal `failed` status and `jobinfo` supplies `exc_info` according to
`docs/schemas/rq-response-contract.md`. This is an expected user-reachable
failure with recovery guidance to resubmit using a finite positive length.

A malformed slope file is exceptional generated/source-state corruption.
Preparation fails the asynchronous job with its parsing exception, exposed by
the same polling contract. The transform must parse and validate the complete
source, write a same-directory temporary file, and call `os.replace` only after
the temporary write is complete. It cleans the temporary file after write or
replace failure. Thus invalid input cannot publish a partial transform, a prior
complete destination remains on failure, and replacing a prior hardlinked
destination never mutates the source inode.

The source is the established application-generated directory-backed run input.
Archive-only and mixed run-input roots remain unsupported and fail through the
canonical run-input projection guard; this package does not reintroduce archive
materialization. Source relative paths and destination IDs remain derived from
the existing watershed summary and translator. That trusted generated-state
boundary and its existing symlink policy are unchanged and are not newly
claimed as hostile-input containment by this contract.

The stored checkbox value is exposed through a dedicated configured-value
accessor for WEPP prep and UI display. The existing effective
`Watershed.clip_hillslopes` behavior remains unchanged for watershed abstraction,
AgFields, and every non-WEPP-prep consumer.

## Compatibility

This change does not rename persisted fields, request keys, or UI controls.
Valid single-OFE results retain their existing clipping behavior. Explicit
finite-positive validation hardens invalid single-OFE state: zero already fails
incidentally, while negative and non-finite values now fail without emitting
invalid geometry. Multiple-OFE runs that enable clipping intentionally receive
changed generated `wepp/runs/p*.slp` geometry; multiple-OFE runs with clipping
disabled remain byte-equivalent to the source slope geometry.

## Rationale

Users select a maximum hillslope clip length to bound the erosion transport
distance represented by an OFE. Applying the threshold to each OFE gives the
same meaning in single- and multiple-OFE runs, while shared-width scaling
preserves the contributing area represented by the complete hillslope.
