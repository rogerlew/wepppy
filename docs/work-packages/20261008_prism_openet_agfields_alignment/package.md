# Historic PRISM OpenET and AgFields alignment

Status: active, 2026-10-08 UTC. Owner: Codex with operator authorization.

Enable historic PRISM mode 16 in two existing downstream climate gates and
verify monthly OpenET/WEPP dates and AgFields parent climate inheritance for
both spatial methods. Canonical behavior is in
`docs/schemas/prism-downstream-eligibility-contract.md`.

Complexity budget: two allowlist additions, focused regressions, bounded artifact
checks and documentation. No new infrastructure or parameterization. Security
impact: low; dedicated security review not required because no authorization,
identity, grants, persistence or filesystem boundary changes are intended.

Acceptance: valid/invalid eligibility tests, three real OpenET hillslope samples,
calendar joins to both archived PRISM WEPP outputs, and native AgFields execution
using prepared parent PRISM files. Record external limitations explicitly.
Production deployment and enabling features for additional accounts are excluded.
