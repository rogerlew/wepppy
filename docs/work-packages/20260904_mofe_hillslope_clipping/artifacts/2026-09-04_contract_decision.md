# Contract Decision: Per-OFE Multiple-OFE Hillslope Clipping

**Decision ID**: `MOFE-CLIP-01`  
**Recorded**: 2026-09-04 11:31 UTC  
**Starting implementation revision**: `6aae4616c`  
**Operator approval**: Roger Lew explicitly requested this behavior in the
Codex workspace conversation on 2026-09-04.

## Applicable Canonical Contracts

- `docs/standards/contract-first-change-standard.md`
- `docs/standards/parameterization-adr-standard.md`
- `docs/schemas/rq-response-contract.md`
- New domain contract:
  `docs/ui-docs/contracts/wepp-hillslope-clipping-contract.md`
- Decision record:
  `docs/adrs/ADR-0048-mofe-per-ofe-hillslope-clipping.md`

No existing canonical contract defined multi-OFE clipping semantics. Existing
user documentation described area preservation but warned that multi-OFE
applicability was limited.

## Exact Normative Delta

When clipping is enabled, the configured length is a per-OFE maximum for both
single- and multiple-OFE slope files. Longer OFEs are capped, shorter OFEs are
unchanged, and the shared width is scaled to preserve width times total OFE
length. Non-positive enabled limits fail explicitly. Disabled clipping remains
unchanged.

## Rationale and Alternatives

The rule makes one advanced option consistent across watershed
representations. A combined-hillslope cap was rejected because the operator
specified a per-OFE limit. No clipping was rejected because it leaves the
enabled option ineffective. Per-OFE widths are unavailable in this slope-file
format, so one total-area-preserving shared-width factor is used.

## Compatibility and Data Impact

No schema key, alias, type, default, or stored state changes. Existing run
directories remain readable. Newly prepared multiple-OFE `wepp/runs/p*.slp`
files change only when clipping is enabled. Valid single-OFE geometry is
unchanged; invalid negative/non-finite state is newly rejected before output.
This is a generated model-input mutation; acceptance therefore requires
downstream artifact inspection.

## Request and Flag Matrix

This package does not change request parsing. `hillslope_clip_length` has
precedence when both aliases are present, and Python integer conversion is
retained.

| Clip flag request | Length request | Persisted update and submission behavior |
| --- | --- | --- |
| Absent | Absent | Preserve both stored values; enqueue normally. |
| False | Absent, empty, boolean, or non-numeric | Persist false when supplied; do not update length; enqueue normally. |
| False | Integer-convertible | Persist false and parsed integer; enqueue normally; no runtime clipping. |
| True | Absent, empty, boolean, or non-numeric | Persist true when supplied, preserve existing length, and enqueue; runtime outcome follows the stored-state matrix. |
| True | Finite integer-convertible | Persist true and parsed integer, then enqueue; positive values clip and zero/negative values fail during asynchronous prep. |
| True | Numeric NaN or string `"nan"`, `"inf"`, or `"-inf"` | Existing integer parsing produces no update; preserve prior length and enqueue; runtime outcome follows stored state. |
| True | Numeric positive or negative infinity | Preserve the pre-existing exceptional synchronous `OverflowError`; no state update or enqueue occurs. Parser hardening is outside this package. |
| Either | Both aliases present; primary extracts a non-`None` value | Parse `hillslope_clip_length` and ignore the compatibility alias. A scalar empty primary is non-`None` and therefore produces no update without fallback. |
| Either | Both aliases present; primary is null or an all-empty collection | Fall back to and parse `clip_hillslope_length`. |

## Stored and Filesystem State Matrix

| Runtime state | Valid? | Required behavior |
| --- | --- | --- |
| Clip false; length absent, empty, valid, or invalid | Yes | Copy source geometry unchanged; unused length does not block the run. |
| Clip true; persisted finite positive length | Yes | Cap every OFE independently and preserve total area. |
| Clip true; persisted zero, negative, NaN, or infinity | No | Async prep raises `ValueError`; polling reports `failed`; do not publish partial transformed output. |
| Source directory-backed and well formed | Yes | Resolve through the canonical run-input boundary and atomically publish transformed output. |
| Source archive-only or mixed-root state | No | Preserve the canonical run-input projection rejection; do not create or replace the destination. |
| Source absent | No | Preserve established explicit missing-input job failure; do not create a destination. |
| Source present but empty or malformed | No | Fail exceptionally with the parsing error; prior complete destination may remain; publish no partial replacement. |
| Supported legacy single-OFE source | Yes | Preserve valid clipping math and output structure. |

## User-Reachable Error Policy

An enabled invalid effective length is an expected validation failure. The
already-enqueued job ends as `failed`; `GET /api/jobstatus/{job_id}` exposes the
terminal status and `GET /api/jobinfo/{job_id}` exposes `exc_info` under
`docs/schemas/rq-response-contract.md`. Recovery is to resubmit with a finite
positive length. Missing or malformed source slope data is exceptional run-data
corruption and uses the same terminal polling surface. Neither failure may
publish a partially transformed destination.

## Valid-State Summary

- Absent/never-used optional state: config defaults supply the existing clip
  boolean and length; behavior follows those values.
- Present-empty request length: no length update; use the prior persisted value.
- Populated enabled state: every OFE is capped independently and area is
  preserved.
- Populated disabled state: source slope geometry is copied unchanged.
- Supported legacy state: single-OFE clipping remains numerically equivalent;
  existing field aliases remain accepted.
- Malformed/hostile state: non-positive enabled length or malformed slope-file
  structure fails explicitly without publishing a partially transformed
  destination.

## Security Impact

High by repository default because a directory-backed input copy becomes a
transformed file write. Path selection, authorization, upload handling, secrets,
external calls, queue topology, and subprocess execution remain unchanged. A
dedicated security artifact and direct unmocked tests of directory-backed valid
input, archive-only/mixed rejection, malformed input, write/replace failure,
hardlink de-aliasing, and prior-destination preservation are required.

## Proposed Regression and Acceptance Evidence

Unit fixtures will cover mixed OFE lengths, all-short no-op geometry, exact
limit, non-positive limit, version/header preservation, and total-area
preservation. A multi-OFE preparation test will prove the enabled flag reaches
the generated `p*.slp` boundary. A direct RQ dependency test will prove an
invalid length or malformed input makes the aggregate root terminal-failed,
exposes the actionable child exception through `jobinfo`, and prevents
hillslope execution and downstream jobs. Existing rq-engine payload tests will
verify the unchanged request aliases. Forest acceptance will deploy an exact revision,
submit local `dainty-signature` through rq-engine with clipping enabled and a
60 m value, poll the job to completion, and verify every OFE in every hillslope
`p*.slp` is at most 60 m. Compare every source/generated pair for OFE count,
header/profile preservation, the per-OFE limit, and width-times-total-length
area within relative or absolute tolerance `1e-9` before accepting the run.

## Implementation Status

Conformance is pending. This artifact and its contract reviews must be committed
as a standalone ancestor before production implementation edits.
