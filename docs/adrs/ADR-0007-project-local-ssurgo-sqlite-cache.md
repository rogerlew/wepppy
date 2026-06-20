# ADR: Project-Local SSURGO SQLite Cache

Status: Accepted
Date: 2026-06-19
Review Date: 2026-12-19

## Context

WEPPcloud soil builds that use SSURGO/STATSGO tabular data depend on the NRCS
Soil Data Access service. NRCS can update tabular records independently of a
WEPPcloud project, so the same WEPPcloud code and same spatial inputs can
produce different WEPP soil parameters if the upstream SSURGO rows change
between rebuilds.

The prior implementation used module-level SQLite cache files in
`wepppy/soils/ssurgo/ssurgo.py`, with shared `/dev/shm` copies of bundled
database files when available. That reduced repeated NRCS requests, but it also
allowed stale or host-global cached rows to cross project boundaries. The
project-local cache package changed this behavior so project builds use
run-scoped SQLite cache files under `<wd>/soils/`, direct
`SurgoSoilCollection(...)` calls default to in-memory SQLite, and operators can
clear the project cache before rebuild.

This ADR ratifies that decision despite the remaining non-determinism: the
first build of a project cache, or any rebuild after the cache is explicitly
cleared, can fetch newer NRCS rows and therefore alter generated WEPP soil
inputs.

## Decision

WEPPcloud will use project-local SSURGO/STATSGO SQLite caches for project soil
builds:

- SSURGO project cache: `<wd>/soils/ssurgo_tabular_cache.sqlite`
- STATSGO2 project cache: `<wd>/soils/statsgo_tabular_cache.sqlite`
- Metadata sidecars: `<cache>.meta.md`

Direct `SurgoSoilCollection(mukeys)` usage remains in-memory by default unless
the caller supplies an explicit `cache_db_path`.

The accepted operating contract is:

- A project cache is a run-scoped snapshot of the SSURGO/STATSGO tabular rows
  fetched so far for that project.
- Rebuilds reuse the project cache unless the operator enables
  `Clear SSURGO cache on rebuild`.
- Clearing the cache intentionally opts into a new NRCS fetch for missing rows
  and can change generated WEPP soil parameters if upstream data changed.
- The adjacent Markdown sidecar records human-readable provenance for the cache
  artifact; the SQLite database remains the canonical machine-readable cache.
- Cache paths and metadata sidecar paths are derived from the active
  `Soils.soils_dir`; absolute cache paths are not serialized in NoDb state.

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: Codex request thread with Roger Lew, 2026-06-19 21:38 UTC
Participants Present: Roger Lew, Codex
Decision Owner(s): Roger Lew / WEPPcloud operator request
Implementer(s): Codex

## Change Summary

Old behavior:

- Project builds and direct SSURGO collection callers used the module-level
  SSURGO/STATSGO SQLite cache paths initialized by `ssurgo.py`.
- When `/dev/shm` was available, those caches were shared host-level files
  copied from bundled SSURGO/STATSGO databases and then mutated with fetched
  NRCS rows.
- Cache reuse could cross project boundaries and could keep stale rows after
  NRCS updated SSURGO.

New behavior:

- Project builds pass an explicit project-local cache path under `<wd>/soils/`.
- Direct callers use an in-memory SQLite database unless they opt into a file
  cache by passing `cache_db_path`.
- Existing projects create the project cache on the next soil rebuild without a
  migration step.
- The `clear_ssurgo_cache_on_rebuild` option is persisted in `Soils` and allows
  an operator to delete the project cache before rebuild.
- Cache clearing removes only the SQLite cache, exact SQLite sidecars
  `<cache>-wal` and `<cache>-shm`, and `<cache>.meta.md`.
- Each file-backed cache writes `<cache>.meta.md` with NRCS source provenance,
  endpoint, runtime context, and table counts.

Parameterization impact:

- Same-project rebuilds are stable with respect to previously cached SSURGO rows
  while the project cache is retained.
- New projects, legacy projects rebuilding for the first time after this change,
  and projects rebuilt after cache clearing can fetch current NRCS rows and may
  produce different WEPP soil inputs than earlier builds.
- Two projects with identical spatial inputs can differ if their project caches
  were populated at different times relative to NRCS data updates.

## Rationale

The project-local cache is the least-bad option for operational reproducibility.
It prevents host-global stale cache contamination while preserving a project
snapshot after the first fetch. Operators get a visible rebuild control for
cases where current NRCS data is desired, and the metadata sidecar makes the
cache artifact auditable.

The decision intentionally prioritizes run-scoped reproducibility over global
bitwise determinism. Full determinism would require pinning or vendoring every
SSURGO row used by a project at a named source vintage, which is outside the
current package scope and would be a larger data-governance project.

## Alternatives Considered

1. Keep the shared module-level cache - Rejected. It can preserve stale rows
   across unrelated projects and hides provenance behind host-local state.
2. Always use in-memory SSURGO caches for project builds - Rejected. Every
   rebuild would refetch from NRCS, increasing upstream load and reducing
   same-project reproducibility when NRCS changes.
3. Pin all projects to bundled SSURGO/STATSGO seed databases - Rejected. This is
   deterministic but can be stale relative to current NRCS and does not scale to
   all project-specific fetched rows without a separate data-vintage program.
4. Project-local caches plus an operator clear control and provenance sidecars -
   Accepted. It bounds cache reuse to the run, makes refresh intentional, and
   exposes enough provenance for audit.

## Consequences

- Positive:
  - Stale host-global cache rows no longer cross project boundaries.
  - Same-project rebuilds reuse the same cached SSURGO rows unless the cache is
    explicitly cleared.
  - Old projects gracefully add cache artifacts on rebuild.
  - Operators can force a fresh NRCS fetch when stale project cache data is
    suspected.
  - Metadata sidecars make each file-backed cache visible as a run artifact with
    source provenance.
- Risks:
  - Results are not globally deterministic across projects or across explicit
    cache clears because NRCS can change upstream rows.
  - A user may clear the cache without realizing it can change generated WEPP
    soil inputs.
  - The metadata sidecar records runtime/source provenance and row counts, but
    does not yet record a full content digest or NRCS source vintage.
- Required operator framing:
  - Treat `Clear SSURGO cache on rebuild` as a parameterization-affecting action.
  - Preserve project cache files with run artifacts when reproducibility matters.

## Evidence

- Work package:
  `docs/work-packages/20260619_ssurgo_project_sqlite_cache/package.md`
- Active implementation plan and outcomes:
  `docs/work-packages/20260619_ssurgo_project_sqlite_cache/prompts/active/ssurgo_project_sqlite_cache_execplan.md`
- Tracker and decision log:
  `docs/work-packages/20260619_ssurgo_project_sqlite_cache/tracker.md`
- Security review:
  `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/security_review.md`
- Code review disposition:
  `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/code_review_findings.md`
- QA review disposition:
  `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/qa_review_findings.md`
- Roger Lew validation evidence:
  2026-06-19 Roger Lew report that both a new project and an old project tested
  successfully after the project-local cache implementation.

## Risk and Rollback Notes

Monitor for:

- unexpected differences in generated `.sol` files after cache clearing,
- operator confusion around the cache-clear checkbox,
- missing or stale `<cache>.meta.md` sidecars,
- project cache files being omitted from run archival workflows.

Rollback options:

1. Disable project cache persistence by passing no `cache_db_path` from `Soils`
   so project builds use in-memory SSURGO caches. This removes project snapshot
   reuse and increases NRCS refetching.
2. Revert to shared module-level cache behavior. This is not preferred because
   it reintroduces cross-project stale-cache risk.
3. Follow-on hardening can add content digests, source-vintage capture, or
   stronger UI warning text without reverting the cache architecture.

## Implementation Notes

- Production implementation:
  - `wepppy/soils/ssurgo/ssurgo.py`
  - `wepppy/nodb/core/soils.py`
  - `wepppy/microservices/rq_engine/soils_routes.py`
  - `wepppy/weppcloud/templates/controls/soil_pure.htm`
- Regression coverage:
  - `tests/soils/test_ssurgo_cache.py`
  - `tests/nodb/test_soils_ssurgo_cache.py`
  - `tests/nodb/test_soils_gridded_root_creation.py`
  - `tests/microservices/test_rq_engine_soils_routes.py`
  - `tests/microservices/test_rq_engine_schema_defaults_routes.py`
  - `tests/weppcloud/routes/test_pure_controls_render.py`
- Documentation:
  - `wepppy/soils/README.md`
  - `wepppy/soils/ssurgo/ssurgo.md`
