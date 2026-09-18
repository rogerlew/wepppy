# Local validation - MOFE propagation correction

## Candidate and scope

Contract ancestors: `ecda89e45` and `f1a4a75b4`. Implementation changes only
`wepppy/nodb/core/landuse.py` and `wepppy/rq/project_rq.py`. No new queue edge,
schema, dependency, scientific value, or recovery mechanism.

The three propagation corrections also close two necessary canopy workflow
links: the public coverage mutation invokes the existing writer, and MOFE
summary rebuilding retains explicit canopy selections. Single-OFE behavior and
RAP precedence remain unchanged.

## Reproduction and artifact evidence

`tests/nodb/test_mofe_scenario_artifacts.py` uses actual management templates,
the management parser/writer, and a real SBS raster with raw values 0/1/2/3/255.
The SBS object returns classified 130/131/132/133/130. Before correction the
landuse builder collapses all five segments to baseline class 50. Afterward it
writes the intended 50/406/418/405/50 assignments and corresponding management
cover values.

Before correction, stored 0.30 and 0.50 overrides both produce 0.40 management
cover. Afterward the public canopy mutation produces the selected values in
combined files and the real management preparation reader/writer preserves them
in `wepp/runs/p1.man`. Unrelated soil and slope work is isolated in this test.

Global mapping tests inspect the actual management file at completion publication.
A directory occupying the output path forces the actual writer to raise
`IsADirectoryError`; no completion is published, assignment rollback holds, and
retry after removing the obstruction writes the requested class. Controller locks
and Redis are isolated; live identity/persistence evidence remains a Forest gate.

Additional tests cover summary retention at 0.0/0.3/0.5, absent/empty assignments,
nonsequential segments, and RAP taking precedence over an explicit 0.3 override.

## Commands and results

- Focused suite: `wctl run-pytest tests/nodb/test_mofe_scenario_artifacts.py tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py tests/nodb/test_landuse_mofe_process_pool.py tests/nodb/test_landuse_modify.py tests/rq/test_project_rq_mutation_guards.py -q --maxfail=1`
  passed 90 tests before the additional nonsequential regression.
- Related suite: `wctl run-pytest tests/nodb tests/rq tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1 -q`;
  running, transcript `/tmp/mofe-related-tests.log`.
- Repository suite: `wctl run-pytest tests --maxfail=1 -q`; running, transcript
  `/tmp/mofe-full-tests.log`.
- `wctl check-test-stubs`: PASS.
- `wctl check-rq-graph`: PASS after regenerating source-line references. All 146
  edges compare equal when excluding `source_lineno`; no topology changed.
- Broad exception enforcement: PASS after updating the existing fork-boundary
  allowlist line from 2678 to 2682; no catch was added or removed.
- Code-quality observability ran in observe-only mode, outputs
  `/tmp/mofe-code-quality.json` and `/tmp/mofe-code-quality.md`; local Radon is
  unavailable, so no cyclomatic-complexity result is claimed.
- Eleven changed Markdown files passed `wctl doc-lint`; canonical contract
  spelling preview and `git diff --check` passed.
- Independent correctness and secondary QA: PASS, no blocking code findings.

## Remaining gate

Actual-project Forest acceptance has not run. Forest is clean and idle but on
`feature/project-owned-config`, so the explicit branch-switch instruction is
pending. Production repair remains separately gated on Roger's deployment.
