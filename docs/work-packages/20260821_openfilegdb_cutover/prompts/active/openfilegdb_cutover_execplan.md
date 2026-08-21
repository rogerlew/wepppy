# Replace the f-esri sidecar with direct OpenFileGDB conversion

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current, and update
this plan together with `docs/work-packages/20260821_openfilegdb_cutover/tracker.md`.

## Purpose / Big Picture

WEPPcloud geodatabase exports should be generated inside the normal GDAL
3.10.3 worker runtime without an Esri SDK, an idle sidecar, or a Docker exec
hop. Users continue requesting `geodatabase` and receiving the same named
`.gdb.zip` artifacts. Operators can observe the result through a real export,
archive inspection, GIS-client open, and the absence of `f-esri` from rendered
and deployed stacks.

## Progress

- [x] (2026-08-21 15:38 UTC) Inventory repository coupling and verify direct
  OpenFileGDB creation/readback on wepp1 and forest.
- [x] (2026-08-21 15:45 UTC) Record operator selection of direct OpenFileGDB
  with accepted output caveats.
- [x] (2026-08-21 16:17 UTC) Amend the canonical features-export specification.
- [x] (2026-08-21 16:17 UTC) Add representative direct-backend
  characterization; external-client evidence remains.
- [x] (2026-08-21 16:17 UTC) Implement direct conversion and
  capability/error/cleanup tests.
- [x] (2026-08-21 16:17 UTC) Remove runtime compatibility and repository
  infrastructure coupling.
- [ ] Complete independent review gates; local validation is complete with
  documented unrelated blockers.
- [ ] Validate forest; obtain separate authorization before production deploy.

## Surprises & Discoveries

- Observation: GDAL 3.10 does not make `FileGDB` an alias for native creation.
  Evidence: runtime lists only `OpenFileGDB`; GDAL documents FileGDB creation
  delegation beginning in 3.11.
- Observation: default OpenFileGDB output converts Integer64 to Float64.
  Evidence: both host smoke runs emitted the warning and returned the sample
  values as floats. Native Integer64 requires the ArcGIS Pro 3.2+ layer option.
- Observation: `co_create_post_wepp_geodatabase_artifact` checks the
  `has_f_esri` function object rather than calling it.
  Evidence: `if not f_esri.has_f_esri:` is always false for the imported
  function. Replace this boundary rather than preserving the bug.
- Observation: the old archive placed `.gdbtable` files at the ZIP root, while
  GDAL's direct `.gdb.zip` contract expects a `.gdb` directory at the first
  level.
  Evidence: the final integration test opens the generated `.gdb.zip` directly
  after asserting every member begins with `output.gdb/`.

## Decision Log

- Decision: Explicitly select `OpenFileGDB` and remove the Esri SDK path.
  Rationale: functional host evidence passed and the operator accepted output
  caveats; explicit naming is required on GDAL 3.10.
  Date/Author: 2026-08-21 / operator and Codex.
- Decision: Retain the legacy request alias `f_esri`.
  Rationale: it is backward-compatible persisted/API input, not infrastructure.
  Date/Author: 2026-08-21 / Codex.
- Decision: Use default broad ArcGIS compatibility for initial output.
  Rationale: the old driver also lacks Integer64 support; forcing the Pro 3.2+
  option would introduce a new client-version constraint.
  Date/Author: 2026-08-21 / operator and Codex.
- Decision: Package the `.gdb` directory itself rather than only its contents.
  Rationale: preserves the public `.gdb.zip` name and enables documented direct
  GDAL archive access plus conventional extraction.
  Date/Author: 2026-08-21 / Codex.

## Outcomes & Retrospective

Implementation outcome: direct replacement and infrastructure removal are
complete locally. Focused and broad changed-area tests pass, supported Compose
topologies render, and the generated archive opens directly through GDAL.
Independent review, external-client evidence, and deploys remain.

## Context and Orientation

`wepppy/nodb/mods/features_export/exporters/geodatabase.py` stages a GeoPackage
then delegates conversion to `wepppy/f_esri/__init__.py`. That helper invokes
`ogr2ogr -f FileGDB` inside `wepppy-f-esri`, adjusts modes, and creates the ZIP.
`wepppy/nodb/mods/features_export/service.py` repeats that boundary for
post-WEPP co-creation. The common worker already contains GDAL 3.10.3 with the
built-in OpenFileGDB writer.

Read `package.md`, `tracker.md`, the feasibility inventory, root `AGENTS.md`,
`wepppy/nodb/AGENTS.md`, `docker/AGENTS.md`, and `tests/AGENTS.md` before edits.
Treat `wepppy/nodb/mods/features_export/specification.md` as the feature-export
authority and amend it before behavior changes.

## Plan of Work

First, characterize one representative generated staging GeoPackage and the
old and new outputs. Record layer names, spatial/non-spatial status, geometry
types and dimensions, CRS, field names/types/nullability, row counts, selected
values, archive layout, file modes, warnings, and runtime. Include empty layers
and the largest relevant numeric identifiers. The goal is behavioral parity,
not binary identity.

Next, add one direct conversion boundary owned by the features-export package
or a shared geospatial module only if a second genuine caller requires it. Use
an argument-array subprocess invoking `ogr2ogr -f OpenFileGDB`, retain the
existing bounded timeout, capture stdout/stderr, fail explicitly when the
driver cannot create vector datasets, remove prior/partial targets safely, and
produce the existing `.gdb.zip`. Avoid shell execution and silent fallback.
Make both ordinary export and post-WEPP co-creation call that boundary.

Then replace f-esri mocks with direct-boundary tests. Exercise successful
multi-layer conversion with real GDAL, missing-driver behavior, nonzero exit,
timeout, cleanup, permissions, ZIP layout, and representative schema/value
readback. Retain tests for the legacy request alias.

After the code path passes, remove `wepppy/f_esri`, root `f_esri.py`, unused
`all_your_base.geo` wrappers and stubs, dedicated helper tests,
`docker/Dockerfile.f-esri`, Compose services/dependencies, vendor `.pth` lines,
CI ref inputs, host setup, CAO clone, and affected documentation. Before
removing Docker-socket mounts, inventory each service independently for other
callers.

Finally, render every supported Compose variant, build the common image, run
focused and broad gates, complete correctness/security reviews, and deploy to
forest for an unmocked export. Production removal and deployment require a
normal operator-approved deploy window and must follow the wepp1 operator
runbook.

## Concrete Steps

Run from `/home/workdir/wepppy`:

    rg -n 'f-esri|f_esri|F_ESRI' .
    wctl run-pytest tests/nodb/mods/test_features_export_exporters.py tests/nodb/mods/test_features_export_service.py --maxfail=1
    wctl check-test-stubs
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

Render all changed Compose combinations with their normal `docker compose
config`/`wctl` entry points. Record exact commands and results here rather than
assuming that deletion from the base file covers overrides.

For documentation:

    wctl doc-lint --path docs/work-packages/20260821_openfilegdb_cutover
    diff -u <file> <(uk2us <file>)

## Validation and Acceptance

Acceptance requires all of the following:

1. A real features export produces the expected `.gdb.zip` through
   OpenFileGDB without Docker exec.
2. Readback matches the accepted schema/value policy and the archive survives
   normal download/extract/open behavior.
3. An operator-approved external GIS client opens the result.
4. Existing cached artifacts remain valid.
5. Every supported Compose render contains no `f-esri` service/dependency and
   all affected services start healthy on forest.
6. Focused tests and the full pre-handoff suite pass, and independent
   correctness and security reviews have no unresolved medium/high findings.

## Idempotence and Recovery

Conversion must remove only its exact artifact-local staging `.gdb` and ZIP.
Retries must start from a clean target and must never publish a partial ZIP.
Infrastructure removal should be additive-code-first, subtraction-second so
the direct path is testable before the sidecar disappears. Forest rollback is
the prior image/Compose revision; production rollback follows the deployment
runbook and restores the prior `f-esri` service until the direct-path defect is
resolved.

## Artifacts and Notes

- `artifacts/2026-08-21_feasibility_inventory.md` records host and coupling
  evidence.
- Add characterization transcripts and review artifacts under `artifacts/`.
- Do not store exported run data, secrets, or large geodatabases in Git.

## Interfaces and Dependencies

At completion, the conversion interface accepts source GeoPackage and target
`.gdb` paths plus a bounded timeout, returns the generated target/archive, and
raises a narrow features-export error containing actionable GDAL diagnostics.
It uses the already-installed GDAL 3.10.3 command-line/runtime dependency and
the `OpenFileGDB` driver. No new dependency is introduced.

Plan revision note (2026-08-21): Initial scaffold created after operator
selection of direct OpenFileGDB and acceptance of documented output caveats.

Plan revision note (2026-08-21 16:17 UTC): Updated all living sections after
implementation, infrastructure subtraction, archive-layout correction, and
local validation; retained independent review and rollout as explicit work.
