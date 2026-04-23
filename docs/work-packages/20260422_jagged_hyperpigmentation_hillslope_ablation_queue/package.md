# Jagged Hyperpigmentation Hillslope Ablation Queue (`H3507`, `H1271`)

**Status**: Open (2026-04-22)
**Timezone**: UTC

## Overview
Marta reported a suspicious sediment-contribution pattern for run `jagged-hyperpigmentation/disturbed9002-10-mofe` (WEPPcloud URL below): two hillslopes (`H3507` and `H1271`) dominate outlet sediment yield, and `element.dat` rows show abrupt numeric anomalies (`*******`) for those hillslopes.

This package queues the next ablation investigation slice so it can start immediately after the current campaign lane in `/workdir/wepp-forest` finishes.

## Objectives
- Capture reproducible source evidence for `H3507` and `H1271` from wepp1 run artifacts.
- Stand up a compliant incident package in `/workdir/wepp-forest/docs/ablation/` for this case.
- Execute one-change-per-lane ablation runs to isolate whether the anomaly is input-triggered, numeric-boundary-triggered, or parser/format-triggered.
- Produce an evidence-backed keep/rollback recommendation for any candidate mitigation.

## Scope
This package scopes only the next queued ablation campaign for two hillslopes in one run signature.

### Included
- Work-package intake, tracker, and active ExecPlan for campaign handoff.
- Explicit staging plan for copying source run evidence from wepp1 (no in-place mutation under production run roots).
- Ablation lane sequencing for `H3507` and `H1271` under `docs/ablation` protocol.
- Required evidence capture outputs (`incident.md`, `notes.md`, `matrix.csv`, `artifacts/*`).

### Explicitly Out of Scope
- Immediate production binary patching or vendoring.
- Scope expansion to unrelated hillslopes or unrelated run IDs.
- Multi-issue patch bundles that break one-lane-one-change attribution discipline.
- WEPPcloud UI/report-contract changes.

## Stakeholders
- **Primary**: Marta and ablation campaign operators in `/workdir/wepp-forest`.
- **Reviewers**: WEPP numerical stability maintainers (`wepp-forest`) and WEPPcloud run operators (`wepp1`).
- **Security Reviewer**: Not required unless scope expands to auth/session/queue surface changes.
- **Informed**: Disturbed/MOFE maintainers tracking `disturbed9002-10-mofe` behavior.

## Success Criteria
- [ ] Source artifacts for both target hillslopes are staged from wepp1 into an immutable local incident workspace.
- [ ] A new ablation incident package is initialized and populated under `/workdir/wepp-forest/docs/ablation/<incident_id>/`.
- [ ] Baseline and observe-only lanes reproduce the anomaly with deterministic signatures.
- [ ] At least one ablation matrix cycle completes with clear keep/rollback outcomes per lane.
- [ ] Final incident artifacts include actionable attribution, next-step recommendation, and rollback safety notes.

## Dependencies

### Prerequisites
- Current in-flight ablation lane in `/workdir/wepp-forest` reaches a handoff point.
- wepp1 access to the source run tree rooted at `/geodata/wc1/runs/ja/jagged-hyperpigmentation`.
- Availability of the currently pinned campaign binary in `/workdir/wepp-forest/src/` or `/workdir/wepp-forest/release/`.

### Blocks
- Follow-on fix package(s) for this specific anomaly remain blocked until this ablation package captures attribution evidence.

## Related Packages
- **Related**: [20260421_disturbed_mofe_9002_soils](../20260421_disturbed_mofe_9002_soils/package.md)
- **Related (external repo)**: `/workdir/wepp-forest/docs/work-packages/20260422-generative-fuzzing-milestone8-p5-hydraulic-ablation/`
- **Follow-up**: TBD after lane results classify root cause.

## Timeline Estimate
- **Expected duration**: 2-3 focused sessions (handoff + execution + closeout).
- **Complexity**: Medium.
- **Risk level**: Medium (output-integrity and attribution risk if evidence is incomplete).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Investigation is run-artifact analysis and numerical behavior isolation; no planned auth/session/secrets or route attack-surface changes.
- **Security review artifact**: `N/A`

## References
- `https://wepp.cloud/weppcloud/runs/jagged-hyperpigmentation/disturbed9002-10-mofe` - user-reported run with anomalous hillslope evidence.
- `wepp1:/geodata/wc1/runs/ja/jagged-hyperpigmentation` - confirmed source artifact root for this queued ablation.
- `/workdir/wepp-forest/docs/ablation/20260422_jagged-hyperpigmentation_hillslope_elementdat-stars/` - initialized incident package with staged hillslope artifacts and baseline logs.
- `/workdir/wepp-forest/docs/ablation/README.md` - incident package contract.
- `/workdir/wepp-forest/docs/ablation/protocol.md` - lane design and keep/rollback policy.
- `/workdir/wepp-forest/tools/ablation_protocol.py` - init/finalize tooling for incident packages.
- `docs/work-packages/20260422_jagged_hyperpigmentation_hillslope_ablation_queue/prompts/active/jagged_hyperpigmentation_hillslope_ablation_execplan.md` - execution plan for this queue item.

## Deliverables
- New ablation incident folder in `/workdir/wepp-forest/docs/ablation/` for this run/hillslope anomaly.
- Populated `incident.md`, `notes.md`, `matrix.csv`, and `artifacts/manifest.csv` + `checksums.sha256`.
- Lane-by-lane outcome summary with explicit keep/rollback decisions.
- Recommendation for next action (no-op, targeted guard candidate, or escalation package).

## Staging Status (2026-04-22)
- Incident initialized: `/workdir/wepp-forest/docs/ablation/20260422_jagged-hyperpigmentation_hillslope_elementdat-stars/`.
- Source snapshot staged from wepp1: `/geodata/wc1/runs/ja/jagged-hyperpigmentation`.
- Baseline local replays executed for `p1271.run` and `p3507.run` with `/workdir/wepp-forest/src/wepp_hill`.
- Signature evidence captured:
  - Source snapshot has `*******`/`********` signatures (`C099`).
  - Staged baseline replay outputs currently show no starred signatures (`C100`).

## Follow-up Work
- If no candidate lane attributes causality, spawn a dedicated follow-up package for next hypothesis family (for example parser-width vs numeric-boundary probes).
- If a minimal lane resolves anomaly with acceptable parity, create implementation package in the appropriate repo (`wepp-forest` for binary-side, `wepppy` for wrapper-side).
