# Roads lateral-flow investigation: UM1

**Status**: Closed, diagnosis complete (2026-10-22)  
**Timezone**: UTC  
**Stakeholders**: Marta Basso (reporter), Roger (operator)

## Problem and scope

Marta reports zero lateral flow in every year and unusually large runoff and
baseflow in the roads totalwatsed output. Roger identified and synced her
`clogging-starch` project (UM1 / reference, `disturbed9002-wbt-mofe`) from wepp1
to forest and requested an investigation on 2026-10-22.

Investigate the roads water-accounting inputs and report aggregation using
`/wc1/runs/cl/clogging-starch`. Preserve the synced evidence. Deliver a supported
causal explanation, impact assessment, and bounded repair recommendation.
Production modification, deployment, and in-place regeneration of the synced
run are outside this investigation scope.

## Initial evidence

Forest readback reproduces the report for 2000–2015 (5,844 daily rows).
Roads WAT contains only segment IDs 900001–900034, with zero `latqcc` throughout.
Roads PASS contains all 66 baseline hillslope IDs plus those 34 segment IDs.
Roads totalwatsed area is 4,127.15 m²; baseline area is 441,820.29 m².
This is a confirmed input-population mismatch and a leading causal hypothesis,
not yet a complete diagnosis of the writer and native aggregation boundaries.

Calendar-year 2001 totals (mm):

| Scope | Lateral flow | Runoff | Baseflow |
| --- | ---: | ---: | ---: |
| Baseline | 1,021.097540 | 183.022941 | 60.107896 |
| Roads | 0 | 20,082.365246 | 1,273.251164 |

See [hashed input inventory](artifacts/initial-inputs.json) and its
[read-only reproduction script](artifacts/inspect_inputs.py).

## Investigation contract and rationale

Preserve both baseline and roads outputs and distinguish road-segment-only
hydrology from combined watershed hydrology. Do not fix the displayed lateral
flow by copying baseline totals or changing units without tracing physical
source populations and area denominators. Roger requested opening an
investigation; this package records evidence and a continuation plan rather
than authorizing production repair. The rationale is to retain the reported
state and test the smallest plausible cause before broad model changes.

## Complexity budget

Reuse existing Roads, interchange, and native aggregation code. No new
infrastructure, dependencies, defaults, formulas, or runtime mechanisms.
First test input-set selection on an isolated scratch copy. Escalation requires
retained evidence that this bounded explanation fails the incident condition.

## Validation and exit criteria

- Trace selected road configuration through raw WAT/PASS, interchange inputs,
  native aggregation, and the exported totalwatsed columns.
- Explain zero lateral flow and inflated runoff/baseflow separately, including
  area units, population overlap, and any road-segment double counting.
- Demonstrate the first divergent boundary with an unmocked isolated replay,
  recording code/native versions and before/after artifact hashes.
- Recommend the smallest correction and required regression cases; distinguish
  historical affected projects from newly generated runs.

Highest supported claim: symptom reproduced and input mismatch identified.
Fresh execution, report-route validation, repair, and deployment are pending.

## Risk and review gates

Security impact: **none** for read-only analysis and repository evidence;
no dedicated security review is required. No parameterization change or ADR
is present. Any future formula/unit/default correction requires the applicable
ADR and correctness review before implementation closeout. No mitigation has
been introduced. Health signals are coherent contributing populations and
physically justified water depths; danger signals are silent zero filling,
wrong area normalization, duplicate contributions, or baseline mutations.
Observe the full retained 2000–2015 record for this investigation.

## References and related work

- [Completed ExecPlan](prompts/completed/investigation_execplan.md)
- [Tracker](tracker.md)
- [Output scope contract](../../schemas/output-scope-contract.md)
- [Hillslope water aggregation contract](../../schemas/hillslope-water-aggregation-contract.md)
- [Generated artifact validation](../../standards/generated-artifact-validation-standard.md)
- [Watershed physical water repair](../20261021_watershed_physical_water_repair/package.md): related accounting work; do not assume its native routing findings explain this report-input mismatch.

Source entry points: `wepppy/nodb/mods/roads/roads.py` workspace preparation,
PASS assembly, and `_regenerate_roads_report_resources`;
`wepppy/wepp/interchange/totalwatsed3.py::run_totalwatsed3` delegates aggregation
to `wepppyo3` using roads-scoped H.pass and H.wat inputs.

## Closure — 2026-10-22 UTC

[Diagnosis and repair recommendation](diagnosis.md) complete. Native replay
confirms the three report-input defects and isolates the baseflow mechanism.
All six source hashes are unchanged. The highest supported claim is diagnosed;
repair, production census, deployment, and incident resolution remain follow-up
work. The initial hypotheses above are superseded by the retained diagnosis.
