# Ablation Protocol Tooling Port

**Status**: Closed (2026-05-02)
**Timezone**: UTC

## Overview
This package ports the established ablation incident tooling contract into `wepppy` by adding `tools/ablation_protocol.py`, targeted tests, and package-level review evidence. The outcome is a reproducible `init/finalize` workflow for ablation incident folders with explicit schema/policy validation and artifact indexing.

## Objectives
- Add `tools/ablation_protocol.py` with `init` and `finalize` subcommands.
- Add regression tests for incident scaffolding, manifest/checksum generation, and policy-era validation gates.
- Capture code review and verification evidence in the package tracker/artifacts.
- Register the package in `PROJECT_TRACKER.md` for discoverability.

## Scope

### Included
- New tool implementation at `tools/ablation_protocol.py`.
- New regression suite at `tests/tools/test_ablation_protocol.py`.
- Work-package scaffolding (`package.md`, `tracker.md`, ExecPlan, artifacts).
- `PROJECT_TRACKER.md` update for package lifecycle visibility.

### Explicitly Out of Scope
- Backfilling or migrating historical ablation incidents.
- Running broad repository test gates beyond targeted tool validation.
- Refactoring unrelated ablation/triage tooling.

## Stakeholders
- **Primary**: WEPP/ablation operators working across `wepppy` and `wepp-forest`.
- **Reviewers**: Maintainers of `tools/` and `tests/tools/`.
- **Security Reviewer**: Not required unless scope expands into networked/runtime trust boundaries.
- **Informed**: Work-package owners consuming ablation campaign outputs.

## Success Criteria
- [x] `tools/ablation_protocol.py` exists and supports `init` and `finalize` flows.
- [x] `tests/tools/test_ablation_protocol.py` provides deterministic regression coverage for key policy gates.
- [x] Targeted tests pass via `wctl run-pytest tests/tools/test_ablation_protocol.py`.
- [x] Code-review notes and risk assessment are captured in package artifacts/tracker.
- [x] `PROJECT_TRACKER.md` includes this package with current status.

## Dependencies

### Prerequisites
- Existing repository test harness (`wctl run-pytest`).
- Existing ablation workflow references in work-package docs.

### Blocks
- Follow-on local ablation package automation work in `wepppy` that assumes this tool exists.

## Related Packages
- **Related**: [20260430_uncapped_spectacular_h2637_ablation_campaign](../20260430_uncapped_spectacular_h2637_ablation_campaign/package.md)
- **Related**: [20260502_mofe_flagged_hillslope_triage](../20260502_mofe_flagged_hillslope_triage/package.md)

## Timeline Estimate
- **Expected duration**: 1 focused session.
- **Complexity**: Medium.
- **Risk level**: Medium (policy-validation logic can be brittle if contracts drift).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: local CLI and filesystem workflow only; no auth/session/secrets or public route attack-surface changes.
- **Security review artifact**: `N/A`

## References
- `/workdir/wepp-forest/tools/ablation_protocol.py` - source-of-truth implementation contract being ported.
- `/workdir/wepp-forest/tests/test_ablation_protocol.py` - upstream regression scenarios.
- `docs/work-packages/README.md` - package lifecycle/process requirements.

## Deliverables
- `tools/ablation_protocol.py`
- `tests/tools/test_ablation_protocol.py`
- `docs/ablation/TEMPLATE_incident.md`
- `docs/ablation/TEMPLATE_notes.md`
- `docs/ablation/TEMPLATE_matrix.csv`
- `docs/ablation/TEMPLATE_artifacts.md`
- `docs/ablation/README.md`
- `docs/work-packages/20260502_ablation_protocol_tooling/tracker.md`
- `docs/work-packages/20260502_ablation_protocol_tooling/prompts/completed/ablation_protocol_tooling_execplan.md`
- `docs/work-packages/20260502_ablation_protocol_tooling/artifacts/20260502_code_review.md`

## Follow-up Work
- Optional: add local policy companion docs (`protocol.md`, watchlist, artifact-policy guardrail docs) if the workflow becomes fully repo-native in `wepppy`.

## Closure Notes

**Closed**: 2026-05-02

**Summary**: Ported the ablation protocol tool and upstream regression suite from `wepp-forest`, adapted test harness pathing/markers for `tests/tools`, and validated with `wctl run-pytest tests/tools/test_ablation_protocol.py` (`17 passed`). Added local `docs/ablation/TEMPLATE_*` files plus a short README so the tool default root works in this repository.

**Lessons Learned**: Existing work-package references already encoded a stable contract; porting implementation+tests together minimized drift and removed ambiguity.
