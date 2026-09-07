# Climate spatial mode switching

Status: Closed 2026-09-07 03:29 UTC. Started 2026-09-07 03:13 UTC (Pacific date 2026-09-06).
Owner: Codex. Requester: WEPPcloud operator.

## Problem and scope

Loading Climate Options with Vanilla CLIGEN or stochastic PRISM removes the
interpolated radio from the DOM. Switching to available observed Daymet or
gridMET cannot restore it. Restore the existing supported dataset/method
relationship with a bounded template fix, regression tests, and help updates.
No defaults, algorithms, schemas, queue wiring, dependencies, or deployment change.

## Authority and compatibility

This is a conformance fix under `docs/standards/contract-first-change-standard.md`
("Conformance Fixes and Urgent Restoration"). Unchanged authority is
`docs/schemas/project-owned-config-contract.md` section 9 (resolved axes,
per-dataset adjacency and exact-current compatibility) and its section 9
capability example (both observed datasets allow interpolated), together with
`docs/ui-docs/controller-contract.md` "Project-config run authority and refresh".
The requested implementation restores those relationships; no normative delta
or contract ancestor commit is required. Starting revision:
`376c993b13fe9debda301e3d2ab5e2e3377f09a6`.

Render the union of spatial modes from selectable datasets in the supplied run
catalog, plus the exact stored current mode. Enable only modes supported by the
selected dataset, honoring its disabled modes. Do not consult the global catalog
or infer additional capabilities. Existing numeric values and server validation
remain compatible. The union avoids requiring a page reload after switching;
rendering every globally known mode would broaden restricted run presentation.

## State and regression plan

| State | Expected result |
| --- | --- |
| New/default run | Switching Vanilla/PRISM to either observed dataset enables mode 2 |
| Empty/absent catalog | Preserve existing rendering compatibility; no new exception |
| Populated observed selection | Mode 2 is present and enabled; stored selection retained |
| Restricted run | No mode 2 unless authorized by a selectable dataset or exact current |
| Legacy exact current | Unsupported stored mode remains visible and disabled |
| Hidden/disabled dataset | Does not contribute additional selectable spatial modes |
| Hostile capability input | Existing server validation owns rejection; no boundary change |

## Security impact

None: template presentation only, no attack-surface change. Dedicated security
review artifact not required. Independent correctness review is required.
No persistence/filesystem safety boundary changes or data migration.

## Exit criteria

Real Jinja render regression fails before the patch and passes after. Controller
coverage verifies switching, selection submission, and switching back. Focused
pytest, frontend lint/tests, full pytest gate, and docs lint are recorded.
Independent review has no unresolved medium/high findings. No claim of live
climate-generation or deployment validation is made.

## Related work

The active Project Config run UI authority package owns the broader domain:
`docs/work-packages/20260827_project_config_run_ui_authority/`.
This package closes only the missing spatial-option defect.

## Deliverables and closure

Implemented locally: spatial options survive dataset switching, with 16 render
matrix cases and two controller switching/submission regressions. Updated
DAYMET/GRIDMET help and user/developer guidance. Independent correctness review
passed with no introduced findings. Focused pytest (212), full Jest (835), lint,
and docs checks passed. Full pytest stopped at an unrelated pre-existing
shape-converter Compose assertion after 5078 passes and 50 skips; isolated
reproduction and unchanged-file evidence are recorded in tracker.md. No
full-suite success or deployment is claimed.

Follow-ups outside scope: reconcile the shape-converter overlay assertion; test
and repair pre-existing disabled legacy-current radio handling in the controller.
