# Roads drainage: physical justification and broader validation

Status: complete, 2026-10-30 UTC. Operator-authorized scientific study; production unchanged.

Evaluate whether source-based buffer drainage survives a broader matrix and has
physical support. The exact `wepp_261026`, normalized 200 mm boundary, soil depths,
initial saturation, management and erosion parameters remain fixed. Read the
[ExecPlan](prompts/completed/study_execplan.md) and [tracker](tracker.md).

Freeze eight generated specimens, five climates, four road designs, two surfaces
and three traffic levels (960 profiles). Execute current and source-buffer drainage
for every profile (1,920 native runs). Three additional specimens are selected from
source metadata before outcomes: lithic 1856573, low-conductivity mineral horizon
53949, and unrestricted 1718494. Existing five specimens are development evidence,
including the previously used specimen named `holdout`.

Source-buffer is a counterfactual: restrictive source Ksat converted from um/s to
mm/h, or deepest emitted horizon Ksat if no restriction was identified. A conservative
policy view retains current drainage for identified bedrock and selects source-buffer
for mineral-horizon or no-identified-restriction cases. Neither view is an accepted
production default. Absence of a reported restriction does not establish permeable
underlying geology; a 10 m restrictive-layer thickness is also unverified.

Compatibility/regression plan: additive isolated records only, no project mutations
or schema changes to production. Rehash references, read back consumed soil, validate
complete native calendars, and retain every factor-ten failure and accounting mismatch.
Reproduce the 600 previous role controls. Report unique input signatures because
modern role preparation aliases some surface/traffic/design combinations.

Security impact: none; no dedicated security review required. Complexity budget:
existing soil preparation, native runner, Rust readers and audited accounting only;
no dependency, rebuild, deployment, service or production parameter change. Any
future production parameter change requires an ADR and separate acceptance.

## Runtime parity discovery

The simplified comparison omits `wepp_ui.txt`, present in the source projects and
canonical Roads fixture. A separately frozen 192-run bridge tests UI mode alone
and the site's complete shared settings. Total: 2,112 new runs. This additional
milestone prevents treating legacy-mode results as production-mode evidence.

## Outcome

[Report](report.md) and [physical justification](physical-justification.md): 2,112
native runs complete; all 600 prior controls reproduce exactly. Source drainage
changes broad factor-ten coverage only from 820/905 to 824/905 and introduces
13 regressions. Runtime settings materially change hydrology; UI-mode coverage is
61/71 for both current and source treatments. Six legacy-mode cases have invalid
negative sediment fluxes. No production candidate accepted.

Repository coverage: 12,186 passed, 298 skipped. Next: establish production-runtime
parity and reproduce the no-traffic negative flux under UI mode before conductivity
tuning. No production code, soil defaults, binary, native source or project changed.
