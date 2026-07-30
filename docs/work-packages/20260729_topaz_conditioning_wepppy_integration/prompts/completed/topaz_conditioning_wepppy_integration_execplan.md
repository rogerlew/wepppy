# Release TopazConditionDem and integrate it into Channel Delineation

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective`
current throughout execution.

## Purpose / Big Picture

After this work, a user of the Weppcloud-WBT Channel Delineation control can
select “Topaz Conditioning Algorithm.” The selection persists through the
existing rq-engine and NoDb boundary, invokes the source-faithful WBT
`TopazConditionDem` release binary, and supplies the conditioned `relief.tif`
to the existing WBT flow and channel stack. New projects using
`disturbed9002_wbt` start with this choice selected.

## Progress

- [x] (2026-07-30 01:24 UTC) Mapped the current UI, controller, route/RQ,
  persistence, emulator, WBT release, config, documentation, and test surfaces.
- [x] (2026-07-30 01:24 UTC) Authored the DOM-05A contract decision, canonical
  field-matrix amendment, ADR-0032, security triage, and package scaffold.
- [x] (2026-07-30 02:02 UTC) Obtained two independent read-only checkpoint
  reviews; both initially returned FAIL with blocking/high/medium findings.
- [x] (2026-07-30 02:16 UTC) Both reviewers returned post-fix PASS after all
  blocking/high/medium findings were dispositioned.
- [x] (2026-07-30 02:24 UTC) Committed the documentation-only checkpoint as
  standalone ancestor `5754a1e06798a2f116a04b5eff4601402e143962`.
- [x] (2026-07-30 02:47 UTC) Built, atomically installed, validated, and
  committed WBT release
  `0f226804e568c12bb698795f352c47ecbc324769`; required containment follow-up
  `47ca8e44730c0691cfcf8ac2bfa106e792254b36` closes the early-output-EOF
  timeout bypass.
- [x] (2026-07-30 03:12 UTC) Implemented the additive `topaz` token,
  prerequisite validation/containment, and config-scoped default.
- [x] (2026-07-30 03:12 UTC) Added/updated contract, unit, integration, and
  generated-output tests; focused gates pass.
- [x] (2026-07-30 03:20 UTC) Passed final gates/reviews, restarted the local
  stack, completed the operator-authorized `austere-inaction` E2E, and
  published closure evidence.

## Surprises & Discoveries

- Observation: DOM-05 is verified, but its canonical field matrix intentionally
  excludes new algorithms, tokens, and defaults.
  Evidence: `artifacts/field_matrix.md` and REM-05 list exactly three tokens and
  exclude algorithm/default changes.

- Observation: WEPPpy imports the wrapper from the sibling repository but
  executes the tracked binary at `/workdir/weppcloud-wbt/WBT/whitebox_tools`.
  Evidence: the canonical WBT release runbook and Docker bind mount.

- Observation: the mutation route does not explicitly allowlist the enum or
  apply the canonical config/run integrity guard, and the defensive NoDb setter
  uses `assert`.
  Evidence: independent operations/security checkpoint review and current
  `watershed_routes.py`/`watershed.py`.

- Observation: the WBT Python wrapper uses `shell=False` but does not yet prove
  bounded process-group cleanup on timeout.
  Evidence: independent operations/security checkpoint review and
  `WBT/whitebox_tools.py`.

- Observation: `_base` is a canonical sentinel rather than a persisted config
  stem, so the new config guard must preserve that special path while rejecting
  mismatches for ordinary config tokens.
  Evidence: retained base-context route test and
  `_is_base_project_context`.

- Observation: a legacy Daymet test installed a fake `whitebox_tools` module
  during collection whenever no earlier test had imported the real module.
  Evidence: the first full suite reached the native Topaz integration after
  4,055 passes and failed on the incomplete fake class; importing the installed
  module before the fallback stub fixed both test orders and the full suite.

- Observation: `wctl check-test-isolation` can print a successful summary after
  pytest exit code 3.
  Evidence: the independent operations/security review reproduced the
  contradictory result. This package relies on explicit order tests and the
  full suite instead.

## Decision Log

- Decision: The canonical value is `topaz`, with label
  `Topaz Conditioning Algorithm`.
  Rationale: It is additive and maps directly to WBT `TopazConditionDem`
  without overloading generic fill/breach terminology.
  Date/Author: 2026-07-30 / operator and Codex.

- Decision: Dispatch with explicit `max_obstruction_width=2`.
  Rationale: Width 2 is TOPAZ's historical WEPPpy control and has exact
  seven-case FILDEP/RELIEF parity evidence; an explicit call does not couple
  scientific behavior to a later wrapper default.
  Date/Author: 2026-07-30 / operator and Codex.

- Decision: Change only `disturbed9002_wbt.cfg`.
  Rationale: The user requested that configuration specifically; persisted
  runs and other configs must not drift.
  Date/Author: 2026-07-30 / operator and Codex.

- Decision: Use staged rollback.
  Rationale: restoring only the new-run config default is immediately safe and
  preserves persisted user choices; full token removal is a separately
  authorized migration, not an implicit rollback step.
  Date/Author: 2026-07-30 / Codex, dispositioning independent review.

- Decision: Treat explicit enum validation, canonical config/run integrity, and
  bounded WBT process cleanup as release prerequisites.
  Rationale: enabling a new native-operation default must not inherit known
  fail-open or unbounded behavior on the same path.
  Date/Author: 2026-07-30 / Codex, dispositioning independent review.

- Decision: Bound `TopazConditionDem` to 540 seconds.
  Rationale: The existing child RQ timeout is 600 seconds; the 60-second margin
  lets the wrapper terminate and reap the process group before RQ abandons the
  worker job. For an effective Topaz selection, elevate a lower configured
  child timeout to 600 seconds while honoring higher values; legacy methods
  retain the configured timeout.
  Date/Author: 2026-07-30 / Codex implementation safety parameter, accepted
  through the operator-authorized work package and independent release review.

- Decision: Mutate local run `austere-inaction` for final E2E after tests and
  reviews.
  Rationale: The operator explicitly authorized this project-scoped validation
  after the original no-run-mutation plan. Contract discovery supplied the
  existing extent/CSA/MCL; only the conditioning token changed.
  Date/Author: 2026-07-30 / operator.

## Outcomes & Retrospective

Complete. The integration shipped locally with exact UI/API/NoDb/RQ/WBT
contracts, config-scoped defaulting, bounded process cleanup, and no silent
fallback. The definitive suite passed 5,598 tests with 58 skips; frontend,
stub, docs, graph, WBT, containment, and seven-case parity gates passed.

After restart, all three Python service roles resolved installed binary
SHA-256
`e5b33364b788f0046db15760320c7b03c6412fda99987f2bbe3ac76ba53b4cd0`.
The authorized `austere-inaction` E2E finished parent job
`30df3081-bed5-4cf1-b75d-63e792d03448` and both children, persisted `topaz`,
and generated relief SHA-256
`b96715730cc157261e894a36140a9bf1bf017733a35eff82616a4d0b733db074`.

Production promotion remains separate: publish both WBT commits, build the
production image from that state, and repeat per-worker path/hash/disposable
execution checks. The known `wctl check-test-isolation` false-success defect is
a tooling follow-up, not a release blocker for this package.

## Context and Orientation

The rendered select is in
`wepppy/weppcloud/templates/controls/channel_delineation_pure.htm`. Both
`channel_delineation.js` and `channel_gl.js` serialize its selected value as
`wbt_fill_or_breach`. The rq-engine parser passes that optional string to
`wepppy/rq/project_rq.py`, which assigns
`Watershed.wbt_fill_or_breach` before `Watershed.build_channels`.

`wepppy/nodb/core/watershed.py` owns validation and persisted configuration.
`wepppy/nodb/core/watershed_mixins.py` passes the value to
`WhiteboxToolsTopazEmulator.delineate_channels`.
`wepppy/topo/wbt/wbt_topaz_emulator.py::_create_relief` currently dispatches
the three legacy tokens to WBT fill/breach methods. The new branch must call
`self.wbt.topaz_condition_dem` with the prepared DEM, `relief_fn`, and explicit
`max_obstruction_width=2`. Downstream D8, flow accumulation, stream
qualification, and channel processing remain unchanged.

The WBT source is `/workdir/weppcloud-wbt`; its canonical release runbook builds
`target/release/whitebox_tools` and atomically installs it at
`WBT/whitebox_tools`. The already-completed WBT parity package contains seven
exact TOPAZ FILDEP/RELIEF golden cases.

## Plan of Work

First complete the contract checkpoint. Register DOM-05A in the Pure UI child
register, project tracker, umbrella tracker, and umbrella ExecPlan; amend the
DOM-05 field matrix; accept ADR-0032; and retain two independent review
artifacts, post-fix confirmations, a disposition, and high-impact security
artifact. Commit only exact DOM-05A documentation hunks as a standalone
ancestor and inspect the cached diff so unrelated dirty-file changes remain
unstaged.

Next implement and test bounded native-process containment in the owned WBT
wrapper, then build and install the current WBT release according to its
runbook with `cargo build --locked`. Verify process-group timeout cleanup,
explicit nonzero exits, source/lockfile/built/installed hashes, preserved prior
binary hash, `TopazConditionDem` discovery/help, the canonical parity harness,
and discovery/execution from each deployment worker host. Commit the WBT
release before the WEPPpy/default release.

Then add `topaz` to the template choices, Watershed validation, emulator
documentation/dispatch, stubs, and relevant request/schema descriptions.
Pin width 2 at dispatch. Add explicit four-token route validation before any
mutation/enqueue, replace the NoDb setter's `assert` with `ValueError`, and add
the canonical path-config/run integrity guard. Change only
`wepppy/nodb/configs/disturbed9002_wbt.cfg`. Preserve the nullable RQ
compatibility behavior and all existing tokens.

Write regression evidence for actual rendered option/selection, both browser
payloads, Watershed configuration and setter behavior, RQ persistence order,
pre-existing legacy-token reload after the config change, normal and
batch/base invalid-enum no-mutation/no-job behavior, config-mismatch ordering,
operation-schema enum, direct WBT emulator dispatch, and native timeout
cleanup. Exercise a disposable fixture/run path to prove the installed binary
creates `relief.tif`; do not mutate production runs.

Finally rebuild generated controllers, update Usersum and developer
documentation, run scoped then broad gates, complete correctness/security
reviews, record binary and output hashes, archive this plan, and close the
package.

## Concrete Steps

Run WEPPpy commands from `/workdir/wepppy` and WBT commands from
`/workdir/weppcloud-wbt`.

    cargo build --locked -p whitebox-tools-app --release
    cp target/release/whitebox_tools WBT/whitebox_tools.new
    chmod 755 WBT/whitebox_tools.new
    mv -f WBT/whitebox_tools.new WBT/whitebox_tools
    WBT/whitebox_tools --toolhelp=TopazConditionDem

    wctl run-pytest tests/topo tests/nodb tests/rq/test_project_rq_mutation_guards.py \
      tests/weppcloud/routes/test_pure_controls_render.py
    wctl run-npm test -- channel_delineation channel_gl
    wctl run-npm lint
    python3 wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl doc-lint --path \
      docs/work-packages/20260729_topaz_conditioning_wepppy_integration

Update this section with exact commands and observed counts as work proceeds.

## Validation and Acceptance

Acceptance requires an ancestor checkpoint preceding every implementation
change. A rendered `disturbed9002_wbt` control must select option value
`topaz`; both controllers must submit that exact value; the worker must persist
it before build; and direct emulator evidence must show one call to
`topaz_condition_dem` with width 2 and no legacy conditioning call.

The freshly installed WBT binary must pass its seven-case canonical parity
harness and produce a conditioned raster through the WEPPpy emulator path.
Legacy values `fill`, `breach`, and `breach_least_cost` must retain existing
tests and behavior. A config other than `disturbed9002_wbt` must remain
unchanged. A pre-existing persisted legacy value must survive reload after the
new config default. Invalid enum and config-mismatch requests must fail before
mutation/enqueue, and a forced WBT timeout must leave no surviving process.

## Idempotence and Recovery

The WBT release installation uses a `.new` file followed by atomic rename and
is safe to repeat. If a post-install check fails, restore the previously
committed `WBT/whitebox_tools`, rebuild, and rerun discovery before allowing
WEPPpy integration tests to proceed. Fixture runs use disposable temporary
directories. No production run may be submitted or mutated.

The new enum is additive. Immediate rollback restores only
`disturbed9002_wbt.cfg` to `breach_least_cost` and retains the option, dispatch,
and binary for persisted projects. Full removal is outside this package and
requires separately authorized inventory/migration, lock/cache-safe mutation,
an audit log, archived/batch handling, failure-atomic recovery, and proof that
no persisted `topaz` remains before old code is deployed.

## Artifacts and Notes

The package `artifacts/` directory retains the contract decision, independent
reviews, security review, disposition, and final validation report. Generated
binary and raster checksums belong in the validation report; large generated
rasters remain in ignored temporary storage.

## Interfaces and Dependencies

The public persisted value set becomes:

    fill | breach | breach_least_cost | topaz

`WhiteboxToolsTopazEmulator._create_relief` accepts the same set. For `topaz`
it calls:

    self.wbt.topaz_condition_dem(
        dem=self.dem,
        output=relief_fn,
        max_obstruction_width=2,
    )

The wrapper and binary come from the owned `weppcloud-wbt` sibling repository;
no new external dependency is introduced.

Revision note (2026-07-30): Initial contract-first plan authored from the
operator-approved request and exact WBT parity evidence.
