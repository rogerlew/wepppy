# Omni MOFE segment eligibility

Status: Active. Operator authorized implementation on 2026-09-18.

Fix the dominant-hillslope gate that prevents eligible multiple-overland-flow-element
(MOFE) segments from receiving Omni thinning, prescribed fire, or mulch. Use the
existing per-segment treatment rules; preserve single-OFE selection and hillslope
slope/burn filters. Production deployments and existing-project reruns are separate.

See [execution plan](prompts/active/execplan.md), [tracker](tracker.md), and
[contract decision](artifacts/20260918_contract_decision.md).

Compatibility: no persisted schema, management key, numerical parameter, queue,
or API changes. Mixed MOFE hillslopes can now receive treatments previously skipped.
Verify generated combined managements and prepared WEPP inputs in regression tests.

## Other findings

The same outer gate affects mulch: this is included as the same defect.
The previous audit's identical low/moderate outlet results and representative
combined managements warrant investigation, but do not establish a current-source
root cause or prove rank-order disagreement with manual scenarios. That audit did
not collect paired manual runs, so its claimed completion of the 20% comparison
was premature. The 20% criterion compares corresponding manual/Omni treatments,
not low versus high severity. Thinning option labels require matching actual
canopy/ground cover before numerical comparison. These remain follow-up audit work,
not authorization to change scientific parameters in this package.
