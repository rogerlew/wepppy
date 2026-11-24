# Refactor Omni controller tests by responsibility

## Purpose

Make the Omni tests easier to find and run. Keep scenarios and controller state in `tests/nodb/mods/test_omni.py` and give workspace cloning, contrast selection, contrast artifacts, stream order and contrast execution their own modules.

## Progress

- [x] 2026-11-22 05:35 UTC. Established a 229-case passing Omni baseline.
- [x] 2026-11-22 05:37 UTC. Move cases and centralize shared setup.
- [x] 2026-11-22 05:39 UTC. Verify parity, measure quality and close local implementation.

## Surprises & Discoveries

The original import fixture installs geospatial dependency stubs, while neighboring Omni modules already import the controller against the real dependencies. Two GeoJSON tests mutate attributes on the rasterio module and stream-order tests set an attribute on the wepppyo3 package directly.

## Decision Log

Use the real runtime dependency imports and keep test-specific substitutes scoped through pytest's monkeypatch restoration. This lets each extracted module run independently and avoids leaving stale geospatial attributes for later tests.

## Outcomes & Retrospective

All 229 Omni tests passed in both runs and the 83 controller cases also passed
in reverse module order. All seven Python files are below the red thresholds.
The [validation record](../../artifacts/validation.md) contains the commands,
case parity, source metrics and runner receipts.

## Context and Orientation

The old file spans 3,687 physical lines. The quality tool measures 2,973 source lines and a longest function of 153 lines. Sibling Omni service tests exercise the same production imports and provide neighboring regression coverage.

## Plan of Work

Move whole test definitions into modules named for their responsibilities. Share the isolated legacy policy fixture and existing geometry test doubles. Extract repeated stream-order raster setup and patch dependencies through monkeypatch. Document the new selection in `tests/README.md`.

## Concrete Steps

From the task worktree, run the following before and after editing, with a different JUnit output filename for each run.

    wctl run-pytest --profile python -- tests/nodb/mods/test_omni*.py -q --junitxml=.wctl-test-runs/omni-after.xml

Measure the baseline and changed Python files with `tools/code_quality_observability.py` and lint the package and changed guides with `wctl doc-lint`.

## Validation and Acceptance

Expect the same 229 case names and parameter IDs to pass. Review every changed test body and preserve its assertions and decorators. Expect no resulting Python file to cross a red severity threshold.

## Idempotence and Recovery

Focused runs use an isolated candidate container and can be repeated with a fresh JUnit report. Use a new follow-up commit for any correction to the merged refactor.

## Artifacts and Notes

Keep validation results and receipt IDs in the package artifacts.

## Interfaces and Dependencies

The shared test module exports a fixture that imports the Omni controller and applies the legacy policy for each test. Geometry test doubles support selection and artifact cases. Existing production entry points and file contracts stay intact.
