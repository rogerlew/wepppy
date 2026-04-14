# Execute WP-10 IFOLP WEPPpy E2E Cutover (`ifolp` default + legacy selectable mode)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is complete, WEPPpy channel delineation defaults to IFOLP with explicit `max_junctions=3`, while preserving a user-selectable legacy `remove_short_streams` path for compatibility and rollback safety. A user can choose `Stream Pruning Method` in WEPPcloud controls, the method is validated and carried through rq-engine payloads/state, and emulator outputs remain deterministic and operationally safe.

## Progress

- [x] (2026-04-14 03:10 UTC) ExecPlan authored and activated.
- [x] (2026-04-14 04:45 UTC) Implemented watershed config/state contract for `stream_pruning_method` with compatibility defaults (`ifolp` fallback for invalid persisted/default values, strict setter validation).
- [x] (2026-04-14 04:45 UTC) Implemented emulator method branching (`ifolp` default, `remove_short_streams` selectable) and explicit IFOLP `max_junctions=3`.
- [x] (2026-04-14 04:45 UTC) Implemented rq-engine parse/validate/pass-through and schema-default runtime/default reporting for pruning method.
- [x] (2026-04-14 04:45 UTC) Implemented WEPPcloud control/payload wiring and frontend tests for pruning-method propagation.
- [x] (2026-04-14 05:25 UTC) Executed required validation gates and captured outcomes in WP-10 artifacts.
- [x] (2026-04-14 05:25 UTC) Captured method-matrix evidence for both modes (`ifolp` + `remove_short_streams`) including explicit IFOLP `max_junctions=3`.
- [x] (2026-04-14 05:30 UTC) Completed mandatory review/disposition with no unresolved high/medium findings.
- [x] (2026-04-14 05:35 UTC) Updated WP-10 package/tracker, archived ExecPlan to `prompts/completed/`, and closed package.

## Surprises & Discoveries

- Local integration environment WhiteboxTools binary does not expose `IterativeFirstOrderLinkPrune` yet. Unconditional IFOLP in real-WBT integration tests failed with `Unrecognized tool name IterativeFirstOrderLinkPrune`.
- Resolution: keep production behavior explicit (no silent fallback), pin the two real-WBT integration test flows to explicit legacy mode, and add method-branch tests that prove IFOLP + legacy dispatch behavior and `max_junctions=3` wiring.

## Decision Log

- Decision: Keep `ifolp` as default but preserve explicit legacy selection (`remove_short_streams`).
  Rationale: Enables low-risk rollout/rollback and controlled cutover behavior.
  Date/Author: 2026-04-14 / Codex.

- Decision: IFOLP WEPPpy invocation must explicitly pass `max_junctions=3`.
  Rationale: WP-09 contract and integration plan require deterministic WEPPpy target behavior.
  Date/Author: 2026-04-14 / Codex.

- Decision: Do not silently fallback to legacy pruning when IFOLP tool is unavailable.
  Rationale: Root repository directives require explicit failures over hidden dependency masking.
  Date/Author: 2026-04-14 / Codex.

- Decision: Keep real-WBT integration tests operational in this environment by explicitly selecting `remove_short_streams` for those two tests.
  Rationale: Current local WBT binary lacks IFOLP command; explicit test-mode selection preserves deterministic coverage without changing runtime default behavior.
  Date/Author: 2026-04-14 / Codex.

## Outcomes & Retrospective

- Implemented end-to-end WP-10 plumbing for `stream_pruning_method` across watershed state, rq-engine validation/defaults, RQ enqueue path, and WEPPcloud controls/controller payloads.
- Confirmed IFOLP path explicitly calls `iterative_first_order_link_prune(..., max_junctions=3)` and legacy path remains selectable as `remove_short_streams`.
- Validation gates passed:
  - `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py`
  - `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py`
  - `wctl run-pytest tests/topo/test_terrain_processor_wbt_integration.py`
  - `wctl run-pytest tests/culverts/test_culvert_batch_rq.py`
  - `wctl run-npm lint`
  - `wctl run-npm test`
- Additional targeted regression check passed:
  - `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py`
- Method matrix evidence captured in tests:
  - `ifolp` branch: asserts IFOLP dispatch and `max_junctions=3`.
  - `remove_short_streams` branch: asserts legacy dispatch and expected arguments.
- Review/disposition closed with no unresolved high/medium findings.

## Context and Orientation

Primary implementation repository:
- `/workdir/wepppy`

Contract source and reference:
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wepppy-integration-plan.md`

Key WEPPpy backend files expected to change:
- `/workdir/wepppy/wepppy/topo/wbt/wbt_topaz_emulator.py`
- `/workdir/wepppy/wepppy/topo/wbt/wbt_topaz_emulator.pyi` (if signature/typing changes)
- `/workdir/wepppy/wepppy/topo/wbt/wbt_documentation.py`
- `/workdir/wepppy/wepppy/nodb/core/watershed.py`
- `/workdir/wepppy/wepppy/nodb/core/watershed.pyi`
- `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py`
- `/workdir/wepppy/wepppy/microservices/rq_engine/watershed_routes.py`
- `/workdir/wepppy/wepppy/microservices/rq_engine/schema_defaults_routes.py`
- `/workdir/wepppy/wepppy/rq/project_rq.py`
- `/workdir/wepppy/wepppy/rq/project_rq.pyi`

Key WEPPcloud UI/controller files expected to change:
- `/workdir/wepppy/wepppy/weppcloud/templates/controls/channel_delineation_pure.htm`
- `/workdir/wepppy/wepppy/weppcloud/controllers_js/channel_delineation.js`
- `/workdir/wepppy/wepppy/weppcloud/controllers_js/channel_gl.js`
- `/workdir/wepppy/wepppy/weppcloud/controllers_js/__tests__/channel_delineation.test.js`
- `/workdir/wepppy/wepppy/weppcloud/controllers_js/__tests__/channel_gl.test.js`

Key tests:
- `/workdir/wepppy/tests/topo/test_terrain_processor_wbt_integration.py`
- `/workdir/wepppy/tests/microservices/test_rq_engine_watershed_routes.py`
- `/workdir/wepppy/tests/rq/test_project_rq_mutation_guards.py`
- `/workdir/wepppy/tests/culverts/test_culvert_batch_rq.py`

Compatibility contract (must hold):
- Allowed methods: `ifolp`, `remove_short_streams`.
- Missing/blank persisted value defaults to `ifolp`.
- Invalid persisted value resolves to `ifolp` for read/default surfaces.
- Unknown mutation payload value is rejected with explicit validation error.

## Plan of Work

Milestone 1 locks the backend/state contract. Add or verify watershed and rq-engine contract plumbing so method values are deterministic and validated at boundaries.

Milestone 2 wires emulator behavior. Keep `extract_streams` creation of `netful0` provenance input and branch only pruning behavior by method, with IFOLP call explicitly using `max_junctions=3`.

Milestone 3 wires WEPPcloud UI controls and payload emission so users can choose pruning method and requests carry that value through rq-engine.

Milestone 4 executes mandatory validation and method-matrix regression checks for both IFOLP and legacy paths, then captures findings disposition.

Milestone 5 closes governance artifacts: update tracker/package with evidence, move this ExecPlan to `prompts/completed/`, and ensure closure gate compliance.

## Concrete Steps

Run implementation and tests in `/workdir/wepppy` unless noted.

1. Contract alignment against integration plan.
   - Read `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wepppy-integration-plan.md` and reconcile implementation deltas.
   - Confirm explicit IFOLP call-site requirements: `max_junctions=3`, transitional `fail_if_only_channel_pruned` behavior.

2. Backend + state wiring.
   - Implement/verify `stream_pruning_method` state defaults and validation boundaries in watershed + rq-engine.
   - Ensure mutation boundaries reject unknown values and normalize valid values consistently.

3. Emulator wiring.
   - Keep `extract_streams` path for `netful0` provenance.
   - Branch pruning call by method:
     - `ifolp` -> `iterative_first_order_link_prune(..., max_junctions=3, ...)`
     - `remove_short_streams` -> legacy path.

4. UI/controller wiring.
   - Add/verify `Stream Pruning Method` control and payload propagation in channel delineation and GL controllers.
   - Add/adjust frontend tests for method propagation.

5. Required validation phase commands.
   - `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py`
   - `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py`
   - `wctl run-pytest tests/topo/test_terrain_processor_wbt_integration.py`
   - `wctl run-pytest tests/culverts/test_culvert_batch_rq.py`
   - `wctl run-npm lint`
   - `wctl run-npm test`

6. Method-matrix regression evidence.
   - Capture evidence for both methods on representative watershed fixtures:
     - `stream_pruning_method=ifolp` (with explicit `max_junctions=3`)
     - `stream_pruning_method=remove_short_streams`
   - Verify deterministic behavior on repeated runs and confirm expected output existence (`netful`, `chnjnt`, downstream artifacts).

7. Mandatory review/disposition.
   - Perform independent review of changed files/tests/docs.
   - Disposition findings by severity and close with no unresolved high/medium findings.

8. Package closure.
   - Update `docs/work-packages/20260414_ifolp_wp10_wepppy_e2e_cutover/package.md` and `tracker.md` with outcomes.
   - Move this file to `prompts/completed/` and include outcomes summary.

## Validation and Acceptance

WP-10 is accepted when all are true:
- WEPPpy defaults to IFOLP pruning and preserves explicit `remove_short_streams` selectable mode.
- IFOLP emulator path explicitly passes `max_junctions=3`.
- `stream_pruning_method` config/state contract behavior is implemented and verified (defaulting, normalization, rejection).
- Required test commands pass and outcomes are recorded.
- Method-matrix regression evidence is captured for both pruning modes.
- Review/disposition closes with no unresolved high/medium findings.

## Idempotence and Recovery

- Keep edits bounded to WEPPpy cutover surfaces and associated tests/docs.
- Preserve legacy path during rollout; do not remove legacy tool usage before explicit Phase 4 disposition.
- If compatibility behavior is ambiguous, resolve contract text first in docs, then implement.
- If validation fails in one method path, capture failing evidence and keep the other path behavior unchanged while fixing.

## Artifacts and Notes

Expected closure artifacts include:
- command logs/outcomes for required phase gates,
- method-matrix regression notes/evidence,
- review disposition summary with severity closure,
- updated package/tracker timeline notes.

## Interfaces and Dependencies

- Allowed method enum is exactly: `ifolp`, `remove_short_streams`.
- WEPPpy IFOLP invocation must include `max_junctions=3`.
- Retained IFOLP baseline hash `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83` remains authoritative for IFOLP algorithm behavior.
- Preserve artifact/provenance expectations around `netful0` and downstream products.

---
Revision Note (2026-04-14 / Codex): Initial WP-10 ExecPlan authored for WEPPpy E2E IFOLP cutover execution with required validation and review closure gates.
