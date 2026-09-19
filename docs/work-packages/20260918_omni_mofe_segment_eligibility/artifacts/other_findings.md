# Other Omni issues and dispositions

| Finding | Evidence / confidence | Disposition |
| --- | --- | --- |
| Mulch also excludes eligible segments using scalar hillslope class | Same prefilter in `OmniModeBuildServices.apply_scenario_mode`; real mixed-segment regression now passes | Fixed with thinning and prescribed fire in this package |
| Old low/moderate outputs identical | Previous audit captured equal watershed values and identical representative management files; no paired manual output collection or execution-revision proof | Investigate generation/freshness before inferring a scientific parameter error; not fixed by this gate patch |
| Scalar hillslope label can disagree with segment assignments | Captured children report class 424 on 434 hillslopes while many segment assignments are forest 90; scalar and segment mutations are separate in Treatments | Use segment/input evidence for MOFE treatment coverage; inspect report consumers before any separate summary behavior change |
| Existing Omni children can be reused after a code update | Orchestrator reuse compares dependency SHA1, definition signature and year coverage, not source-code revision | Operational rebuild requirement; do not claim upgrading code refreshes old results |
| Manual/Omni 20% and rank comparison was not completed | Earlier audit collected Omni aggregate output and read manual source, rather than pairing the named manual runs | Outstanding audit work; compare equivalent measures and interventions after fresh inputs are verified |
| Different thinning selections | Captured Omni 40/75 and 65/85 versus manual canopy overrides at 30%/50% | Expected configuration difference; compare exact cover choices or explicitly qualify non-equivalence |

No evidence here authorizes changing numerical soil/management parameters, runoff
or sediment formulas. The manual-versus-Omni tolerance applies to corresponding
scenarios, not to the difference between low and high fire severity.
