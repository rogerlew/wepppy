# Revision 7 current project: independent implementation review

Reviewer: `mipa_contract_correctness`, 2026-11-03 UTC. Separate scope from fixed
seed/panel replay. No native model call or retained-input mutation by the reviewer.

## Initial findings

**HOLD before native execution.** The prepared disposable context is appropriate,
but its initial execution helper omits a required consumer step and leaves
controller selection outside the frozen execution inputs.

| ID | Severity | Finding | Required correction |
| --- | --- | --- | --- |
| R7-PROJECT-01 | High, execution blocker | `execute_current_r7_project.py:run` calls `Wepp.run_hillslopes()` and then `run_watershed()` without building hillslope interchange. `WeppRunService.run_hillslopes` emits native output only. Watershed postprocessing invokes `_build_totalwatsed3`, whose reader requires `H.pass.parquet` and `H.wat.parquet` (`totalwatsed3.py:369–376`). The fresh output directory is empty before execution. | Use the standard hillslope-interchange boundary/options after hillslope execution and before watershed postprocessing. Preserve the initial declaration and bind the amended helper explicitly; do not reuse old interchange files. |
| R7-PROJECT-02 | Medium, execution identity gap | The declaration binds native input files and code, but not cloned NoDb files controlling binary selection, hill membership and runtime behavior. `_wepp_bin` is asserted only during declaration; execution hashes the declared pair without checking which controller selection will actually be invoked. | Bind cloned root NoDb hashes after watershed preparation, verify them before deserialization/execution, and assert selected binary/configured flags at invocation. Retain per-process binary traces for post-execution readback. |

Initial execution declaration SHA256:
`f8e2c22038432da4e47088f46089046bd027a36c1c6cef55a95d3fdc963f876a`.
No drift was observed in the actual controller selection: copied state selects
`wepp_261029`, enables watershed and multi-OFE execution, and disables deletion
after interchange. All copied root NoDb text was free of the original project
prefix after preparation. The second finding concerns the missing binding check,
not an allegation that a different binary has already run.

## Preparation and scope

The preparation helper creates an exclusive disposable copy, rebases serialized
paths before NoDb deserialization, preserves copied old runs/outputs separately,
and executes complete configured `prep_hillslopes`. It records PMET, groundwater,
UI and snow enabled; frost disabled; multi-OFE enabled. This is current model-input
preparation using retained source material, not a new soil acquisition or generated
candidate adoption. No silent geometry exclusion or shared default change occurs.

Normal runner behavior, including its bounded timeout retries, is part of this
controller execution lane. Retain actual attempt/binary traces; do not describe
the lane as the seed driver's no-retry protocol. Later native/interchange/report
readback and fresh Roads lifecycle contexts remain required and unexecuted here.

## Final disposition

**Bounded implementation and staging PASS for the exact v3 declaration.** Both
initial findings are closed. The first amendment adds the canonical hillslope
interchange boundary with the configured pass family/calendar and raw-file
retention. The second binds all cloned root NoDb files, owned configurations and
feature-registry YAML before native execution. It verifies NoDb hashes before
controller deserialization and checks binary selection/runtime flags before each
native stage. Neither initial declaration was executed or overwritten.

Verified declaration chain:

- Initial: `f8e2c22038432da4e47088f46089046bd027a36c1c6cef55a95d3fdc963f876a`.
- V2: `ecf3e84a60551c92cae0e5f1783c2a7f8701ed3bf18a788a50af752af78d550b`.
- Approved v3: `d5178b116fae71c4c4e15f07febc1c96f52f2b78c500affa1b8885b8c6b0e0fa`.

The final execution helper SHA256 is
`0d0a2804e5f4346513228aa09d0cf6f4a6ef15130bbfff9c6e61954468b8ac5c`.
Independent staging readback verified 334 prepared hillslope files, 344 total
declared run files, 1,153 dependencies, 12 cloned NoDb bindings and all 3,374
protected original source-file hashes. It confirmed 66 hillslope run files plus
one watershed run file, the exact declared r7 binary pair, UID 1000/GID 993 and
four workers. Output remained empty and no execution-start receipt existed.
Machine evidence: `resumption-r7-current-project-staging-readback.json`.

Read-only native-input parsers independently verified all 66 hillslopes and 193
OFEs: management, slope and soil OFE counts agree; management rotations and run
prompts specify 16 years; every climate contains the complete 5,844 unique dates
from 2000-01-01 through 2015-12-31. The four PMET rows uniquely cover every emitted
crop key, all within native eight-character identity width. This check neither
rewrote inputs nor deserialized controllers.

There is no remaining implementation blocker for the declared baseline invocation.
No current-project native or scientific acceptance claim follows. Completion
still requires fresh process/binary traces, full output/calendar/interchange
readback and installed-report checks, followed by the separately declared Roads
lifecycle/geometry contrasts. No RQ/browser rollout is established by this lane.
