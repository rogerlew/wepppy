# Iterative First-Order Link Prune WP-09 Max Junctions Support (`--max_junctions`)

**Status**: Closed (2026-04-14)
**Timezone**: UTC

## Overview
This package adds `--max_junctions` support to IFOLP in `weppcloud-wbt` and defines WEPPpy cutover behavior to run IFOLP with `--max_junctions=3`. The goal is to preserve current retained IFOLP parity as baseline while extending pruning behavior to cap excessive junction fan-in.

## Objectives
- Add optional `--max_junctions` argument to `IterativeFirstOrderLinkPrune` (CLI + wrappers).
- Implement deterministic max-junction pruning behavior in IFOLP with explicit error-contract/test coverage.
- Add parity/regression evidence comparing retained baseline vs `--max_junctions=3` behavior.
- Update WEPPpy integration planning docs to make `--max_junctions=3` explicit for emulator cutover.
- Close with mandatory test and code-review phases, including findings disposition (no unresolved high/medium findings).

## Scope
This package is limited to IFOLP max-junction capability and integration planning updates.

### Included
- IFOLP spec and implementation-plan updates in `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/`.
- Rust tool and wrapper changes in `/workdir/weppcloud-wbt` for `--max_junctions`.
- WEPPpy work-package governance artifacts and execution tracking in this package.
- WEPPpy integration-plan update to include `--max_junctions=3` in target call contract.
- Required code review, tests, and parity/regression evidence.

### Explicitly Out of Scope
- Non-IFOLP algorithm refactors.
- Culvert path migration beyond documentation/planning updates.
- New baseline redefinition without explicit parity disposition approval.

## Stakeholders
- **Primary**: WEPPcloud WBT maintainers.
- **Reviewers**: IFOLP maintainers and WEPPpy topology maintainers.
- **Security Reviewer**: not required for this package scope.
- **Informed**: operators consuming IFOLP rollout plans.

## Baseline Contract (Required)
All parity/regression work must treat retained IFOLP behavior from WP-05/WP-06/WP-07/WP-08 as baseline unless explicitly re-baselined.

Retained artifact identity:
- Canonical hash: `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83`

## Success Criteria
- [x] `--max_junctions` accepted by IFOLP CLI/help and both Python wrapper surfaces.
- [x] `--max_junctions=3` behavior implemented and deterministic on fixture reruns.
- [x] IFOLP tests updated and passing, including max-junction edge cases.
- [x] Required test gate commands are executed and recorded in WP-09 closure notes.
- [x] Parity/regression evidence produced and dispositioned against retained baseline.
- [x] `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wepppy-integration-plan.md` explicitly defines WEPPpy target call with `max_junctions=3`.
- [x] Mandatory code review completed and findings dispositioned with no unresolved high/medium issues.

## Required Validation Phases

### Phase 1: Test Execution (Required)
- Run and capture outcomes for:
  - `cargo check -p whitebox_tools`
  - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`
  - `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`
- If wrapper behavior changes, include wrapper smoke/invocation evidence.
- Test phase must complete before review closure.

### Phase 2: Code Review and Disposition (Required)
- Perform independent review of implementation, tests, and contract docs.
- Disposition all findings by severity (`fixed`, `accepted-risk`, `deferred` with rationale).
- Closure gate: no unresolved high/medium findings.
- Record review evidence in WP-09 artifacts and tracker notes.

## Dependencies

### Prerequisites
- Completed IFOLP WP-00 through WP-08 packages.
- Existing IFOLP retained baseline artifacts under `/tmp/ifolp_wp05_remediate/run1` and `run2`.

### Blocks
- Future WEPPpy IFOLP cutover execution that requires max-junction-capped behavior.

## Related Packages
- **Depends on**: [20260413_ifolp_wp08_wrapper_release_readiness](../20260413_ifolp_wp08_wrapper_release_readiness/package.md)
- **Related**: [20260413_ifolp_wp05_topaz_parity_validation](../20260413_ifolp_wp05_topaz_parity_validation/package.md)

## Timeline Estimate
- **Expected duration**: 1-3 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: algorithm/tooling and planning scope; no auth/secrets/public boundary changes.
- **Security review artifact**: `N/A`

## References
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wepppy-integration-plan.md`
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`

## Deliverables
- `docs/work-packages/20260414_ifolp_wp09_max_junctions_support/package.md`
- `docs/work-packages/20260414_ifolp_wp09_max_junctions_support/tracker.md`
- `docs/work-packages/20260414_ifolp_wp09_max_junctions_support/prompts/completed/ifolp_wp09_max_junctions_support_execplan.md`
- WP-09 test execution evidence (commands + pass/fail outcomes).
- WP-09 review/disposition artifact(s) with severity and closure state.

## Closure Summary (2026-04-14 UTC)
- Implemented IFOLP `--max_junctions` support in Rust tool contract, Phase B behavior, tests, and both Python wrappers in `/workdir/weppcloud-wbt`.
- Required gates passed:
  - `cargo check -p whitebox_tools`
  - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (`77 passed`, `0 failed`)
  - `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`
- Retained baseline parity preserved for omitted `--max_junctions`:
  - run1/run2 canonical hash `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83`
  - byte-identical to retained `parity-report.final_effective.canonical.json` artifacts.
- Deterministic `--max_junctions=3` validation completed:
  - added deterministic phase test (`iterative_first_order_link_prune_phase_b_max_junctions_three_prunes_deterministically`)
  - run1/run2 parity canonical for `max_junctions=3` matched each other and hashed to the retained canonical hash for current fixtures.
- WEPPpy integration planning updated to require explicit `max_junctions=3`.
- Review closure gate passed with no unresolved high/medium findings (see `review_disposition.md`).

## Follow-up Work
- Final WEPPpy cutover package should consume this package’s `--max_junctions=3` contract and parity evidence.

## Kickoff Prompt
- Archived ExecPlan: `docs/work-packages/20260414_ifolp_wp09_max_junctions_support/prompts/completed/ifolp_wp09_max_junctions_support_execplan.md`
