# MOFE Flagged Hillslope Triage for Ablation Campaigns

**Status**: Open (2026-05-02)
**Timezone**: UTC

## Overview
This package operationalizes triage of MOFE closure-audit flagged hillslopes from the `wepp_260501` replay validation set. The goal is to classify defect signatures, select representative seeds, and produce an ablation-ready campaign matrix without rerunning WEPP or changing model code.

## Objectives
- Build normalized triage tables from existing validation artifacts and run-context metadata.
- Assign deterministic defect families and validate them with an unsupervised cluster cross-check.
- Produce representative seed manifests and an ablation campaign matrix with clear pass/fail observables.
- Provide complete package-local artifacts so downstream ablation work can start without re-deriving context.

## Scope

### Included
- Package scaffolding, tracker, and active ExecPlan under `prompts/active/`.
- Artifact generation under `artifacts/` (`triage_table_*`, taxonomy outputs, seed manifest, precedent crosswalk, campaign matrix, defect family summary).
- Read-only consumption of validation artifacts from `docs/mini-work-packages/20260502_rq_replay_mofe_260501_validation/artifacts/`.
- Crosswalk against existing ablation incidents under `/workdir/wepp-forest/docs/ablation/`.

### Explicitly Out of Scope
- Changing WEPP/MOFE model physics or thresholds.
- Re-running full WEPP pipelines for this package.
- Opening or executing downstream ablation incidents (this package prepares inputs only).

## Stakeholders
- **Primary**: Hydrology/model QA maintainers triaging MOFE closure anomalies.
- **Reviewers**: WEPPcloud operators and ablation workflow maintainers.
- **Security Reviewer**: Not required unless scope expands into auth/session/secrets/queue surfaces.
- **Informed**: Operators monitoring post-restart replay stability.

## Success Criteria
- [ ] Work-package artifact directory contains complete M1-M6 outputs defined by the active ExecPlan.
- [ ] Every flagged hillslope has `family_primary` and rationale in `taxonomy_assignments.csv`.
- [ ] `representative_seeds.csv` and `campaign_matrix.csv` are sufficient to bootstrap ablation incidents.
- [ ] `precedent_crosswalk.md` and `defect_families.md` capture triage conclusions and next-step recommendations.
- [ ] Tracker and ExecPlan are fully updated with decisions, surprises, and closeout notes.

## Dependencies

### Prerequisites
- Validation artifacts from `docs/mini-work-packages/20260502_rq_replay_mofe_260501_validation/artifacts/`.
- `/wc1/runs` mounted for run-context and staged-input checks.
- `/workdir/wepp-forest/docs/ablation/protocol.md` and `/workdir/wepp-forest/tools/ablation_protocol.py`.

### Blocks
- Follow-on ablation packages that consume the seed/campaign matrix outputs.

## Related Packages
- **Depends on**: [20260502_rq_replay_mofe_260501_validation](../../mini-work-packages/20260502_rq_replay_mofe_260501_validation/README.md)
- **Related**: [20260430_hillslope_mofe_daily_closure_audit](../20260430_hillslope_mofe_daily_closure_audit/package.md)
- **Related**: [20260430_uncapped_spectacular_h2637_ablation_campaign](../20260430_uncapped_spectacular_h2637_ablation_campaign/package.md)

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium (classification quality and precedent mapping correctness).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Data-analysis and documentation workflow using existing artifacts; no auth/session/secrets/route attack-surface changes.
- **Security review artifact**: `N/A`

## References
- `docs/work-packages/20260502_mofe_flagged_hillslope_triage/prompts/active/mofe_flagged_hillslope_triage_execplan.md` - Active execution plan.
- `docs/mini-work-packages/20260502_rq_replay_mofe_260501_validation/artifacts/` - Source validation evidence.
- `/workdir/wepp-forest/docs/ablation/protocol.md` - Ablation lane/incident contract.

## Deliverables
- Final package-local artifacts produced by M1-M6 in `artifacts/`.
- Updated tracker and ExecPlan with execution record and closeout.

## Follow-up Work
- Open one or more ablation execution packages by defect family once campaign matrix is accepted.
