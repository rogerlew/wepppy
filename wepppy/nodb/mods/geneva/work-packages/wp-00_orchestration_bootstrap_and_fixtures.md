# WP-00 Evidence: Orchestration Bootstrap and Fixtures
Status: ready_for_execution  
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
- `/workdir/wepppy/tests/nodb/mods/geneva/test_fixture_manifest.py`

## Conformance-Deviation Disposition Evidence
- `DEV-001`: Approved in specification deviation table.
- `DEV-002`: Approved in specification deviation table.
- `DEV-003`: Approved in specification deviation table.
- `DEV-004`: Approved in specification deviation table.

## Execution Checklist
- [ ] Add at least one small synthetic fixture case and expected outputs.
- [ ] Run focused Geneva fixture tests via `wctl run-pytest`.
- [ ] Update WP-00 board row state and evidence links.
- [ ] Complete QA + security checklist items from implementation plan.

## Validation Executed
- `wctl doc-lint --path wepppy/nodb/mods/geneva/specification.md` (pass)
- `wctl doc-lint --path wepppy/nodb/mods/geneva/implementation-plan.md` (pass)
- `wctl doc-lint --path wepppy/nodb/mods/geneva/work-packages/wp-00_orchestration_bootstrap_and_fixtures.md` (pass)
- `wctl run-pytest tests/nodb/mods/geneva/test_fixture_manifest.py --maxfail=1` (pass)
