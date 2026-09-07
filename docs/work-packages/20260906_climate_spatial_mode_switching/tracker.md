# Climate spatial mode switching tracker

## Status

Closed 2026-09-07 03:29 UTC; implemented locally with unrelated broad-suite failure documented.

## Task board

- [x] Assess source and unchanged canonical authority.
- [x] Create package and active ExecPlan.
- [x] Add failing render regression and controller switching coverage.
- [x] Repair template and update user/developer guidance.
- [x] Run focused, frontend, broad, and documentation gates (broad failure disposition below).
- [x] Obtain independent correctness review (no introduced findings).
- [x] Disposition broad pytest and close package.

## Decisions

2026-09-07 03:13 UTC: Conformance fix, no normative contract changes or ancestor
commit. Derive the rendered spatial union from the supplied selectable catalog,
then preserve per-dataset enablement and exact-current compatibility.

## Verification

2026-09-07 03:18 UTC: Before patch, the available-Daymet/Vanilla render test
failed because mode 2 was absent. After patch, focused template and Flask climate
suites passed: 212 tests. Focused Jest: 17 passed. Frontend lint passed.
Full pytest/Jest and independent correctness review are in progress.
Host Python lacks Jinja2; bundle rebuild uses the canonical running container.

2026-09-07 03:18 UTC: Full frontend suite passed (108 suites, 835 tests).
Bundle rebuilt in the running weppcloud container with no generated diff.
Docs lint and changed broad-exception enforcement passed. Code-quality
observability completed (non-blocking; host radon unavailable). Spelling preview
found only unrelated pre-existing "labelled" in the controller README, left intact.

## Known limitation outside this fix

Independent review noted that existing `climate.js:updateSpatialModes` ignores
`disabled_spatial_modes` and `current_selection_disabled`. Disabled legacy-current
markup can therefore be re-enabled during bootstrap. This patch preserves the
initial template state; it does not claim to repair that separate controller path.

2026-09-07 03:19 UTC: Independent correctness review passed; artifact is
`artifacts/20260906_correctness_review.md`. Broad pytest remains the last gate.

## Final validation and disposition — 2026-09-07 03:29 UTC

| Gate | Result |
| --- | --- |
| Pre-patch render regression | Failed on absent interpolated radio, as expected |
| Template and climate route pytest | 212 passed |
| Climate Jest | 17 passed |
| Full frontend Jest | 108 suites, 835 tests passed |
| Frontend lint | Passed |
| Bundle rebuild | Passed in container; no generated changes |
| Documentation lint | Passed |
| Broad exception enforcement | Passed; no changed production Python |
| Code-quality observability | Completed, non-blocking; radon unavailable |
| Full pytest, maxfail=1 | 5078 passed, 50 skipped, 1 failed in 648.53 seconds |
| Independent correctness | Passed for scoped fix, no introduced findings |

The broad failure is
`tests/shape_converter/unit/test_runtime_hardening.py::test_prod_wepp1_overlay_does_not_override_shape_converter_hardening`.
It asserts `shape-converter` is absent from the production wepp1 Compose overlay,
but that service is present. The test and `docker/docker-compose.prod.wepp1.yml`
are unchanged from starting HEAD. An isolated run reproduced the same failure
(1 failed in 9.61 seconds). This unrelated existing test/config mismatch is not
repaired by a climate UI package. Full-suite success is not claimed; tests after
the maxfail stop were not executed in that broad run.

No deployment or live climate-generation job was performed. The focused suite
runs the real Jinja template, and Jest exercises the existing controller. No
parameterization, persistence, or execution boundary changed.

## Outcome

The rendered spatial union now survives dataset switching and uses only
selectable datasets supplied by run authority. DAYMET/GRIDMET interpolation
help and user/developer guidance are updated. The unchanged canonical contracts
remain authoritative; package.md "Authority and compatibility" records the
conformance rationale. Closed ExecPlan is in prompts/completed/.
