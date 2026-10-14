# Preserve temperature ordering in every PRISM spatialization writer

This living plan follows `docs/prompt_templates/codex_exec_plans.md`. Execute package `20261013_prism_temperature_ordering`; keep this plan and its tracker current. The operator authorized execution. All milestones are complete; see the package report for evidence and limitations.

## Purpose / Big Picture


A climate build should not emit minimum temperature above maximum solely because PRISM adjusted the extrema independently. After implementation, crossed adjusted extrema share their arithmetic midpoint, valid days retain existing output, and users can see when correction occurred. The result must reach the climate actually consumed by WEPP through the real native and Python paths.

## Progress


- [x] (2026-10-13 23:52 UTC) Package and accepted ADR authored from the operator-approved, measured midpoint proposal.
- [x] M1: Review and commit canonical contract checkpoint before implementation.
- [x] M2: Implement matching Rust/Python semantics and diagnostic reporting; verify exact writers.
- [x] M3: Build and identify the imported native extension; validate project artifacts, 24 retained revisions, fresh WEPP consumption, and performance.
- [x] M4: Close review findings, run gates, update durable documentation, and commit handoff.

M1 ancestor: `7bd7707c2`. M2 checks: 23 Rust tests and 76 focused Python tests pass. Six fresh WEPP executions consume actual native/EDDE rewrites.

## Surprises & Discoveries


The Python public PRISM function is not WEPPcloud's daily production writer. `wepppy/nodb/core/climate_build_helpers.py:cli_revision` calls `wepppyo3.climate.cli_revision` for ordinary daily climates and uses Python only for breakpoint files. The Rust formula lives in `wepppyo3/cli_revision/src/lib.rs:rust_cli_revision`. All four paths named in the package must be covered.

The candidate study in `docs/work-packages/20261013_edde_v2_feasibility/artifacts/prism-inversion-patch-evaluation.json` repaired 15 days in three rejected climates and left all 21 accepted revision DataFrames identical. The three corrected climates each completed a fresh 20-year WEPP run. Existing serializer rounding changes some auxiliary values during any rewrite; compare against each writer's unrepaired output, not against the raw source, to isolate this patch. Different language formatters may treat ties differently; verify ordering and bounded numerical parity without gratuitously replacing serializers.

Native arithmetic retains `(source - reference) + target`; EDDE retains `source + (target - reference)`. Floating-point equality can therefore produce different sub-femtodegree correction counts while serialized temperatures agree within existing 0.1 C precision. No tolerance or arithmetic reassociation was introduced. The project validation harness initially used a nonexistent `Climate.load`; corrected to canonical `load_detached`, preserving the failed attempt.

## Decision Log


2026-10-13, operator/Codex: the operator accepted the midpoint recommendation and requested a work-package and ADR. ADR-0092 is accepted for implementation, not evidence of installed code. Use `a / 2 + b / 2` only when finite adjusted Tmin `b` exceeds adjusted Tmax `a`; both become that value. This preserves the extremes' midpoint, minimizes squared adjustment, and leaves valid days untouched. Equality is acceptable; no positive range floor, one-sided preference, swapping, or redistribution to other days.

Use current native ownership. No Python postprocessing replacement for the Rust daily writer, no new dependency, and no existing-project rebuild or deployment. Correction logging and additive EDDE manifest fields require a precise contract before implementation; no public signature change is assumed.

## Context and Orientation


Workspaces are `/home/workdir/wepppy` and `/home/workdir/wepppyo3` (also available under `/workdir`). Read root and nearest AGENTS in each before editing. Read `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`, `docs/standards/contract-first-change-standard.md`, `docs/standards/parameterization-adr-standard.md`, and artifact-validation standards. The native crate is `cli_revision_rust`; release ownership/build conventions are in wepppyo3 `README.md`, `docs/module-registry.md`, and `docs/release-provenance.md`. Do not invent a parallel deployment or release path.

The other writers are `wepppy/climates/prism/__init__.py:prism_revision`, the breakpoint branch of `wepppy/nodb/core/climate_build_helpers.py:cli_revision`, and `wepppy/climates/edde/cligen.py:revise_prism`. The EDDE adapter validates source climates then rejects revised inversions; replace only that introduced-inversion rejection with the accepted correction, preserving source/finite/date/precipitation/provenance checks and new-output ownership.

The proposed ADR retains its stable filename `docs/adrs/ADR-0092-prism-temperature-inversion-midpoint-proposal.md` even after acceptance. ADR-0091 and `docs/schemas/edde-v2-experimental-client-contract.md` describe former rejection behavior and need a precise prospective amendment during M1. `docs/schemas/climate-parquet-lineage-contract.md` remains authoritative for build-stage ownership and finalization; assess whether amendment is needed, without broadening those semantics. Promote a generic numerical contract under `docs/schemas/prism-spatialization-temperature-contract.md` before code changes.

## Plan of Work


M1 creates `artifacts/<date>_contract_decision.md` with both starting revisions, the affected canonical contract set, source-versus-adjustment invalidity, additive EDDE metadata fields, existing-log diagnostic content, compatibility/security impact, operator provenance, and regression evidence. Ratify only the approved numerical delta. Enumerate absent/new output, populated/reused output, legacy manifests without optional repair metadata, malformed input, and native extension version states separately from daily/breakpoint/model/mode combinations. Obtain two independent read-only contract reviews as required by the standard, disposition findings, and commit a standalone ancestor checkpoint. Record its hash in tracker; no NoDb-coupled implementation can precede it. Planning documents alone are not this checkpoint.

M2 adds minimal tested numerical code. Python writers can share a narrow helper; Rust implements the same rule in its existing streaming writer. Preserve existing valid output bytes wherever the same serializer is retained and require numerical unchanged-day parity everywhere. Validate finite operands and output without silently normalizing malformed source records. Define rejection cases before coding; avoid adding unrelated input restrictions to supported legacy paths. Record affected count, maximum inversion, and adjustment using existing logs; the EDDE companion manifest records its additive repair information. No new Rust public return type is presumed. Add Rust and Python tests for valid/equal/crossed extrema, negative values, zero range, month transitions, near-equality/rounding ties, and nonfinite values. Exercise the actual daily and breakpoint file readers/writers, including breakpoint precipitation timing records.

M3 follows the canonical native build process for the climate crate, retaining the exact source revision, compiler, command, artifact hash, Python version, and imported module path. The package includes an affected-module build/release refresh with provenance when required by the existing installation mechanism; no unrelated shared objects may change. Prove the existing development container imports the newly built module, not a stale installed copy. Run the NoDb helper through its actual Rust branch and the real Python breakpoint branch. Use a scratch project with real normals/raster sampling and normal build/preparation mechanisms; do not substitute mocked GDAL or manufactured files for the changed boundary. Preserve identity, groups, mounts, umask, and configuration in evidence. Verify generated climate, prepared `wepp/runs/` climate, fresh WEPP outputs, and report/export readback. No live source project is mutated.

Reuse hash-verified archived source climates and frozen hillslopes from the feasibility package. Rewrite the candidate harness or add a new implementation harness so acceptance calls the patched public writers and loaded extension; re-running its local midpoint calculation is not implementation proof. Reproduce 24 revisions, preserve 21 accepted climates, repair 15 days, and run all three formerly rejected 20-year climates through WEPP. Add a non-EDDE source case and a real breakpoint case. Quantify midpoint rounding, monthly extrema-mean perturbation, and applicable historical/future changes; do not invent a universal drift threshold from the prototype. Measure native elapsed time with the same representative file before/after; no pure-Python replacement or new performance claim is authorized.

M4 obtains a correctness review using `docs/prompt_templates/correctness_review_template.md` and resolves medium/high findings. Security remains low for current scope; re-triage any new boundary. Update affected climate/native module docs, ADR implementation status, durable contract conformance, and package trackers. Report exactly which source and release revisions are wired and validated. Do not claim deployment or run repair from development acceptance.

## Concrete Steps


From `/home/workdir/wepppy`, inspect `git status --short` and preserve unrelated work, especially the generated usersum docs index. Inspect the sibling repo similarly; do not create/switch branches without authorization. After M1 and implementation, use `wctl run-pytest tests/climates/test_edde_client.py tests/climates/test_edde_cligen.py` plus the new temperature-revision tests, then `wctl run-pytest tests/nodb/test_climate_build_helpers.py` and relevant observed Multiple/breakpoint tests discovered at M1. From `/home/workdir/wepppyo3`, run `cargo test -p cli_revision_rust` with the repository's required environment; build the climate extension by its canonical documented process. Record real commands and outcomes as work proceeds.

Before handoff run `wctl run-pytest tests --maxfail=1`, affected `wctl run-stubtest` targets, `wctl check-test-stubs`, changed-exception enforcement, code-quality observability, and scoped `wctl doc-lint`. No frontend/RQ graph gates are needed unless actual scope changes touch those surfaces. A prior EDDE broad test run failed an unchanged SBS metadata expectation; reproduce/report the current situation honestly and do not fix unrelated behavior to obtain a green claim. Preserve logs and distinguish completed gates from interrupted runs.

## Validation and Acceptance


Success requires finite ordered extrema after the exact writer serializes them, unchanged valid days and other weather relative to that writer's old behavior, stable dates/file structure, observable repair counts, and direct WEPP consumption. Confirm zero-range days work using the rebuilt implementation. The fixture matrix is finite and not proof for all datasets. Retain binary and input/output hashes alongside semantic checks; file existence or successful job status alone cannot establish correctness.

A real scratch-project build and export/preparation check are required before an environment-validated claim. If project setup or native build is unavailable, continue other independent checks and report the narrower completion state; do not mark this package closed with only a helper or prototype passing.

## Idempotence and Recovery


Use new scratch output directories and verified retained inputs. Preserve failed attempts. Existing source projects and prior study artifacts remain immutable inputs. Native artifact changes use the existing build/release provenance process and have an explicit previous artifact identity for rollback. If corrected files change valid data or fail consumption, revert coordinated source/native changes, restore the EDDE rejection behavior, and retain diagnostics; do not conceal failure with a fallback writer.

## Artifacts and Notes


Keep new checkpoints, review dispositions, exact native build/import evidence, before/after comparisons, timing records, consumed-file hashes, WEPP results, and validation logs under this package's `artifacts/`. Reference prior evidence instead of copying entire source caches. A compact generated/consumed archive is appropriate when its member list and hashes are retained. Record all compatibility/diagnostic field decisions in current canonical docs before package closure.

## Interfaces and Dependencies


Keep existing climate API signatures and Rust import paths. Reuse NumPy and owned Rust arithmetic; no new dependency. No change to queue wiring, NoDb persistence keys, climate schemas, station selection, PRISM normals acquisition, or other forcing fields. Additive EDDE provenance fields must permit reading legacy manifests and distinguish no repair from unavailable historical diagnostics.

## Outcomes & Retrospective


Completed 2026-10-14 UTC. Contract ancestor `7bd7707c2`, native source `d3e51c2`, native release `0515272`. All four writers, native build/import identity, 24 retained comparisons, seven fresh WEPP executions and 200-hillslope project preparation/export checks pass. Focused tests pass 80; Rust tests 23. Independent correctness/artifact review has no open findings. Broad-suite, legacy typing and line-offset allowlist limitations are recorded in the package report. Deployment and EDDE integration remain separate. Source/harness failures and their dispositions are retained, not erased.

M1 review amendment: process logging alone misses durable per-project diagnostic retention. Implement visible per-output `.temperature-ordering.log` with working/completed status in the normal climate/attempt directory, without changing native return values. This is the smallest bounded escalation after verifying separate native/module and project log channels. Add actual canonical ZIP archive/restore plus authenticated browser/download checks for completed/failed climate and log paths. The Historic PRISM downstream `max(raw tdmean, final Tmin)` rule remains unchanged and needs a repaired-day propagation regression.

Final discoveries: required EDDE diagnostics must complete before its manifest declares success; numerical diagnostics measure actual float movement and reject nonrepresentable magnitudes. The canonical project export requires a live logger-enabled Climate instance and its explicit export entrypoint. Fresh-process project preparation matches persisted mappings; same-process selection showed stale state and is a separate follow-up observation. Final review verifies all retained archive members. No temporary mitigation was introduced.
