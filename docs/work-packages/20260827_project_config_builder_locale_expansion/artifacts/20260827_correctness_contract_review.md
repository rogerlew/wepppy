# WP12C Independent Correctness Contract Review

**Reviewer**: Singer (`contract_correctness_review`)
**Date**: 2026-08-27
**Initiative / canonical branch**: `feature/project-owned-config` / `master`
**Promotion policy**: WP12C may push the initiative branch and deploy only to
host `forest`; WP12 owns canonical merge and production
**Checkpoint**: `bb1745fd8`
**Disposition**: Ready; no unresolved blocking contract findings

## First Review Findings

The first review blocked on incomplete schema-v2 relations, an overbroad
Multiple OFE statement, missing exact runtime writes, ambiguous historical graph
compatibility, legacy-client exposure, and stale climate build-ordering prose.

## Disposition

ADR-0047 now records exact axes, numeric modes, method adjacency/defaults,
locale/map/unit and provider writes, cell sizes, soil/landuse dispatch behavior,
and the single `wbt|multiple-ofe|wepp_260803` tuple. The canonical contract now
defines append-only frozen structural contracts and separate locale-keyed
components/graphs while keeping both singular compatibility members US-only.
The RQ API contract now describes atomic stable/numeric climate method fields.

The first-review findings are closed.

## Second Review Findings and Disposition

The second review found that old-client creation was impossible under the first
compatibility wording, the normative US v3 example omitted Daymet relations,
historical-v2 update behavior was unspecified, the exact source boundary omitted
snapshot/update modules, v3 and reader-first gates were incomplete, and the RQ
contract named `climate_catalog_id` only for v2.

The amended contract now versions Builder description and requests, retains the
frozen US v2 members only for parsing, and fails old creation with
`unsupported_builder_schema` before mutation. The US v3 example contains all
four climate datasets and complete Daymet adjacency/defaults. Frozen v2 update
behavior, `snapshot.py`, `project_config_update.py`, v3 hostile/rollback gates,
and v2/v3 climate catalog requirements are now explicit.

Final independent re-review found no remaining blocking correctness findings.
Implementation and release remain gated on the contracted direct tests and
`forest` acceptance evidence.
