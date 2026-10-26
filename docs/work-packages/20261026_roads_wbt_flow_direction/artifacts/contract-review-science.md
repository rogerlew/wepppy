# Independent contract review: science and regression

Reviewer: `/root/science_review`. Date: 2026-10-26.
Scope: Roads flow-direction contract, package and ExecPlan; read-only inspection of
Roads caller, native adapter, Peridot conversion and tracer. No implementation edits.

## Verdict

**PASS for contract checkpoint.** No scientific or compatibility blocker in the
proposed bounded correction. This approves intended behavior and its acceptance
gates, not implementation, binary publication, production deployment or an
unexecuted project result.

The conversion values agree with the tracer's actual row/column offsets for all
eight directions. WBT and TOPAZ share several numeric codes with different
meanings, so accepting a code as valid cannot establish its encoding. Explicit
`wbt=True` from the WBT-only Roads caller is scientifically preferable to value
inference. Reusing Peridot's existing conversion changes representation without
changing terrain, flow routing algorithms, receiving-channel rules, hydrologic
parameters or road eligibility.

The keyword-only native `wbt=False` default preserves legacy TOPAZ callers and
existing positional parameters. Conversion of the loaded buffer preserves source
rasters. The helper maps undefined codes to zero, which the existing tracer
terminates as `invalid_flow_direction`; legacy mode must retain its current
behavior. Missing inputs, seed/shape errors, loop/edge/step guards and channel
recognition remain separately testable obligations. A channel seed can succeed
without consuming a direction, as in the existing tracer; do not accidentally
change that precedence while testing invalid directions.

## Review observations and acceptance conditions

- Peridot conversion-arm compass comments are misleading, although numeric
  mappings and the neighbor diagrams agree with the contract. Tests must assert
  independently specified coordinates, distances and slopes, not merely compare
  the adapter with the same helper or copy its comments. The contract already
  requires independent neighbor expectations. This is a documentation hazard,
  not evidence that the conversion values are wrong.
- Preserve the distinction between correcting encoding and validating physical
  routing. Five recovered channel traces and 35 completed segments are expected
  acceptance outcomes, not yet measured proof. The four NoData exclusions must
  remain excluded; this repair does not authorize snapping them into a basin.
- Real GDAL/Python-extension tests must exercise all eight WBT directions,
  overlapping codes and invalid values, alongside unchanged default TOPAZ
  behavior. A real invalid-value raster checks reader coercion as well as the
  tracer. The paired extension must be identified in a fresh process; a Python
  mock cannot establish the native encoding boundary.
- Fresh isolated project artifacts must prove recovered segments proceed through
  profile generation, PASS combination, watershed execution and report/receipt
  readers. Check accounting and finite outputs under existing contracts, plus
  unchanged baseline and original-source hashes. Correct tracing alone cannot
  establish successful hydrologic integration.

These conditions are already covered by the proposed plan and contract. No new
scientific parameterization ADR is needed for this representation-only change.
Any implementation that changes terrain, eligibility, accounting or routing
physics exceeds this approval. Production rollout and original-project repair
remain excluded.

## Publication scope addendum

The reported whole-file `roads.py` fingerprint change must remain visible. A
reviewed source-delta receipt and explicit stale full-project coverage notice can
preserve historical 516-profile results without claiming those results validate
new routing coverage. Retain historical counts and original source/binary hashes;
do not silently rebind them to the new source. The isolated project acceptance
supplies separate evidence for recovered routing and integration. This position
assumes implementation remains trace-boundary-only: changes to profile generation
or the model execution path would require reassessing the historical suite's
applicability. Publication tests should verify the precise acknowledged delta and
stale scope, rather than broadly disabling fingerprint checks.
