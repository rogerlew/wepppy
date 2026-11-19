# Native input capacity evaluation correctness review

Reviewer: Codex (self-review, not an independent review).
Date: 2026-11-19 UTC.
Scope: native prototype commit `fd7e0a5a6526ae217a58eb5bb2c491d75273610d`.
Authority: evaluation only. Production generated-soil contract remains
`docs/schemas/soil-horizon-boundary-contract.md#normative-behavior`.

## Outcome and failure class

The incident is input-horizon capacity exhaustion after property-preserving
200 mm insertion. Native input arrays originally shared a ten-layer limit with
calculation arrays. The evaluated reader accepts eleven input horizons without
expanding calculation storage. Actual generated-state inspection proves that
an influential eleventh horizon is used. Python's production writer still fails
at ten; this prototype is not an operational repair of the reported job.

## Coverage and review findings

Source-depth references before aggregation now use local input storage. Shared
`solth1` is populated by the original calculation-grid loop. Input-sized property
arrays use `mxhzin`; calculation flags, conductivity accumulators and output
arrays retain `mxnsl`. Initialization loops respect those separate dimensions.
Unit conversions, terminal extension, 1800 mm clipping, top-200-mm treatment,
property aggregation and restriction handling are unchanged.

Forty native tests include 9/10/11 horizons, eight format variants, multiple OFEs,
heterogeneous analytical aggregation, clipped/shallow profiles, and mixed count
and material ordering compared to isolated reads. Eighty old-capacity probes
match baseline state exactly. Full old-input hillslope outputs match bytewise,
including an active-runoff case and a three-OFE sixteen-year case. Bounds checks
exercise the real reader and dependencies; no physical calculations are mocked.

Counts 0 or above eleven stop explicitly. This changes the baseline behavior
for excess counts (previously silently discarded), and needs a documented
compatibility decision before production adoption, especially for uploaded soils.
No output-array expansion or binary pass schema change is introduced.

## Remaining acceptance boundaries

The prototype is suitable for completing a bounded native evaluation; it does
not establish an adequate national SSURGO input limit, arbitrary subdivision
invariance, physical accuracy below/above the existing depth clamp, Windows
release qualification, or end-to-end WEPPcloud recovery. The final evaluation
report records broader regression results. Production promotion additionally
requires a parameterization ADR, authoritative capacity/executable compatibility
contract, generated-artifact tests through raw/prepared/channel writers, paired
binary provenance, and an isolated replay of the original project workflow.
