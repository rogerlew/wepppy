# Correctness and User-Experience Review — Staley watershed engine

## Metadata

- Package: `20260908_staley_watershed_engine`.
- Reviewer: independent read-only Codex reviewer `/root/staley_correctness`.
- Date: 2026-09-09 UTC; recorded by the implementing agent from reviewer findings.
- Context: `master`, baseline `db03285e986c7d42afb65434429e02eff66a2b48`, working tree.
- Scope: scalar engine/tests, examples/generator, coefficient/watershed audits,
  specification, accepted engine contract and ADR-0056.
- Canonical intent: engine contract “Scope and interfaces,” “Forward
  calculation,” and “Inverse equality and numerical policies”; specification
  “Scientific Model” and “Project Watershed Assessment Scope”; ADR-0056.
- Security impact remains none for the in-memory engine; no separate security
  review is required. Audit scripts are offline trusted-fixture evidence only.

## User Outcome

Explicit prepared predictors produce finite probabilities or structured inverse
equality results with correct duration-specific accumulation/intensity units.
Invalid inputs raise argument-specific exceptions. Unavailable/nonunique inverse
results have absent numeric values. Calls are stateless: no partial writes,
project loading, network, UI or queue operations.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Project state absent | Yes | Operate on supplied predictors | Direct numerical tests |
| Project artifacts empty/incomplete | Outside scope | No implicit reads/fallback | Engine source |
| Prepared predictors | Yes | Explicit model/duration evaluation | Six-row Decimal oracles |
| Zero response | Yes | Constant probability; nonunique/unavailable inverse | Constant-response tests |
| Legacy persisted state | N/A | Additive API, no migration | No persistence/schema changes |
| Malformed numeric inputs | No | Explicit rejection | Type/range/nonfinite tests |
| Frozen watershed fixture | Yes, audit only | Preserve source files | Container hashes/grid/outlet audit |
| Required fixture absent | No, audit only | Explicit filesystem failure | Direct required-path reads |

Input combinations were reviewed separately: models/durations, response signs,
zero/positive rainfall, invalid inputs, finite extremes, target endpoints,
adjacent-baseline targets and inverse representability.

## User-Reachable Error Policy

| Condition | Classification | Result |
| --- | --- | --- |
| Unsupported scalar type | Caller error | Argument-specific TypeError |
| Invalid range/model/duration/nonfinite input | Caller error | Argument-specific ValueError |
| Response/forward overflow | Numeric boundary | OverflowError |
| Unreachable side of baseline | Expected inverse outcome | negative_rainfall |
| Constant response, matching/different target | Expected inverse outcome | constant_probability / constant_probability_mismatch |
| Inverse/intensity overflow | Numeric boundary | arithmetic_overflow |
| Nonzero inverse rounds to zero | Numeric boundary | arithmetic_underflow |

The accepted contract justifies each result. Unavailable/nonunique outcomes
contain `None` numeric values, and available zero is reserved for baseline.

## Review Checks

- [x] Canonical intent is accepted contract/owner direction, not inferred tests.
- [x] State and input dimensions are assessed independently and scoped honestly.
- [x] Numerical boundaries are exercised directly without calculation mocks.
- [x] Existing auth, locking, persistence and workflows are unchanged.
- [x] Stateless failure/retry semantics and actionable errors are explicit.
- [x] No exhaustive binary64 or scientific-validation claim is made.

## Findings

| ID | Severity | Surface and evidence | Required action / disposition | Status |
| --- | --- | --- | --- | --- |
| COR-01 | Medium | Original M1/30 inverse for T=.4,F=.6,S=.3 and target one representable value below baseline returned positive rainfall about 9.10e-16; M3 examples returned zero. | Exact target/baseline reachability, centered log1p near baseline, all-row/both-sign regressions, matching contract/ADR clarification. Reviewer inspected and verified all changes. | Resolved |
| COR-02 | Low | Nonzero inverse could round to zero with response around 1e308. | Explicit arithmetic_underflow, absent numerics, signed extreme-response regressions and contract/ADR text. Reviewer verified. | Resolved |

## Validation Evidence

Reviewer ran container focused suite: **145 passed**, 9.30 s, two dependency
deprecation warnings. Additional read-only Decimal calculations covered **108
cases** at 0.5/0.75/1.25/1.5 times baseline and adjacent values across all rows
and both M1 response signs. Maximum relative inverse error: **1.296e-15**;
reconstruction and reachability assertions passed.

Reviewer independently reran the container watershed audit with WBT at
`/workdir/weppcloud-wbt`: seven hashes, 49,917 cells, grid identity, outlet
inclusion and polygon/subcatchment support match. Visual publication check
confirmed equations 4–6 and Table 4. Synthetic generator/output includes six
rows, independent Decimal arithmetic, q/x intermediates and edge statuses.
GPL pfdf sources/tests were not inspected.

## Verdict

Gate: **pass**. Unresolved findings: high 0, medium 0, low 0.
Reviewer recommendation: **ship-with-conditions**, requiring parent completion
of full-suite/documentation checks and tracking updates before package closure.
Sign-off: `/root/staley_correctness`, 2026-09-09 UTC.

Residual limits: binary64 reconstruction near baseline/saturation is approximate.
Real-project aggregation, scientific calibration and deployed workflows are
unvalidated. The manuscript/specification area-range discrepancy remains future
scientific-guidance work. See [validation](validation.md) for final parent gates.
