# Current Roads contexts: independent implementation review

Reviewer: `mipa_contract_correctness`. Scope: the five disposable public-controller contexts in [current_r7_roads.py](current_r7_roads.py) and the [declared protocol](resumption-r7-current-roads-protocol.md), based on the completed `current-project-v2` baseline. No native call, production edit, new exclusion, or frozen-artifact edit was performed by this reviewer.

## Initial findings

- **R7-ROADS-01 — Medium, missing execution/validation dependencies.** The initial driver `dependencies()` bound `roads_project.py` and `extract_fixture.py` but omitted the lazily imported `tests/roads/roads_matrix.py::read_management` and the native input templates under `wepppy/nodb/mods/roads/legacy_templates/`. Production preparation reads the soil/management templates (`roads.py:3228–3248`); the test helper also reads the management template as its expected result (`roads_project.py:182–195`). A change to either could alter the declared experiment or its acceptance check without failing the frozen dependency comparison. Required correction: bind the helper and actual template files in an additive amendment or fresh declaration before execution.
- **R7-ROADS-02 — Medium, missing geometry/source bindings.** The inherited `prep.snapshot()` included `wepp/`, `roads/`, `climate/`, and root `*.nodb`, but omitted the DEM/channel/subcatchment/flow-vector rasters and watershed geometry/translation data. These are actual Roads inputs (`roads.py:738–789,1520,3868,4618–4619`), so source drift could alter segment geometry while passing the recorded inventory. Required correction: add `dem/` and `watershed/` to this lane's frozen source snapshot and runtime comparisons, with VRT source coverage. The only staged VRT is `dem/dem.vrt`; it refers to local `dtm_UM1.tif` with `relativeToVRT=1`, so no external raster dependency was found.

The original unexecuted declaration is `current-roads-v1/declaration.json`, SHA256 `f03e604629f73bd5a0bc897e8dd40bf4d5a405b4b6145304f188d9ead54fc60a`. Its original 1,157 dependencies and 3,303 source entries match actual bytes. The gaps above concern omitted files, not a mismatch or known scientific defect.

## Source and acceptance readback

The driver invokes the existing `validate_project` unchanged, creates independent destinations, and rebases serialized paths before controller loading. The helper verifies the pinned original 55-feature upload; only the declared positive unrutted case excludes the exact OSUNUM6 feature (SHA256 `b30f47d5562e899813769eb37c84be30f9a242d429c8aa6f87c534d791902b22`). The full-upload negative case remains distinct. The helper explicitly sets each feature's design and the already declared unrutted 30 m/10% fill and buffer values; these are experiment inputs, not new defaults.

Positive cases must complete the installed controller lifecycle and reconcile 5,844 daily rows, contiguous indices, 2000–2015 year coverage, target area, weighted water terms, canonical PASS volume, streamflow composition, management assignments, segment summaries, and current output receipts. Copied baseline native inputs/outputs and source files are checked for invariance. These checks exercise existing report/accounting behavior; they are not a complete independent physical closure or native per-segment calendar audit.

The negative branch catches only `RuntimeError` with the expected two-segment message and then independently calls `verify_negative`. That helper requires exactly two failed rows, target IDs 271/272, `roads-seg-000001`, reason `failed_non_positive_top_ofe`, all 55 uploaded features, absence of a current lifecycle receipt, and unchanged baseline/source. Unexpected errors or an unexpected successful negative run stop the task. Existing source history has no failed rows, so it cannot supply the expected failures accidentally. No context retry or broader error-to-success conversion was introduced.

Both r7 executable hashes match the installed pair; the source selects `wepp_261029`. All 494 completed baseline output/interchange hashes match the v2 completion receipt. The outcome readback SHA256 is pinned to `7cc96450086f02474dd723c2b01b3dd15bf2ec913d98c30180c29935e3f07de6`. The declared UID/GID, 1000/993, matches an independent `wctl exec -T weppcloud` identity readback. Contexts run sequentially. Native reader `.so` files are already included in inherited dependencies.

## Final disposition

**PASS for execution of the exact amended declaration; both initial findings are closed.** `current-roads-v1/declaration-v2.json`, SHA256 `738ccec3e4a113cd63edc6108d33616bb4e34026db86b3603110b7174fdda2be`, adds the actual management checker, all 18 native template files, and the DEM/watershed inventory. Its predecessor remains unchanged and unexecuted. The five cases, baseline outcome, binaries, identity and scope are unchanged.

I independently rehashed all 1,176 declared dependencies and 3,537 source files, verified preservation of the original 3,303 source bindings, checked the VRT source against the expanded inventory, and verified that execution had not started. I also invoked only the actual driver's `dependencies()` and `source_snapshot()` through Compose: both exactly equal the amended declaration. `run()` was not invoked. Runtime checks use the expanded snapshot before execution and after every context; dependency and binary checks remain in place.

- Reviewed driver SHA256: `29da25d48eacbd1ae0296e34d23ef04ba40e4484a6ca65e19467371d858f4136`.
- Reviewed protocol SHA256: `c7299ddddc93632ea8bc3d9845b34392c96b00ddda193595bfce59543487233d`.
- [Independent staging readback](resumption-r7-current-roads-staging-readback.json) SHA256: `0bac4d02251cc6035e7cec6ed81b576ee214c5b4f2a8f958d84a3c13af23ab41`.

No unresolved implementation blocker remains in this bounded review. Outcome acceptance is separate: the five contexts have not been executed by this reviewer, and this lane does not establish browser/RQ/query-catalog parity, generated-U12 parameter acceptance, withheld validation, or global scientific acceptance. Independent postexecution native/artifact/report readback is still required, including the exact negative failure evidence; passing the source review is not evidence that those outcomes pass.
