# ExecPlan: MOFE Flagged Hillslope Triage for Ablation Campaign Design

This ExecPlan is a living document. Update `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` as work proceeds.

## Purpose / Big Picture
We observed `requires_scientific_review` flags on a subset of hillslopes during MOFE closure validation. The next step is not immediate model surgery; it is triage:

1. understand the nature of flagged defects,
2. cluster them into actionable defect families, and
3. produce an ablation-campaign-ready grouping strategy.

Primary source artifacts:
- `docs/mini-work-packages/20260502_rq_replay_mofe_260501_validation/artifacts/hillslope_audit_rollup.csv`
- Per-hillslope summaries under that same artifact tree.

## Goal
Deliver a defensible defect taxonomy and candidate ablation campaign matrix so follow-on experiments can target root-cause classes instead of isolated outliers.

## Flagging Contract (Current)
A day is `requires_scientific_review=true` when late-OFE conditions trip thresholds in `tools/hillslope_mofe_daily_closure_audit.py`:
- late OFE window: `3`
- `late_max_abs_ofe_closure_residual_mm >= 100.0`
- `late_max_surface_pulse_proxy_mm >= 100.0`
- and if ratio is available: `late_max_qofe_to_q_ratio >= 2.0`

Hillslope-level flag = at least one flagged day.

## Scope
In scope:
- Derive hillslope-level and run-level defect classes from existing artifacts.
- Quantify prevalence, severity, and signature stability of each class.
- Identify a minimal ablation test set per class (representative hillslopes).
- Produce execution-ready campaign recommendations.

Out of scope:
- Implementing model fixes.
- Changing WEPP/MOFE equations or production thresholds.
- Re-running full WEPP pipelines unless needed for a small targeted verification subset.

## Deliverables
1. Triage dataset artifact with per-hillslope class labels and rationale.
2. Defect-family summary report with prevalence/severity table.
3. Candidate ablation campaign matrix:
   - class
   - hypothesis
   - representative hillslopes
   - expected observable signals
   - pass/fail criteria
4. Follow-on work-package recommendations (one per major defect family if needed).

## Progress
- [x] (2026-05-02) Work-package created.
- [ ] Build normalized triage table from existing rollup + summary JSONs.
- [ ] Define first-pass defect taxonomy and assign all flagged hillslopes.
- [ ] Validate taxonomy consistency on a random flagged sample.
- [ ] Produce ablation-campaign matrix and prioritization.
- [ ] Review and finalize recommendations.

## Proposed Triage Axes
Use these axes to group defects:
- Magnitude axis: `max_abs_closure_mm`, `max_abs_ofe_closure_mm` bands.
- Transfer axis: surface vs subsurface chain residual dominance.
- Ratio axis: high `QOFE/Q` vs ratio-unavailable vs ratio-below-threshold.
- Temporal axis: isolated-spike days vs persistent flagged-day counts.
- Topology axis: late-OFE-localized vs broader OFE-distributed anomalies.
- Run-context axis: run/config clustering, shared scenario characteristics.

## Initial Defect Family Draft
Candidate families (to validate with data):
- F1: Extreme late-OFE residual + high pulse + high ratio (likely runoff-routing imbalance signatures).
- F2: Extreme residual + pulse with unstable/unavailable ratio support (instrumentation/term-alignment candidates).
- F3: Moderate residuals with high OFE-local concentration but low chain-transfer artifacts.
- F4: High chain-transfer residual-dominated anomalies with lower closure residual totals.

## Milestones
1. Data shaping and feature extraction.
2. Deterministic taxonomy draft + automatic assignment.
3. Manual calibration on high-severity exemplars.
4. Campaign design and prioritization.
5. Closeout report and handoff.

## Decision Log
- 2026-05-02: Prioritize defect-family triage before any remediation coding.
- 2026-05-02: Use existing validation artifacts as the baseline evidence set.

## Surprises & Discoveries
- None yet.

## Outcomes & Retrospective
- Pending execution.
