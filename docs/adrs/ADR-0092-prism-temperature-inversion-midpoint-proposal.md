# ADR-0092: Proposed midpoint repair for PRISM temperature inversions

## Status

Proposed; evaluated on retained EDDE climates. No production parameterization change is made by this ADR or its study script.

## Decision provenance

Decision venue: operator/Codex conversation, 2026-10-13, America/Los_Angeles; records use UTC. Participants: repository operator and Codex. Decision owner: operator for scientific adoption; Codex proposes the bounded implementation. Implementer: Codex, candidate evaluation only. Operator request: “we should figure out how to patch this.” This supersedes documentation-only investigation scope, without claiming explicit operator selection of a numerical formula.

## Context

PRISM spatialization adds separate monthly normal differences to daily Tmax and Tmin. Their difference can shrink a narrow daily range below zero. The retained Cascade pair shrinks January/December ranges by 0.5 C; three 20-year EDDE revisions produced 15 inverted days, up to 0.5 C. This is a generic transfer-function issue, not a missing-data issue or an EDDE-specific defect.

The deployed daily climate writer is Rust `wepppyo3/cli_revision/src/lib.rs:rust_cli_revision`, called by `wepppy/nodb/core/climate_build_helpers.py:cli_revision`. Breakpoint files use the Python branch of that helper. The public Python `wepppy/climates/prism/__init__.py:prism_revision` and experimental `wepppy/climates/edde/cligen.py:revise_prism` are separate paths. A complete fix must give all four paths the same rule without replacing the owned Rust writer with Python postprocessing.

## Proposed transformation

Keep existing PRISM adjustments. For adjusted extrema `a = Tmax` and `b = Tmin`, leave the pair unchanged if `b <= a`. Otherwise set both to `a/2 + b/2`, before existing CLI serialization. Reject nonfinite input; do not use this rule to conceal invalid source metadata or unrelated failures. Equality is allowed; add no arbitrary positive minimum daily range.

The rule preserves the arithmetic midpoint of the two daily extremes before serialization (not a claim about true time-integrated daily mean). It is the smallest squared change to the adjusted pair subject to Tmin <= Tmax. For an inversion of size d, each extreme moves d/2. Only invalid days change. Existing 0.1 C output rounding can move the written midpoint by up to 0.05 C.

Monthly Tmax/Tmin means are no longer exactly the original additive-offset targets: Tmax increases and Tmin decreases by the summed half-inversions divided by the monthly sample count. Measure and disclose this drift rather than claiming exact monthly preservation. Corrections in historical/future periods can differ, so exact change-signal preservation is not promised where repairs occur.

## Alternatives considered

- Raise Tmax to Tmin or lower Tmin to Tmax: changes one extreme by the full inversion and shifts the daily midpoint. No evidence favors one extreme.
- Swap the extrema: preserves midpoint but moves each by the full inversion and turns an invalid negative range into a positive range of the same magnitude. This is a larger change without physical evidence for that range.
- Add a positive range floor: introduces an unsupported threshold and changes the correction according to an arbitrary range choice.
- Scale daily temperature range by the ratio of target/reference normal ranges: maintains ordering for positive normal ranges, but changes every day's temperature variability and is a broader spatialization-method change.
- Redistribute repairs across other days to force exact monthly means: couples otherwise valid days and adds an unvalidated temporal adjustment. Not justified before the smallest correction is evaluated.
- Continue rejecting: explicit and safe for research but leaves otherwise usable future climates unavailable for a small number of affected days.

## Evidence and implementation acceptance

The [candidate evaluation](../work-packages/20261013_edde_v2_feasibility/artifacts/evaluate_prism_inversion_patch.py) uses hash-verified source archives and frozen hillslopes, creates new standalone output directories, and compares repaired and unrepaired files through the same serializer. It checks unchanged valid days and non-temperature fields, exact dates, ordered finite temperatures, daily midpoint, monthly mean drift, and fresh WEPP consumption of all previously rejected cases. Results: 24 revisions checked; 15 corrected days in three formerly rejected climates; all three repaired climates pass fresh 20-year WEPP execution. All 21 prior accepted revision DataFrames match exactly. Maximum per-extreme repair is 0.25 C before output rounding. The largest written calendar-month mean perturbation is 0.00968 C; the largest 20-year monthly mean perturbation is 0.000968 C. The previously validated historical/future pairs are unaffected; missing Cascade historical generation prevents equivalent paired claims there. Results belong to the candidate, not to the unchanged production writers.

Before production adoption, amend the canonical spatialization contract and implement the rule in the Rust writer and all Python paths. Add parity tests for valid, equal, inverted, negative-temperature, rounding-boundary, and nonfinite cases; verify daily and breakpoint outputs through their real serializers. Retain correction counts/magnitudes in normal workflow observability without inventing a new hidden artifact location or changing public return types casually. The EDDE manifest should identify the repair and its measured effects. Run existing regression gates and an actual generated-to-consumed WEPP artifact check with the built Rust extension.

## Risk and rollback

Zero daily range must be checked with actual WEPP consumption; candidate evidence covers only the retained cases. This does not correct source-model bias or future auxiliary fields. The old EDDE rejection behavior and generic spatialization formulas remain active until implementation is completed. If a future implementation changes valid days, precipitation, other climate fields beyond existing serialization, or introduces nonfinite output, revert the formula patch and preserve its diagnostics. Existing successful projects are not rebuilt as part of this evaluation.
