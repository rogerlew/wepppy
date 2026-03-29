# Features Export Artifact README Metadata Packaging ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, every features-export zip artifact will include a deterministic, human-readable `README.md` that summarizes what was exported, how it was produced, and how to interpret key metadata fields, while preserving `manifest.json` as the machine-readable source of truth. Users will be able to open one zip and immediately understand request settings, layer inventory, units, CRS behavior, dependency lineage, and warnings without manually parsing JSON.

## Progress

- [x] (2026-03-29 20:15Z) Reviewed current `features_export` spec/service/manifest contracts and identified available README inputs.
- [x] (2026-03-29 20:33Z) Updated `wepppy/nodb/mods/features_export/specification.md` with standards baseline, metadata availability assessment, and dynamic README packaging contract.
- [x] (2026-03-29 20:45Z) Authored work-package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- [x] (2026-03-29 20:00Z) Implemented `wepppy/nodb/mods/features_export/readme_builder.py` with deterministic section ordering, table rendering, and absolute-path redaction for relpath fields.
- [x] (2026-03-29 20:01Z) Integrated cache-miss publication flow in `service.py` to generate/write `README.md` and include it in `bundle_member_sources` and planned packaged member relpaths.
- [x] (2026-03-29 20:03Z) Extended `tests/nodb/mods/test_features_export_service.py` coverage for zip membership (`README.md` + `manifest.json` + payload), README/manifest consistency assertions, cache-hit packaged member propagation, and deterministic README redaction behavior.
- [x] (2026-03-29 20:06Z) Ran required backend/doc validation commands and captured exact pass results in tracker/closeout notes.

## Surprises & Discoveries

- Observation: The current `features_export` implementation already carries enough metadata to generate a useful first-pass artifact README without adding new upstream science contracts.
  Evidence: `manifest.json` currently includes resolved request, layer row/feature counts, selected columns/units, dependency fingerprint and dependency entry details, CRS metadata, and warning payloads.

- Observation: Packaging policy in recent package history changed multiple times (include profile/provenance files, then remove profile/provenance files), so the README contract must be explicit to avoid another oscillation.
  Evidence: `docs/work-packages/20260328_features_export_profiles_provenance_zip/package.md` vs current `wepppy/nodb/mods/features_export/specification.md` contract text prior to this update.

- Observation: Cache-hit manifest packaging metadata can remain aligned without new cache-hit README generation because `_artifact_metadata_from_cache_entry(...)` already rehydrates `packaged_member_relpaths` directly from cache index entries.
  Evidence: `test_execute_features_export_cache_hit_returns_new_job_id_and_source_job_id` now asserts `README.md` is present in cache-hit `manifest["artifact"]["packaged_member_relpaths"]` after a cache-miss seed run.

## Decision Log

- Decision: Generate README as a deterministic derivative of resolved manifest metadata rather than introducing a parallel metadata authority.
  Rationale: Prevents drift and keeps one canonical machine-readable contract.
  Date/Author: 2026-03-29 / Codex.

- Decision: Keep profile files excluded from artifact bundles while including generated README.
  Rationale: Profile replay already has route-level contracts; bundling profiles creates duplicate truth sources.
  Date/Author: 2026-03-29 / Codex.

- Decision: Keep README provenance pointer implicit via `artifact.packaged_member_relpaths` and bundle root member name (`README.md`) rather than adding a new manifest field such as `readme_relpath`.
  Rationale: Existing artifact member contract already communicates member presence deterministically; adding another field would duplicate pointer data without improving consumer behavior.
  Date/Author: 2026-03-29 / Codex.

## Outcomes & Retrospective

Implementation completed end-to-end for the package scope. Features-export cache-miss publication now generates a deterministic artifact `README.md`, includes it in zip bundles with payload members and `manifest.json`, and preserves profile-file exclusion. Cache-hit flows remain artifact-reuse based and continue to emit job-scoped manifests while carrying `README.md` membership through cached `packaged_member_relpaths`.

Validation outcomes:
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py -k "readme or manifest or cache_hit" --maxfail=1` -> `2 passed, 57 deselected`.
- `wctl run-pytest tests/nodb/mods/test_features_export_manifest.py tests/nodb/mods/test_features_export_exporters.py --maxfail=1` -> `21 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` -> `21 passed`.
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1` -> `59 passed` (extra confidence run beyond required checklist).
- `wctl doc-lint --path ...` for specification/package/tracker/execplan -> all passed with `0 errors, 0 warnings`.

## Context and Orientation

The relevant code path starts in `wepppy/nodb/mods/features_export/service.py`, where artifact payload members are assembled and zipped. Manifest generation currently occurs through `wepppy/nodb/mods/features_export/manifest.py` and `write_export_manifest(...)`, then `package_files_as_zip(...)` builds the final download bundle. The current bundle contract already includes deterministic zip member ordering.

The most relevant existing files are:
- `wepppy/nodb/mods/features_export/service.py` - cache-miss and cache-hit artifact orchestration.
- `wepppy/nodb/mods/features_export/manifest.py` - machine-readable metadata assembly/serialization.
- `wepppy/nodb/mods/features_export/manifest_builder.py` - output-layer column metadata helper.
- `wepppy/nodb/mods/features_export/specification.md` - normative contract.
- `tests/nodb/mods/test_features_export_service.py` - packaging and cache-flow tests.
- `tests/nodb/mods/test_features_export_manifest.py` - manifest contract tests.

## Plan of Work

Milestone 1 introduces a new README-builder helper module under `wepppy/nodb/mods/features_export/` that takes resolved export metadata and returns deterministic Markdown text. The helper will define section order, table formatting, and allowed fields, and will sanitize content to avoid host-path leakage.

Milestone 2 wires the helper into the cache-miss publication flow in `service.py`: after manifest generation and before final zip creation, write `README.md` into artifact directory and add it to `bundle_member_sources`. Ensure final `packaged_member_relpaths` includes README and update any in-memory artifact metadata object if needed.

Milestone 3 addresses cache-hit behavior and consistency checks. Cache-hit jobs should continue to reuse the cached artifact bundle, which already contains README once produced by cache-miss path. Job-scoped manifest generation remains unchanged except where pointer consistency is required.

Milestone 4 adds regression coverage and contract assertions. Tests should verify: zip contains README + manifest + payload members, README sections exist, selected key values match manifest fields, and cache-hit result shape still behaves as expected.

Milestone 5 runs targeted validation commands, updates this plan and package tracker with evidence, and prepares closeout artifacts.

## Concrete Steps

Work from `/workdir/wepppy`.

1. Implement README builder module and unit-level formatting helper tests (if split needed).
2. Update `service.py` bundle assembly to include generated `README.md`.
3. Update manifest/service metadata pointers only if required by final contract.
4. Extend existing tests to cover README packaging and consistency.
5. Run validation commands and capture pass/fail counts in tracker.

Expected command sequence:

    cd /workdir/wepppy
    wctl run-pytest tests/nodb/mods/test_features_export_service.py -k "readme or manifest or cache_hit" --maxfail=1
    wctl run-pytest tests/nodb/mods/test_features_export_manifest.py tests/nodb/mods/test_features_export_exporters.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1
    wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md
    wctl doc-lint --path docs/work-packages/20260329_features_export_artifact_readme_metadata/package.md
    wctl doc-lint --path docs/work-packages/20260329_features_export_artifact_readme_metadata/tracker.md
    wctl doc-lint --path docs/work-packages/20260329_features_export_artifact_readme_metadata/prompts/active/features_export_artifact_readme_metadata_execplan.md

## Validation and Acceptance

Acceptance is met when:
- A cache-miss features-export run produces a zip that contains payload members, `manifest.json`, and `README.md`.
- README content includes required sections and values that match manifest fields.
- Cache-hit job execution still returns canonical response shape and download path with reusable artifact behavior.
- Targeted tests and doc-lint commands pass.

## Idempotence and Recovery

The implementation is additive and idempotent at artifact-generation boundaries. Re-running the same request should overwrite/replace artifact README content deterministically for newly generated artifacts while cache-hit requests reuse existing artifacts. If a README-generation failure occurs, fail export explicitly with a service-layer error rather than silently emitting an artifact without README.

## Artifacts and Notes

Target README section outline (v1):

    # Features Export Artifact Metadata

    ## Export summary
    ## Standards and interpretation notes
    ## Resolved request profile
    ## Layer inventory
    ## Column and unit summary
    ## Dependency lineage summary
    ## Warning summary
    ## Machine-readable contract pointer

## Interfaces and Dependencies

Proposed module/interface additions:

- In `wepppy/nodb/mods/features_export/readme_builder.py`, define:

    def build_export_readme(*, manifest: Mapping[str, object], runid: str, config: str) -> str:
        ...

- In `wepppy/nodb/mods/features_export/service.py`, invoke README build/write during cache-miss finalization and include `README.md` in `bundle_member_sources` before `package_files_as_zip(...)`.

- Keep dependencies internal to stdlib + existing module contracts; do not add external packages.

Revision Note (2026-03-29, Codex): Initial ExecPlan authored to implement standards-aligned dynamic artifact README generation and zip-plumbing for features_export.
Revision Note (2026-03-29, Codex): Updated plan as a living document after implementation, including completed progress checkboxes, validation evidence, final decisions, and outcomes for package closure.
