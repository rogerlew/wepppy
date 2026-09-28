# SUDI-03 independent contract security review

Reviewer: `/root/review_7777_security`. Date: 2026-09-28.
Starting revision: `50495bfeebf5ccf3c8cf50753100803e35bb5382`.

## Verdict

**Pass for the preimplementation contract checkpoint.** No unresolved security
contract findings or accepted exceptions. This approves the bounded implementation
proposal; final security approval requires implementation and artifact evidence.
No runtime files were changed by this reviewer.

## Scope and evidence

Reviewed the package, active ExecPlan, contract decision, canonical Single
User-Defined inputs contract (Upload interface and validation), and ADR-0075
SUDI-03. Inspected existing strict validation and preserving WSU parsing/writing,
the provided `/tmp/boulderck_mica_1_7777.sol`, and native
`/workdir/wepp-forest/src/input.for` record branches.

The proposed eight-field header, ten-field layers and three-field restrictive
record match the owned parser and native 7777 read layout. Profile anisotropy
belongs to the restrictive record; introducing a per-layer anisotropy field or
treating 7777 as the six-field 2006 layout would desynchronize native reads.
Explicit format dispatch in the strict validator and preserving serializer is
the appropriate bounded change. The supplied file uses CRLF and two layers;
its restrictive record is `1 10 0.46`.

## Threat model and noninterference

An authorized uploader controls soil bytes, counts, labels and numeric values.
The expanded parser admission reaches a native executable and remains a high
security-impact surface. Require exact record consumption, bounded counts,
native-compatible labels, finite representable numbers and native increasing
depths before publication and after serialization. Existing common helpers
already implement these rules; 7777 must pass through them unchanged.

The amendment changes no authorization, CSRF, request fields, multipart limits,
filename/path handling, immutable source publication, locking, source metadata
shape, reuse, archive/restore, or error envelope. Invalid replacements retain
the prior accepted source. Existing formats and ordinary catalog/Disturbed
serialization stay unchanged. The opt-in policy and independent mode selection
continue to govern entry into preservation; uploaded labels confer no authority.

## Required final evidence

- Reject 7777 missing/extra header, layer and restrictive fields; malformed
  labels, native control tokens, nonfinite and nonrepresentable numbers,
  reversed hydraulic fractions, nonpositive density and nonincreasing native
  depths. Exercise accepted 10 layers and rejected 11 layers.
- Confirm source publication records canonical version `7777`, preserves raw
  bytes/hash, and retains the previous source on rejected replacement. Exercise
  authenticated multipart handling with the provided file.
- Inspect all ten layer fields, profile anisotropy, ksflag and version in
  consumed single/MOFE files, including compatible modifiers and 32 OFEs.
- Run fresh pinned native execution and inspect finite, nonempty result
  artifacts. Native code references layer-anisotropy work arrays in shared
  averaging paths despite the 7777 branch not reading per-layer anisotropy;
  this is a native acceptance risk requiring evidence, not a reason to invent
  an uploaded field or silently migrate the format.
- Retain regression evidence for previously supported uploads and ordinary
  non-upload paths. Review actual changed surfaces and contract-checkpoint
  ancestry before closure; deployment remains separate.
