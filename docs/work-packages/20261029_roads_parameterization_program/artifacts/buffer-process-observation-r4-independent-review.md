# Independent scientific review: revision-4 buffer observation

The nine-pair design is accepted for bounded observation preparation. This is
independent AI review, not institutional peer review or acceptance of a new
parameterization. Execution remains conditional on the source/variable/unit map,
observer patch and provenance review required by the plan.

## Selection readback

The [independent executable](review_buffer_observation_selection_r4.py) rebuilds
eligibility and ordering from the complete paired ledger without importing the
selector or executing its stored SQL. The
[receipt](buffer-process-observation-r4-independent-selection.json) confirms all
nine selections, their source records, paired-file hashes, calendar/native-year
mapping and original case summaries. All outlet differences exceed the combined
native printing interval; the smallest is 187 intervals. Four selected paved
cases have exactly zero observed road export throughout both full-period lanes.
An absent daily ELEMENT row is not reclassified as an observed zero.

The panel contains the lower-incoming-water/sediment contrast, dry legacy
outlets, a passing control with the same annual signature, underprediction both
with and without lower incoming sediment, a small passing control and a
meaningful overprediction. The ninth case adds a rutted underprediction control.
These extreme cases cannot estimate population effects or establish mechanism
coverage of all designs. The full-panel facts remain essential: 13 of 18
meaningful passing controls share the annual lower-fill/higher-outlet pattern,
while all 48 meaningful underpredictions have lower generated outlet export.

## Required implementation gate

Before compilation, freeze and independently review the exact observation
sites, variable names, dimensions, time support, normalization, valid-state
guards, source/object hashes and complete observation-only patch. Identify the
actual call paths; routine names alone do not establish execution. Unavailable
terms must remain explicit. No production source or scientific arithmetic may
change. This review does not certify a variable map that has not yet been written.

The plan correctly requires unconditional owning day/OFE/hydrology markers,
including the dry legacy branch, plus entered/skipped status. Missing executed
branch observations reject coverage; valid absence of sediment routing does not
imply an observed zero class load. Never print inactive/uninitialized state.

Prioritize storm-time layer liquid/ice, conductivity/restrictions, front/suction,
infiltration and routing support before interpreting class composition. Annual
pore capacity and prior-day total storage cannot establish storm-time available
storage. Incoming buffer classes must be observed at their actual upstream
handoff, with load/rate integration factors. Terminal EVENT fractions cannot
substitute. Signed local rates require native spatial/time/width normalization;
net boundary exchange cannot identify gross erosion, deposition or tagged origin.

The first pair must pass the full-period preflight before the remaining eight
pairs. Every lane requires all ordinary native outputs byte-identical to its
existing unobserved R4 record, plus post-run input/source rehashes, normal
completion, coverage and the unchanged strict particle audit. Full-period parity
and bounded target/prior-day tracing are separate requirements. No interpretation
transfers from an observer attempt that fails parity.

## Disposition

No scientific design blocker remains. Accept preparation subject to the stated
implementation gates; accept no observation result in advance. Preserve all
failed attempts and both discrepancy directions. A subsequent conclusion may
justify one falsifiable ablation or a separate defect investigation, but this
study authorizes neither parameter tuning nor a universal buffer coefficient.

Reproduce selection with the existing project virtual environment:

```bash
.venv/bin/python docs/work-packages/20261029_roads_parameterization_program/artifacts/review_buffer_observation_selection_r4.py --ledger /workdir/wepppy/out/roads-parameterization-program-20261031/event-supply-retention-r4-v3 --seeds /workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-process-observation-r4/seeds.json --output /tmp/buffer-observation-selection-review.json
```

The output path must be fresh; the command does not modify frozen inputs or run
the native model.
