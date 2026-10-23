# Tracker

Status: closed 2026-10-23; implementation and validation complete.

- [x] Inspect disturbed suite, Roads generators, site inputs and Usersum pipeline.
- [x] Review and commit suite/publication contract checkpoint `c4774cf2a`.
- [x] Implement portable fixtures, matrix, analysis and freshness tests.
- [x] Execute matrix and isolated design checks; retain full-unrutted rejection and qualified positive subset.
- [x] Vendor/link report and validate actual Usersum rendering.
- [x] Final reviews/gates, task-scoped commits and closure.

2026-10-23 UTC: source climate contains 16 years despite a 100-year header.
Median site segment length is only about 2.62 m; include short/median/long geometry
controls and report this limitation. Source project remains read-only. Unrelated
UI-lab, infrastructure and code-quality changes are excluded.

Reviewed checkpoints: suite/publication `c4774cf2a`; management reference repair
`5ebc3b0ff`; full-upload negative plus bounded unrutted subset `fa5c40a76`.
Production changes preserve plant references and remove one non-data soil token.
Three full-upload additive checks and the explicitly limited unrutted positive
check pass; negative control retains two failures and no current receipt.
Final review added production grade clamping, management semantic readback,
staged-input identities, project evidence revalidation and unavailable ratios.
The final source-bound matrix is retained at `/tmp/roads-matrix-verified-oct23`.

Final matrix: 516 passed in 361.05 seconds. Independent native audit confirms
3,015,504 PASS rows and 6,942,672 WAT rows. Publication/Usersum gate: 68 passed.
Actual forest HTTPS report, navigation, guide and vendor URLs return 200; vendor
copy is byte-identical. Broad regression follows the implementation freeze.

Closure: implementation `a501c15cc`; independent reviews approve with no unresolved
high/medium findings. Broad regression: 11,647 passed, 131 skipped in 3,270.42 s.
See [validation evidence](artifacts/20261023_validation.md). Durable rules live in
[the suite contract](../../schemas/roads-validation-suite-contract.md); reproducible
commands live in [the suite README](../../../tests/roads/README.md).
