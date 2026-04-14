# WP-00 Evidence: Orchestration Bootstrap and Fixtures
Status: done  
Last Updated: 2026-04-14  
Work-Package: `WP-00`

References:
- Plan: `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- Spec: `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`

## Scope Target
- Create work-package evidence scaffold.
- Create initial Geneva fixture manifest for tests.
- Add a schema/manifest test under `tests/nodb/mods/geneva/`.
- Record conformance-deviation disposition evidence (`DEV-001..DEV-004`).

## Bootstrap Artifacts Created
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/README.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp_evidence_template.md`
- `/workdir/wepppy/tests/data/geneva/README.md`
- `/workdir/wepppy/tests/data/geneva/fixtures_manifest.json`
- `/workdir/wepppy/tests/data/geneva/synthetic_small_watershed_v1/bound.tif`
- `/workdir/wepppy/tests/data/geneva/synthetic_small_watershed_v1/landuse.tif`
- `/workdir/wepppy/tests/data/geneva/synthetic_small_watershed_v1/hydgrpdcd.tif`
- `/workdir/wepppy/tests/data/geneva/synthetic_small_watershed_v1/burn_severity.tif`
- `/workdir/wepppy/tests/data/geneva/synthetic_small_watershed_v1/fixture_metadata.json`
- `/workdir/wepppy/tests/nodb/mods/geneva/test_fixture_manifest.py`

## Conformance-Deviation Disposition Evidence
- `DEV-001`: Approved in specification deviation table.
- `DEV-002`: Approved in specification deviation table.
- `DEV-003`: Approved in specification deviation table.
- `DEV-004`: Approved in specification deviation table.

## Execution Checklist
- [x] Add at least one small synthetic fixture case and expected outputs.
- [x] Run focused Geneva fixture tests via `wctl run-pytest`.
- [x] Update WP-00 board row state and evidence links.
- [x] Complete QA + security checklist items from implementation plan.

## QA + Security Checklist Outcomes
- QA gate: pass. Fixture includes `burn_severity` values `0..3` (unburned + burned classes) and documents provenance/limits in `fixture_metadata.json` plus `tests/data/geneva/README.md`.
- Security gate: pass. Fixture is synthetic only, contains no secrets, and carries no sensitive location data.
- Manual integration gate: pass. Fixture inputs are stored as repository-relative paths in `fixtures_manifest.json` and validated by `tests/nodb/mods/geneva/test_fixture_manifest.py::test_geneva_fixture_inputs_exist`.

## Validation Executed
- `wctl doc-lint --path wepppy/nodb/mods/geneva/specification.md` (pass)
- `wctl doc-lint --path wepppy/nodb/mods/geneva/implementation-plan.md` (pass)
- `wctl doc-lint --path wepppy/nodb/mods/geneva/work-packages/wp-00_orchestration_bootstrap_and_fixtures.md` (pass)
- `wctl run-pytest tests/nodb/mods/geneva/test_fixture_manifest.py --maxfail=1` (pass)
- `wctl run-pytest tests/nodb/mods/geneva --maxfail=1` (pass; `4 passed, 2 warnings`)
- `wctl doc-lint --path wepppy/nodb/mods/geneva` (pass; `6 files validated, 0 errors, 0 warnings`)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass; `Changed Python files scanned: 0`, `Net delta: +0`)
