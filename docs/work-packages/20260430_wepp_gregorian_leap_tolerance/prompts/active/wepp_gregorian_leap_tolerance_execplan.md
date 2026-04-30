# Patch WEPP Leap-Year Logic to Gregorian Rules While Preserving Centurial Day-366 Tolerance

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this patch, WEPP will stop misclassifying centurial years such as `100` as leap years when February has 28 days. At the same time, legacy climate files that still include a 366th day for non-400 centurial years will continue to run (tolerated behavior), so existing data pipelines are not broken. Success is visible when year-100 runs no longer emit false leap warnings for 28-day February, while year-100 366-day inputs still complete without fatal stops.

## Progress

- [x] (2026-04-30 07:19Z) Authored package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- [x] (2026-04-30 07:19Z) Captured contract decision: Gregorian classification + tolerant handling for non-400 centurial day-366 inputs.
- [x] (2026-04-30 08:05Z) Implemented canonical Gregorian leap-year branch pattern in `/workdir/wepp-forest/src` at all active call sites (`stmget.for`, `wshpas.for`, `contin.for`, `wshdrv.for`), with explicit non-400 centurial day-366 tolerance branches where day-count/loop selection occurs.
- [x] (2026-04-30 08:21Z) Added centurial-edge replay evidence: `year100/365` no false leap warning after patch, `year100/366` tolerated run completion, `year2000/366` leap control preserved.
- [x] (2026-04-30 08:41Z) Passed required `wepp-forest` gates; vendored release `wepp_260430` binaries into `wepppy`; passed provenance, smoke, and focused `wepp_runner` regression gates.
- [x] (2026-04-30 08:53Z) Re-ran the full `wepp-forest` gate set on the patched tree (`smoke`, `watchlist 12/12`, `ablation policy`, `pytest -q` `79 passed`) to confirm reproducible pass status before final handoff.

## Surprises & Discoveries

- Observation: Active leap checks are inconsistent across call sites (`mod(year,4)` and `mod(year+1,4)` patterns) rather than one shared helper.
  Evidence: `/workdir/wepp-forest/src/stmget.for`, `/workdir/wepp-forest/src/wshpas.for`, `/workdir/wepp-forest/src/contin.for`, `/workdir/wepp-forest/src/wshdrv.for`.

- Observation: Existing fixtures already include explicit year-100 warning evidence, which can be used for before/after validation.
  Evidence: `/workdir/wepp-forest/tests/fixtures/reconciled_condenser_pw0/logs/pw0.stdout` contains `Leap year detected ... year  100`.

- Observation: `wshpas` and watershed/day-loop drivers (`contin` and `wshdrv`) needed separate but aligned tolerance variables because `ndays` and `lp` are computed in different call frames.
  Evidence: `/workdir/wepp-forest/src/wshpas.for`, `/workdir/wepp-forest/src/contin.for`, `/workdir/wepp-forest/src/wshdrv.for` now each carry `legacy_centurial_day366` alongside Gregorian classification.

- Observation: Existing centurial replay harness artifacts under `/tmp/wepp_leap_cases` were sufficient for regression evidence without adding new fixture files to repo history.
  Evidence: `/tmp/wepp_leap_cases/case100_365/stdout.txt` (before warning), `/tmp/wepp_leap_cases/case100_365/stdout_after.txt` (warning removed), plus `case100_366` and `case2000_366` `stdout_after.txt` success markers.

## Decision Log

- Decision: Use Gregorian leap-year classification (`divisible by 4`, except `divisible by 100` unless also `divisible by 400`) as the canonical rule.
  Rationale: Aligns runtime calendar semantics with standard leap-year definitions and removes false positives for centurial years like 100.
  Date/Author: 2026-04-30 / User + Codex.

- Decision: Keep compatibility tolerance for non-400 centurial years when climate input includes day 366.
  Rationale: Avoids breaking legacy climate datasets and long-lived operational archives.
  Date/Author: 2026-04-30 / User + Codex.

- Decision: Implement one shared branch pattern inline at each active call site rather than introducing a new global Fortran helper.
  Rationale: Smallest-risk patch in this codebase; avoids cross-unit linkage/interface churn while still making all active call sites semantically consistent.
  Date/Author: 2026-04-30 / Codex.

## Outcomes & Retrospective

Implementation completed end-to-end for release `wepp_260430`.

What changed:
- Runtime leap classification now follows Gregorian semantics at the four active leap call sites in `/workdir/wepp-forest/src`.
- Non-400 centurial day-366 tolerance remains supported in day-count/loop-selection branches (`wshpas`, `contin`, `wshdrv`).
- Changelog synchronized in both `wepp-forest` and vendored `wepppy` copy.

Validation summary:
- `wepp-forest` gates passed: smoke (`wepp`, `wepp_hill`), watchlist (`12/12`), ablation policy gate, and `pytest -q` (`79 passed, 2 warnings`).
- Centurial controls confirmed:
  - `year100/365`: false leap warning removed after patch.
  - `year100/366`: run completes successfully (tolerated behavior).
  - `year2000/366`: leap behavior preserved.
- Vendored `wepppy` gates passed:
  - `tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_260430 wepp_runner/bin/wepp_260430_hill`
  - `tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_260430`
  - `tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_260430_hill`
  - `pytest -q tests/wepp_runner/test_run_hillslope_retries.py tests/wepp/test_wepp_runner_outputs.py` (`8 passed`)

Release artifact hashes:
- `wepp_260430`: `ecee0f1a7eb223801a9f289f6a52628106a336fb7a4a3f752ae7c0b1c3301ec0`
- `wepp_260430_hill`: `5b1d758e2544446beb0c7a5ca36cfa8ec7ee54b605195ebeb08f0dc58e9ce2bc`

## Context and Orientation

The patch target is `/workdir/wepp-forest` (source-of-truth for WEPP binaries). The relevant call sites today are:

- `/workdir/wepp-forest/src/stmget.for`
  - Emits leap warning text and currently checks `mod(year,4)`.
- `/workdir/wepp-forest/src/wshpas.for`
  - Determines per-year `ndays` (`365/366`) using `mod(year,4)`.
- `/workdir/wepp-forest/src/contin.for`
  - Sets leap-year branch flag `lp` via `mod(year+1,4)`.
- `/workdir/wepp-forest/src/wshdrv.for`
  - Mirrors `contin.for` leap flag behavior.

After source patching and validation in `wepp-forest`, binaries are vendored to:

- `wepppy/wepp_runner/bin/wepp_<tag>`
- `wepppy/wepp_runner/bin/wepp_<tag>_hill`

and changelog synchronization is required in:

- `/workdir/wepp-forest/change-log.md`
- `wepppy/weppcloud/routes/usersum/vendor/wepp-forest/change-log.md`

## Plan of Work

Milestone 1 implements one canonical leap-year decision path and removes the ad hoc modulo checks at the four active runtime call sites. The implementation can be either a shared helper function or a consistent inlined branch pattern, but all four files must use the same semantics.

Milestone 2 introduces compatibility tolerance behavior for non-400 centurial years that still include day 366 in input. Tolerance means the run completes without fatal abort and without false leap-missing-day messaging for the 28-day case. If a compatibility warning is retained, it must be explicit and non-fatal.

Milestone 3 adds regression validation for three control scenarios:

- year 100 with 28-day February (no false leap warning),
- year 100 with explicit day 366 (tolerated run completion),
- year 2000 leap behavior preserved.

Milestone 4 runs full required build/test gates in `wepp-forest`, updates changelog, then vendors binaries into `wepppy` and runs provenance/smoke/focused runner tests.

## Concrete Steps

All source edits and binary builds run in `/workdir/wepp-forest`.

1. Inventory and patch call sites.

    rg -n "mod\(year,4\)|mod\(year\+1,4\)|Leap year detected" /workdir/wepp-forest/src -S

    Edit:
    - `/workdir/wepp-forest/src/stmget.for`
    - `/workdir/wepp-forest/src/wshpas.for`
    - `/workdir/wepp-forest/src/contin.for`
    - `/workdir/wepp-forest/src/wshdrv.for`

2. Build binaries.

    cd /workdir/wepp-forest/src
    make clean
    make wepp
    make wepp_hill

3. Run required `wepp-forest` gates.

    cd /workdir/wepp-forest
    tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp
    tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp_hill
    python tools/run_hillslope_watchlist.py --binary /workdir/wepp-forest/src/wepp_hill
    python tools/check_ablation_artifact_policy.py
    pytest -q

4. Run explicit centurial control replays and capture logs.

    - Replay a year-100, Feb-28 case and assert no false leap-warning block.
    - Replay a year-100 day-366 case and assert non-fatal completion.
    - Replay a year-2000 case and assert leap behavior still present.

5. Update `wepp-forest` changelog.

    - Add top entry in `/workdir/wepp-forest/change-log.md` with new hashes and validation evidence.

6. Vendor into `wepppy` and validate.

    cd /workdir/wepppy
    install -m 0755 /workdir/wepp-forest/src/wepp wepp_runner/bin/wepp_<tag>
    install -m 0755 /workdir/wepp-forest/src/wepp_hill wepp_runner/bin/wepp_<tag>_hill
    cp /workdir/wepp-forest/change-log.md wepppy/weppcloud/routes/usersum/vendor/wepp-forest/change-log.md
    tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_<tag> wepp_runner/bin/wepp_<tag>_hill
    tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_<tag>
    tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_<tag>_hill
    pytest -q tests/wepp_runner/test_run_hillslope_retries.py tests/wepp/test_wepp_runner_outputs.py

## Validation and Acceptance

Acceptance requires all of the following:

- False leap warning for year `100` with 28-day February is removed.
- Non-400 centurial year with explicit day 366 remains runnable and non-fatal.
- Year `2000` leap handling remains correct.
- `wepp-forest` required gates pass (smoke, watchlist, ablation policy, pytest).
- Vendored binaries in `wepppy` pass provenance and smoke gates.
- Focused wepp_runner regression tests pass.
- Both changelogs (`wepp-forest` + vendored usersum copy) are updated.

## Idempotence and Recovery

- Source patching is idempotent when constrained to the four identified call sites.
- If centurial tolerance causes broad drift, revert only leap-contract changes and rerun control replays before wider rollback.
- Vendoring should happen only after all `wepp-forest` gates pass, so retries are safe and traceable.

## Artifacts and Notes

Required artifacts/evidence:

- Before/after log excerpts for year-100 warning behavior.
- Centurial day-366 tolerance run transcript with successful completion marker.
- Hashes for vendored binaries and changelog entries.
- Validation command outputs summarized in tracker progress notes.

## Interfaces and Dependencies

End-state contract expectations:

- Runtime leap classification aligns with Gregorian rule in all active leap call sites.
- Legacy non-400 centurial day-366 climates are tolerated and non-fatal.
- No change to WEPPcloud route/API contracts; only binary behavior and vendored artifacts update.

---

Revision note (2026-04-30 07:19Z): Initial ExecPlan authored from incident reproduction and user contract directive.
Revision note (2026-04-30 08:41Z): Execution completed through vendoring and post-vendor validation gates for `wepp_260430`.
Revision note (2026-04-30 08:53Z): Required `wepp-forest` validation suite rerun on patched tree; pass status unchanged.
