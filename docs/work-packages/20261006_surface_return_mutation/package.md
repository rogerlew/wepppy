# Fixed-build hand-to-mouth-drought mutation repeat

**Status:** Closed (research execution), 2026-10-06. **Timezone:** UTC.

All 1,088 eligible mutations and 280 baselines completed and were independently
reconciled. Figures 1–3 are generated and visually checked. See
[results](artifacts/results.md); the scientific correction remains subject to
review and has not been deployed by this work.

Repeat the original Topanga (hand-to-mouth-drought) small-mutation experiment
with the default-on surface-return peak correction. Deliver Figures 1, 2, 3:
paired runoff, sediment delivery, and peak flow. Both sides of each mutation
comparison use the corrected executable, not old versus new executables.

## Scope and success criteria

Use burned base and undisturbed Omni strata, all 140 hillslopes per stratum,
full 1980–2024 histories, Ksat factors 0.99/1.01 and paired initial cover
deltas -0.01/+0.01. Exclude both cover directions if either would clip.
Preserve rrinit, dynamic rill width, climate and all nonmutated model inputs.
Retain input hashes, realized mutations, terminal records, outer-paired event
data, exclusions and figure statistics. No per-mutation watershed routing,
production mutation, binary deployment, new model flag or stakeholder email.

## Complexity budget and validation

Reuse existing census mutation adapters and plotting conventions. Permit only
an isolated execution/analysis script and observational companion build if
needed to extract full-precision outputs. No service or dependency additions.
Prove observer-on/off canonical output parity before the census. Validate each
changed input, finite values, unique event keys, full-period completion, exact
trial reconciliation, thresholds, and rendered figures. Figures are screening
evidence, not observed-flow validation or proof every residual is a defect.

## Artifact and compatibility contract

Additive research artifacts only; no production schema changes. Original closed
packages remain immutable. External raw outputs stay on forest under a new
holdout directory; compact manifests, scripts, summaries and figures live here.
Original legacy solver traces cannot be used as fixed-build peak authority.
If observation grain differs, record it explicitly and preserve missing events
as missing, not zero. Sediment continues to use the original EBE 0.1 kg/m output.

## Security and parameterization

Security impact: low, trusted offline research inputs and bounded local model
subprocesses only; no public surface, credentials or production writes. Review
path containment, no-overwrite behavior, subprocess arguments and timeout before
execution. No parameterization policy changes; the previously implemented
scientific correction remains requires_scientific_review, not a release claim.

## References

- Completed execution plan: prompts/completed/repeat_execplan.md.
- Original design: ../20260809_peakflow_topanga_census_execution/package.md.
- Corrected build: /Users/roger/src/wepp-forest/docs/ablation/20261006_surface_return_peak/incident.md.
