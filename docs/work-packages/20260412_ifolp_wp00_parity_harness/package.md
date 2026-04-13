# Iterative First-Order Link Prune WP-00 Parity Harness

**Status**: Closed (2026-04-13)
**Timezone**: UTC

## Overview
This package prepares and governs end-to-end execution of WP-00 for the Iterative First-Order Link Prune effort in `/workdir/weppcloud-wbt`. The outcome is an execution-ready, procedure-compliant work package with an active ExecPlan that a coding agent can run to produce parity fixtures, TopAZ oracle artifacts, and deterministic comparison harness outputs.

## Objectives
- Provide a WEPPpy work-package-compliant execution surface for WP-00.
- Define explicit WP-00 deliverables, validation gates, and evidence requirements.
- Supply an active ExecPlan prompt that can be executed without additional planning.
- Track status, decisions, and handoff notes for multi-agent continuity.

## Scope
This package covers orchestration and execution guidance for WP-00 in `weppcloud-wbt`.

### Included
- Work-package scaffold (`package.md`, `tracker.md`, `prompts/active`).
- Active ExecPlan for WP-00 parity harness execution in `/workdir/weppcloud-wbt`.
- Integration of this package into `PROJECT_TRACKER.md`.
- Cross-reference updates in `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`.

### Explicitly Out of Scope
- Implementing WP-01+ (tool scaffolding and algorithm code).
- WEPPpy runtime integration changes.
- Closing the full iterative-first-order-link-prune initiative.

## Stakeholders
- **Primary**: WEPPcloud WBT maintainers.
- **Reviewers**: Stream-network tooling maintainers and parity reviewers.
- **Security Reviewer**: Not required for this orchestration-only package.
- **Informed**: WEPPpy maintainers coordinating multi-agent execution.

## Success Criteria
- [x] Work package scaffold exists and is linked from `PROJECT_TRACKER.md`.
- [x] Active ExecPlan prompt exists for WP-00 end-to-end execution.
- [x] WP-00 deliverables and validation gates are explicit and unambiguous.
- [x] WP-00 implementation run is completed and evidence artifacts are produced in `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/`.
- [x] WP-00 orchestration row is updated to `done` with review/test/parity gates completed.

## Dependencies

### Prerequisites
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`
- Real-world fixture anchor: `/wc1/runs/cl/clueless-aftertaste/dem/wbt`

### Blocks
- WP-01 start in `weppcloud-wbt` should wait for WP-00 completion evidence.

## Related Packages
- **Depends on**: None.
- **Related**: `docs/work-packages/20260403_roads_map_drilldown/package.md` (active execution baseline pattern).
- **Follow-up**: New package for WP-01+ implementation if split ownership is needed.

## Timeline Estimate
- **Expected duration**: 1-2 sessions for WP-00 execution once agent is assigned.
- **Complexity**: Medium.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: package is orchestration/documentation for offline parity harness work; no auth/secrets/public route surface changes.
- **Security review artifact**: `N/A`

## References
- `docs/work-packages/README.md` - WEPPpy work-package process.
- `docs/prompt_templates/codex_exec_plans.md` - ExecPlan standard.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md` - Algorithm contract.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` - Work-package sequence and WP-00 scope.

## Deliverables
- `docs/work-packages/20260412_ifolp_wp00_parity_harness/package.md`
- `docs/work-packages/20260412_ifolp_wp00_parity_harness/tracker.md`
- `docs/work-packages/20260412_ifolp_wp00_parity_harness/prompts/completed/ifolp_wp00_parity_harness_execplan.md`
- `PROJECT_TRACKER.md` entry in In Progress.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/fixture-catalog.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/topaz-oracle-manifest.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/parity-metrics-spec.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/determinism-report.md`
- `/workdir/weppcloud-wbt/tools/ifolp_wp00_prepare_fixtures.py`
- `/workdir/weppcloud-wbt/tools/ifolp_wp00_run_topaz_oracle.sh`
- `/workdir/weppcloud-wbt/tools/ifolp_wp00_compare_outputs.py`

## Follow-up Work
- Start WP-01 (tool scaffolding and registration) using the WP-00 parity harness artifacts as baseline gates.
- Confirm threshold metadata provenance for inferred fixture pairs before WP-05 final parity sign-off.

## Closure Notes
**Closed**: 2026-04-13

**Summary**: WP-00 was completed end-to-end in `/workdir/weppcloud-wbt` with clean-room TopAZ-oracle staging, checksum-pinned fixture manifests, reusable harness utilities, and deterministic rerun proof. The WBT orchestration table now marks WP-00 as `done` with review/test/parity gates complete.

**Lessons Learned**:
- Canonical parity reports are required for reproducibility checks because full reports include run-root metadata.
- Early fixture/oracle pinning reduced ambiguity and simplified downstream parity gating.

**Archive Status**: ExecPlan retained under `prompts/completed/`; package preserved for historical traceability.
