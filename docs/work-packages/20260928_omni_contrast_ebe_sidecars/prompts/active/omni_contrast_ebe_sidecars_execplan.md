# Repair and verify Omni contrast EBE sidecar integrity

This ExecPlan is a living document maintained according to `docs/prompt_templates/codex_exec_plans.md`. The required `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` sections must remain current.

## Purpose / Big Picture

After this work, an Omni contrast that requests watershed event-by-event output cannot silently lose its outlet-channel selection merely because channel diagnostic output is disabled. Operators can rerun the affected `strategic-eloquence` contrasts and verify daily outlet records by reading the generated Parquet metadata rather than trusting job success.

## Progress

- [x] (2026-09-29 00:00Z) Isolated missing `chan.inp` as the cause and ruled out path length.
- [x] (2026-09-29 00:00Z) Audited the historical sidecar set and scaffolded the package.
- [x] (2026-09-29 00:20Z) Implemented explicit EBE sidecar preparation and inheritance regression coverage; 83 focused tests pass.
- [ ] Run focused tests, documentation lint, broad tests, and changed-exception enforcement (focused 83/83, docs, and exception gate pass; broad suite passed through 22% and remains to complete).
- [ ] Regenerate the 69 production contrasts and validate raw and Parquet artifacts (delegated to Jackson by operator direction; Codex canceled all 70 deferred repair jobs before execution).
- [ ] Complete reviews, tracker, and retrospective.

## Surprises & Discoveries

- Observation: `chan.inp` is not only a `chan.out` diagnostic trigger. WEPP reads it into `nchnum`/`ichnum`, and the EBE writer iterates that same selection.
  Evidence: `/workdir/wepp-forest_260430_baseline/src/wshinp.for` lines 475-484 and `src/sedout.f90` lines 466-482.
- Observation: historical contrast assembly copied every ordinary parent run sidecar, then output-trigger logic deleted `chan.inp` and `tc.txt` when their diagnostic flags were false.
  Evidence: parent-versus-contrast inventory for `strategic-eloquence` contrast 1.
- Observation: a production control with the same output flags proves the repaired behavior. `honeyed-marathoner` has `chan.inp` and populated EBE Parquets in all 100 contrasts generated July 14, while all 69 June 29 `strategic-eloquence` contrasts lack both.
  Evidence: direct PyArrow metadata and filesystem readback on `wepp1`.

## Decision Log

- Decision: Preserve inherited sidecars and additionally prepare `chan.inp` whenever either `chan_out` or `ebe_pw0` is enabled.
  Rationale: This states the real consumer dependency while retaining backward-compatible inherited configuration.
  Date/Author: 2026-09-29 / Codex.
- Decision: Let sidecar preparation errors propagate.
  Rationale: A warning followed by a successful header-only artifact violates the repository rule favoring explicit failure over hidden recovery.
  Date/Author: 2026-09-29 / Codex.

## Outcomes & Retrospective

Pending implementation and production artifact verification.

## Context and Orientation

`wepppy/nodb/mods/omni/omni_clone_contrast_service.py` builds each contrast workspace and inherits files from the parent `wepp/runs` directory. `wepppy/nodb/mods/omni/omni.py::_apply_contrast_output_triggers` prepares optional WEPP trigger files. `chan.inp` contains the outlet channel selection used by both channel diagnostic output and watershed EBE output. `tests/nodb/mods/test_omni.py` owns focused orchestration regression coverage.

The affected project is `/wc1/runs/st/strategic-eloquence` in containers and `/geodata/wc1/runs/st/strategic-eloquence` on the `wepp1` host. It contains 69 contrast workspaces under `_pups/omni/contrasts`.

## Plan of Work

First amend the trigger helper so `ebe_pw0=True` requires `chan.inp` just as `chan_out=True` does, preserving an inherited file and preparing it only when absent. Remove warning-only exception suppression so a missing required input fails before model execution. Add focused tests for EBE-only preparation, inherited sidecar preservation, failure propagation, and clone inheritance of representative sidecars while excluding contrast-owned run/log files.

Then run focused NoDb Omni tests and repository gates. On `wepp1`, preflight services and queue activity, rerun only the affected contrast set using the existing Omni route/job contract, poll the job tree, and verify all 69 raw EBE files and Parquets semantically. Do not rerun parent hillslopes or full scenarios unless the established contrast job contract requires it.

## Concrete Steps

From `/home/workdir/wepppy`, edit the helper and tests with `apply_patch`, then run:

    wctl run-pytest tests/nodb/mods/test_omni.py --maxfail=1
    wctl doc-lint --path docs/work-packages/20260928_omni_contrast_ebe_sidecars
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl run-pytest tests --maxfail=1

Before production mutation, verify `wepp1`, the run path, services, queue state, and the canonical Omni rerun endpoint or RQ function. After completion, read each `ebe_pw0.parquet` with PyArrow metadata and require 69 files, zero zero-row files, successful WEPP completion logs, and unchanged contrast identifiers.

## Validation and Acceptance

The regression test must demonstrate that EBE-only options create `chan.inp`, existing contents are preserved, and preparation failure is visible. The clone test must demonstrate representative sidecars (`chan.inp`, `tc.txt`, `snow.txt`, `wepp_ui.txt`) resolve in the child while `pw0.run` and `pw0.err` are not inherited. Production acceptance requires semantic readback of every generated EBE Parquet; job completion alone is insufficient.

## Idempotence and Recovery

Local tests are repeatable. Contrast regeneration replaces only numbered contrast workspaces using the established Omni cleanup path. Before submission retain a manifest of contrast ids and historical artifact metadata. If the batch fails, identify and rerun only failed contrast jobs; do not restart the stack or delete parent/scenario artifacts.

## Artifacts and Notes

The historical signature is 69 valid Parquets, each with 15 columns and zero rows. Contrast 1 has positive average annual outlet discharge near 71.5 million cubic metres per year despite its empty EBE table.

Production repair queue evidence:

    upstream finalizer: 2ac9c8ea-1103-440c-a289-beb82ee7098d
    repair jobs: 69, batch size 6
    first repair job: 1b33c3e4-2ffd-4e54-8fe7-6b102a5dde07
    repair finalizer: dd705c3d-bcc6-4705-a6e4-7ed5cfd484ef

All 70 repair-tagged jobs above were canceled in `deferred` state on operator
direction. They are retained here only as an audit record; Jackson owns the
fresh production rerun and final artifact verification.

## Interfaces and Dependencies

No new dependency is introduced. `_apply_contrast_output_triggers(wepp, output_options)` remains the interface. Its postcondition becomes: when `output_options["chan_out"]` or `output_options["ebe_pw0"]` is true, `<runs_dir>/chan.inp` exists or the function raises before WEPP execution.
