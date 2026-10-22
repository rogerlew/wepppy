# Roads segment loss summary correction

Status: Active, contract checkpoint. Date: 2026-10-22.

Correct the target-hillslope attribution defect in the existing segment summary.
Roger authorized scaffolding/execution after the UM1 diagnosis; prior session
commit authority persists. Execute [the plan](prompts/active/repair_execplan.md).
Current progress: [tracker](tracker.md).

Deliver canonical contract/ADR, independent checkpoint, source-qualified producer,
regressions and isolated UM1 Parquet/CSV/browser/archive evidence. Preserve column
names, file layout, access and aggregate water accounting. No production deploy,
new dependency, model rerun, geometry repair or original UM1 mutation.

Compatibility plan: additive provenance; nullable unsupported aliases; correct
existing numeric meaning; explicit regeneration of historical artifacts only.
Sources are native-produced PASS and WAT; original model and baseline artifacts
must remain byte-identical. Missing completed-source data fails, empty manifests
produce typed empty tables. Security triage: high (file publication boundary).
Dedicated correctness and security reviews required before closeout.
