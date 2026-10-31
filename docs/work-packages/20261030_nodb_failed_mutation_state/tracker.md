# NFMS-01 tracker

## Status

2026-10-31 UTC: discovery and contract checkpoint preparation. Implementation is
blocked until reviewed checkpoint receives standalone ancestor commit authority.
Active plan: `prompts/active/implementation_execplan.md`.
Checkpoint accepted by both independent reviewers; awaiting operator commit authority.
Ancestor revision: not yet created. No production implementation files edited.

## Evidence and decisions

- Starting master HEAD `2f2bd0ef49f7521f0b888c94d4cdd16e473de416` verified.
- Preserve dirty roads program active plan/tracker and untracked role assessment;
  ignore dirty usersum generated index.
- `wctl run-pytest tests/nodb/test_base_boundary_characterization.py --maxfail=1`:
  70 passed, 2 warnings, 11.45 seconds.
- Discovery-only `artifacts/baseline_probe.py`: one passed, 4 warnings, 9.30
  seconds. It asserts the defect: disk A after failure, held/cache B, unrelated
  C persists B and nested B. This is not a conformance test or fix evidence.
- Normative delta and rationale: `artifacts/20261030_contract_decision.md`.
- Consumer discovery: `artifacts/consumer_matrix.md`.

## Remaining work and ownership

Codex: independent contract reviews and scoped docs lint completed; disposition
in `artifacts/20261031_review_disposition.md`.
Operator: authorize only the prepared checkpoint commit when review is accepted.
Codex after that commit: implement, reproduce real consumer faults, validate
prepared inputs/resources/performance, complete independent correctness/security/QA
reviews and required gates. Preserve unresolved consumer rows until demonstrated.

No deployed repair, affected-run recovery or post-change signal exists yet.

## Final checkpoint evidence (2026-10-31 02:23 UTC)

Extended discovery probe: 2 passed, 4 warnings, 9.34 seconds; process exited 0.
Real Soils `_build_gridded` with missing SSURGO rejects after `_initial_sat=0.9`;
disk remains 0.2, held state is 0.9, unrelated save persists 0.9. No malformed HTTP
payload or validation bypass is involved. Warnings are existing deprecations and
unknown pytest marks because this artifact probe is outside tests/conftest.py.
This artifact deliberately asserts baseline defects and is not a conformance gate.

Two independent contract reviews approve after compensation wording and authority
inventory fixes. Production code and conformance tests remain untouched. No
performance/resource benchmark or prepared-input fix evidence yet. Scoped docs
lint and git diff whitespace checks pass. Concurrent roads artifacts appeared
during work and remain untouched.
