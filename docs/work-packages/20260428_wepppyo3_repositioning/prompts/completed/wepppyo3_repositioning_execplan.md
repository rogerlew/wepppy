# wepppyo3 Repositioning ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package is executed, maintainers and agents will understand `/workdir/wepppyo3` as WEPPpy's native kernel and interchange substrate rather than as a loose bundle of Rust speedups. A reader should be able to open the README and quickly answer: why this repo matters, which modules are production-critical, how it differs from Peridot and `weppcloud-wbt`, how release artifacts are promoted, and which performance claims are confirmed versus only inferred.

The visible result is a repositioned README plus canonical docs that future work packages can cite when deciding whether a new hot-path implementation belongs in `wepppyo3`.

## Progress

- [x] (2026-04-28 17:20 UTC) Reviewed codebase shape, release package, tests, and WEPPpy callsites.
- [x] (2026-04-28 17:20 UTC) Determined posture: `wepppyo3` is the WEPPpy native kernel and interchange substrate.
- [x] (2026-04-28 17:20 UTC) Created package scaffold, posture artifact, tracker, and active ExecPlan.
- [x] (2026-04-28 17:38 UTC) Rewrote `/workdir/wepppyo3/README.md` front matter and positioning.
- [x] (2026-04-28 17:38 UTC) Added canonical module registry under `/workdir/wepppyo3/docs/`.
- [x] (2026-04-28 17:38 UTC) Added architecture/boundaries, release/provenance, and claim-discipline docs.
- [x] (2026-04-28 17:38 UTC) Aligned relevant WEPPpy references.
- [x] (2026-04-28 17:38 UTC) Ran scoped validation and closed package.

## Surprises & Discoveries

- Observation: `wepppyo3` has nine deployable PyO3 modules in `release/linux/py312/wepppyo3/`, plus internal Rust support crates.
  Evidence: release package contains `climate`, `raster_characteristics`, `roads_flowpath`, `sbs_map`, `swat_interchange`, `swat_utils`, `watershed_abstraction`, `wepp_interchange`, and `wepp_viz` shared libraries.

- Observation: WEPPpy production callsites already treat `wepppyo3` as infrastructure.
  Evidence: imports appear in climate, landuse, soils, roads, SWAT, WEPP interchange, MOFE, RHEM, RAP, Omni, BAER/SBS, and WEPP visualization paths.

- Observation: The current README is useful as a catalog but weak as positioning.
  Evidence: it starts with "Rust/PyO3 extension modules for wepppy" and then lists APIs, while the repo now carries multiple production contracts and release concerns.

- Observation: `wepppyo3` has no repo-local Markdown lint wrapper comparable to WEPPpy `wctl doc-lint`.
  Evidence: no doc tool was found during execution, so closure used manual relative-link validation plus `git diff --check` for `/workdir/wepppyo3`.

## Decision Log

- Decision: Position `wepppyo3` as WEPPpy's native kernel and interchange substrate.
  Rationale: The repo is a shared Python-callable Rust substrate for production compute, raster, and file-interchange contracts. "Accelerator bundle" undersells its role and makes ownership boundaries unclear.
  Date/Author: 2026-04-28 / Codex.

- Decision: Keep runtime behavior and binary deployment out of this package.
  Rationale: The requested work is posture/repositioning. Release provenance gaps should be documented first, then handled by separate implementation packages.
  Date/Author: 2026-04-28 / Codex.

- Decision: Add a dedicated `docs/claim-discipline.md` instead of embedding all claim rules only in the README.
  Rationale: The README should orient readers quickly; benchmark and communication wording needs a reusable canonical reference for future work packages.
  Date/Author: 2026-04-28 / Codex.

## Outcomes & Retrospective

Completed as a docs-first repositioning. `/workdir/wepppyo3/README.md` now states the native kernel and interchange substrate posture up front, links to canonical docs, and preserves the API surface. The new docs define the module registry, boundaries, release provenance, and claim discipline. WEPPpy references were aligned in active architecture/dependency docs and README files. No runtime behavior, release shared objects, or deploy artifacts changed.

Remaining work is intentionally follow-up scope: binary release manifest/version stamping, deeper module maturity audit if support labels become policy, and benchmark evidence curation for high-visibility modules.

## Context and Orientation

The primary documentation/work-package repository is `/workdir/wepppy`. The codebase being repositioned is `/workdir/wepppyo3`, a Rust workspace that builds Python extension modules used by WEPPpy.

`wepppyo3` currently has workspace members for climate processing (`cli_revision`), a Geneva hydrology core (`geneva_core`), shared raster IO (`raster`), raster characteristics, roads flowpath tracing, SBS map processing, SWAT interchange, SWAT utilities, watershed abstraction helper kernels, WEPP interchange, and WEPP visualization. The canonical deployable Python package is under `/workdir/wepppyo3/release/linux/py312/wepppyo3/`.

The important boundary is that `wepppyo3` does not replace WEPPpy orchestration. WEPPpy remains responsible for routes, NoDb state, RQ orchestration, run directories, and user-facing workflows. `wepppyo3` owns narrow native kernels and file interchanges where Rust materially improves correctness, throughput, memory behavior, or parser reliability.

`wepppyo3` also does not replace Peridot. Peridot owns watershed abstraction as a standalone Rust graph/CLI engine. `wepppyo3.watershed_abstraction` currently owns helper kernels that remain Python-callable from WEPPpy, such as MOFE map label assignment.

## Plan of Work

Milestone 1 updates `/workdir/wepppyo3/README.md`. Replace the opening with a clear "why this matters" statement and the posture: WEPPpy's native kernel and interchange substrate. Preserve the module catalog, but reorganize it around production contracts rather than a flat list of functions.

Milestone 2 adds `/workdir/wepppyo3/docs/module-registry.md`. For each module, record purpose, release artifact, WEPPpy callsites, maturity classification, primary tests, and evidence status. Use cautious labels such as production-critical, production-used, optional/fallback, internal support, or incubating; do not make operational policy claims without evidence.

Milestone 3 adds `/workdir/wepppyo3/docs/architecture-and-boundaries.md`. Explain what belongs in `wepppyo3`, what belongs in Peridot, what belongs in `weppcloud-wbt`, and what remains in Python. Include examples from existing modules so future agents can route work correctly.

Milestone 4 adds `/workdir/wepppyo3/docs/release-provenance.md`. Document the canonical `release/linux/py312/wepppyo3/` layout, current manual copy workflow, source/provenance gaps, and a follow-up plan for version stamping or release manifest generation. Do not rebuild binaries in this package.

Milestone 5 aligns WEPPpy references where appropriate. Prioritize docs that explain dependency posture, performance baselines, or native module ownership. Avoid broad churn in historical completed work-package records unless a link or claim is actively misleading.

Milestone 6 validates and closes. Run scoped doc lint in WEPPpy, run any available doc validation for wepppyo3 if present, run `git diff --check` in touched repos, update tracker/package closure notes, and update `PROJECT_TRACKER.md` lifecycle state.

## Concrete Steps

Start by checking worktrees:

    cd /workdir/wepppy
    git status --short --untracked-files=all
    cd /workdir/wepppyo3
    git status --short --untracked-files=all

Read the posture artifact:

    cd /workdir/wepppy
    sed -n '1,240p' docs/work-packages/20260428_wepppyo3_repositioning/artifacts/2026-04-28_codebase_posture_review.md

Edit docs in `/workdir/wepppyo3` first, then align WEPPpy references. Keep changes docs-only unless the user explicitly expands scope.

Validation commands from `/workdir/wepppy`:

    wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260428_wepppyo3_repositioning
    git diff --check

Validation command from `/workdir/wepppyo3`:

    git diff --check

If any code or release artifact changes are introduced despite the docs-first scope, run targeted cargo/pytest validation before handoff.

## Validation and Acceptance

Acceptance is met when a reader can open `/workdir/wepppyo3/README.md` and immediately understand the native-substrate posture, then follow links to module registry, architecture/boundaries, and release/provenance docs.

The work-package tracker must show real progress timestamps and closure notes. `PROJECT_TRACKER.md` must move the package through lifecycle states if execution starts or completes.

Documentation validation must pass for changed WEPPpy package docs. If no wepppyo3 doc lint exists, record manual link/path validation in the validation artifact.

## Idempotence and Recovery

This package is docs-first and should be safe to rerun. Do not modify `.so` files, `target/`, or `release/linux/py312` binaries. If runtime edits accidentally enter the diff, either revert only those package-owned edits or document why scope changed before proceeding.

The WEPPpy worktree may contain unrelated dirty files. Do not stage, rewrite, or normalize unrelated RQ/cache-guard work.

## Artifacts and Notes

Initial artifacts:

- `artifacts/2026-04-28_codebase_posture_review.md`
- `artifacts/2026-04-28_validation_summary.md`

Closure artifact:

- `artifacts/2026-04-28_validation_summary.md`

## Interfaces and Dependencies

Primary source paths:

- `/workdir/wepppyo3/README.md`
- `/workdir/wepppyo3/Cargo.toml`
- `/workdir/wepppyo3/*/Cargo.toml`
- `/workdir/wepppyo3/release/linux/py312/wepppyo3/`

Primary WEPPpy reference paths:

- `/workdir/wepppy/PROJECT_TRACKER.md`
- `/workdir/wepppy/docs/standards/dependency-evaluation-standard.md`
- WEPPpy module docs that mention `wepppyo3` as a performance baseline or optional accelerator.

Claim labels:

- `confirmed`: directly observed in code, release files, tests, or existing artifacts.
- `inference`: conclusion drawn from confirmed evidence with stated assumptions.
- `hypothesis`: plausible future benefit or unmeasured claim.

## Revision Notes

- 2026-04-28 / Codex: Initial ExecPlan authored after codebase review and posture determination.
- 2026-04-28 / Codex: ExecPlan completed and archived after docs-first repositioning, WEPPpy reference alignment, and validation.
