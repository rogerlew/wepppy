# Warming-championship roughness sensitivity

**Status**: Closed 2026-10-06, research complete. **Timezone**: UTC.

## Overview and scope

Compare outlet hydrographs for the user's warming-championship run on forest,
using the corrected surface-return binaries and initial random roughness of
0.10, 0.17, and 0.60 m only on initial-condition records originally at 0.10 m.
Preserve the other 19 records and all climate, soil, geometry, routing, and
management fields. Recompute all 864 hillslopes and the watershed for 24 years.
This is an offline sensitivity experiment, not calibration, a new default,
production deployment, or repair of the user's original run.

## Complexity budget and compatibility

Reuse existing WEPP binaries, generated input files, Python scientific runtime,
and subprocess execution. Add only package-local research scripts and evidence.
No services, dependencies, privileges, schema changes, or production changes.
Copies of executable inputs are the explicit experimental boundary; NoDb project
initialization and UI clone semantics are not being tested. Original source files
remain read-only. Output mode changes from daily peak to 10-minute hydrograph,
with identical routing timestep and an output-only parity replay.

## Generated artifact validation and success criteria

Retain source and binary SHA256 manifests, semantic management readbacks, exact
token mutation records, fresh execution terminals, and output hashes. All 2,592
hillslope executions and three watershed executions must succeed before claiming
the experiment complete. Check the output-mode parity replay. Produce hydrograph
figures and peak, volume, and timing summaries from the fresh outlet outputs.
Missing or invalid days are failures, not zeros. Report any model warnings and
limits of daily/subdaily output interpretation.

## Security and parameterization gates

Security impact: none; bounded offline model execution uses existing trusted
executables and inputs, not a new service or execution interface. Dedicated
security review is not required. No production parameterization changes, so no
parameterization ADR is required. Stakeholder: Roger Lew. Results are research
evidence, not a release or physical-validation claim.

## Deliverables

See [results](artifacts/results.md), [validation review](artifacts/validation-review.md),
tracker.md, and prompts/completed/experiment_execplan.md. Scripts, manifests,
summaries, figures, and results are retained in artifacts; bulk outputs on forest.

## Closure

All 2,596 model executions passed, including the output-mode control. Consumed
inputs, negative controls, source preservation, and all 24 years of outlet data
passed readback checks. The maximum outlet peak falls by 0.672% at 17 cm and
0.913% at 60 cm; reported total runoff changes by -0.01098% and -0.02106%.
No large consistent timing shift is resolved in the selected hydrographs.

A separate approximately 1.3% discrepancy between integrated hydrographs and
the reported volume ledger remains explicitly unresolved. This is a scientific
limitation and possible follow-up investigation, not omitted acceptance evidence
for the bounded input-sensitivity experiment. No defaults or production runs
were changed, and no physical calibration or routing-fix release is claimed.
