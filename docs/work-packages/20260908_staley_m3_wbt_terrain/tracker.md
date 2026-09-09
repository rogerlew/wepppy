# Tracker — Staley M3 WBT Terrain

## Quick Status

**Started**: 2026-09-08 23:30 UTC
**Last updated**: 2026-09-09 02:08 UTC
**Phase**: Closed; all required gates and independent reviews passed
**Security impact**: high; dedicated review required and recorded

## Task Board

- [x] M1: User adopted maximum upstream raw elevation minus outlet elevation; ADR-0052, CLI contract and predeclared protocol recorded.
- [x] M2: Rust traversal, registration, both bindings, analytical and generated-output tests implemented.
- [x] M3: Final rebuilt binary and both bindings verified; pinned reference differences explained.
- [x] M4: 24 paired comparisons and 864 M3 scenarios completed; recommend genuine 10 m for initial support.
- [x] M5: Final validation/review sign-off complete; durable docs promoted and prompts archived.

## Decisions and Rationale

The user authorized WBT ownership and a resolution study, then explicitly
adopted the physical maximum-minus-outlet formula after reviewing pfdf's
analytical failure. [ADR-0052](../../adrs/ADR-0052-staley-m3-upstream-terrain.md)
records the accepted formula and why highest-source and max-minus-min
alternatives were rejected. The 10 m recommendation follows the predeclared
engineering screen; no arbitrary 30 m size exemption or production UI rule
was introduced. Implementation is independent of GPL reference code/tests.

## Findings and Evidence

[Resolution decision](artifacts/resolution_decision.md): controlled effects reach
10.598 probability points and 12.479% inverse-threshold change. Both controlled
and native sets fail at two of 12 outlets; all 24 masks have no detected
edge/NoData contact. Main-outlet agreement alone conceals headwater failures.
Native matching can delineate different catchments despite nearby centers.

[Reference comparison](artifacts/reference_parity.md): pfdf 3.0.2/pysheds 0.4
fails a monotonic-chain physical expectation. The rebuilt owned tool produces
30 m / 300 m2 at all three diagnostic outlets. Calibration-preprocessing
parity is not established or claimed.

The final study workspace is `/tmp/staley-m3-terrain-study/study-v4/`.
Input fixtures remain unchanged; no branch changes, commits, runtime binary
installation, production wiring or live-run mutations occurred.

## Validation and Reviews

[Validation](artifacts/validation.md) records commands, hashes and limitations.
WBT has 152 passing app Rust tests and 15 passing Python tests, including
11 CLI/binding regressions and two study-matching regressions. Raster checks
cover 42 integration cases and one documentation example. Independent
[correctness review](artifacts/20260908_correctness_review.md) closed five
findings; [security review](artifacts/20260908_security_review.md) closed two.
The broad WEPPpy gate passed: 7742 tests passed, 72 skipped. Documentation,
spelling previews, links and both repository diff checks passed.

## Remaining Scope

Package execution is complete; archived prompts record final outcomes.
Production postfire integration, soil readiness, availability enforcement,
deployment and vendoring remain separate work. No unresolved scientific
choice blocks this engineering tool or its conservative resolution recommendation.
