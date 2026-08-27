# Expose authoritative Europe, Canada, Australia, and Earth Builder profiles

This ExecPlan is a living document and must be maintained under
`docs/prompt_templates/codex_exec_plans.md`. The `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` sections must stay
current.

Work occurs only on `feature/project-owned-config`, starting from local/origin
revision `e1ef3b8df`. `master` at `6af9ecdd6` is canonical and is an ancestor of
the initiative branch. WP12C may push the initiative branch and deploy only to
host `forest`; WP12 exclusively owns merge to `master` and production promotion.

## Purpose / Big Picture

After this work, a power user can open Config Builder, choose Continental United
States, Europe, Canada, Australia, or Global Earth, and see only the terrain,
soil, land-cover, and climate data that apply to that locale. The server will
validate the same choices and store that locale's complete schema-v3 graph in
the new run, so reopening the run does not depend on a later registry version.

Canada is a Canada-wide profile, not the existing British Columbia preset. It
uses Copernicus DEM, ISRIC soil, C3S global land cover, offers Vanilla CLIGEN
and observed Daymet, defaults to Vanilla CLIGEN, and uses GHCN stations.

## Progress

- [x] (2026-08-27 15:40Z) Scoped the exact five-profile set and Canada policy.
- [x] (2026-08-27 18:03Z) Ratified canonical contract amendments; correctness
  security, and governance re-reviews are Ready with no blocking findings.
- [x] (2026-08-27 18:12Z) Committed the ratified standalone contract
  checkpoint as `bb1745fd8`; it is the ancestor of all WP12C implementation
  work.
- [x] (2026-08-27 18:39Z) Implemented typed profile climate/station sources,
  adapter-bound provider components, and instance-local CLIGEN catalogs.
- [x] (2026-08-27 18:39Z) Implemented and serialized validated schema-v3 graphs
  for all five exposed profiles while retaining the historical v2 reader.
- [x] (2026-08-27 18:39Z) Made Builder description, dependent controls,
  validation, and resolution
  select the graph for the chosen locale.
- [x] (2026-08-27 18:39Z) Focused Python and JavaScript tests prove historical
  and hostile stored-graph behavior, cross-locale rejection, and API/UI parity.
- [x] (2026-08-27 20:00Z) Closed two review-discovered compatibility defects:
  legacy/schema-v1 update synthesis and locale-dispatched provider ownership.
  Correctness and security independently marked exact candidate `b31eeb625`
  Ready with no unresolved High or Medium findings.
- [x] (2026-08-27 20:00Z) Passed the final complete Python gate (7,080 passed,
  63 skipped), frontend lint and all 107 suites / 794 tests, stubs, exception
  enforcement, diff checks, and dead-code checks.
- [x] (2026-08-27 20:05Z) Operator accepted the chronology-preserving
  checkpoint correction for the two omitted read/export consumers and required
  a scope-vs-changed-files gate in WP12.
- [x] (2026-08-27 20:10Z) Committed the audit correction as `f6784420a`;
  independent governance re-review marked the exact commit Ready with no
  remaining blockers.
- [x] (2026-08-27 20:15Z) Recreated only Forest `weppcloud` and `rq-engine`
  without building, forced the Builder writer off, passed 14 deployed-reader
  matrix tests, and proved the authenticated create boundary returns canonical
  writer-disabled `503`.
- [x] (2026-08-27 20:15Z) Recorded exact revision `187a856d4` as the minimum
  post-create rollback floor after all five v3 profiles and historical v2
  passed on the deployed reader.
- [ ] Enable the Builder writer on exact host `forest` and record authenticated
  create/reopen plus real provider/run evidence.
- [ ] Close the package, push, and hand the accepted revision to WP12.

## Surprises & Discoveries

- Observation: Australia has a real 2010-2011 land-cover provider and deployed
  Forest data, but the WP12B typed land-cover catalog currently records the
  Australia locale group as empty.
  Evidence: `wepppy/au/landuse_201011/__init__.py` and
  `/wc1/geodata/au/landuse_201011/lu10v5ua`.

- Observation: EOBS and AGDC are implemented climate providers but their
  current global support-state fields prevent Builder exposure.
  Evidence: `wepppy/nodb/locales/climate_catalog.py` entries `eobs_modified`
  and `agdc`.

- Observation: `CligenStationsManager` currently mutates process-global
  database and PAR-root variables. Concurrent Legacy/GHCN construction can pair
  rows from one database with paths under another root.
  Evidence: `wepppy/climates/cligen/cligen.py` assigns module globals in the
  manager constructor and `StationMeta` reads the global root later.

- Observation: the shipped GHCN `all_years` PAR entries may be symlinks into
  the 30-year catalog, so the concurrency test must compare the resolved
  instance root and selected file identity rather than assume every lexical
  path remains below `all_years` after canonicalization.
  Evidence: the direct SQLite/PAR test in
  `tests/climates/test_cligen_station_catalog_isolation.py`.

- Observation: the full suite retained a pre-WP12C assertion that Australia
  exposes no AGDC climate source even though the ratified matrix explicitly
  includes AGDC.
  Evidence: the first broad run stopped in
  `tests/nodb/test_climate_catalog.py`; the corrected contract assertion and
  complete rerun pass.

- Observation: the checkpoint's exact changed-consumer enumeration omitted
  `project_config_capabilities.py` and `locales/__init__.py`, although both were
  necessary implementation consumers.
  Evidence: `git diff --name-only bb1745fd8..280cf7e84` and
  `artifacts/20260827_checkpoint_scope_deviation.md`.

- Observation: final review found legacy/schema-v1 Builder update preview could
  consult the live registry and synthesize a modern graph, and a remediation
  had made ESDAC/ASRIS and Australian land cover claim runtime selector writes
  contrary to ADR-0047.
  Evidence: both paths are closed in `b31eeb625`, with no-write and exact
  component-ownership regressions.

## Decision Log

- Decision: Use capability schema version 3 for WP12C and retain the schema-v2
  reader unchanged.
  Rationale: Climate Station Database is a new mandatory stored axis/default.
  A new schema prevents historical v2 graphs from being misclassified as
  partial while keeping their bytes and behavior unchanged.
  Date/Author: 2026-08-27 / project operator and Codex.

- Decision: Builder description schema version 2 carries schema-v3
  `capability_graphs_by_locale` and retains the frozen historical v2 US graph
  only for response parsing. New validation/creation requires the description
  version; old creation fails explicitly.
  Rationale: An old client cannot express the mandatory station-database axis,
  so pretending it can create safely would silently invent state.
  Date/Author: 2026-08-27 / Codex.

- Decision: Dataset availability is owned by each `LocaleProfile`, including a
  new `climate_sources` axis and separate `climate_station_databases` axis.
  Rationale: Component-global exposure flags and UI allowlists cannot be a
  second source of truth.
  Date/Author: 2026-08-27 / project operator and Codex.

- Decision: Preserve checkpoint `bb1745fd8` and record its incomplete consumer
  enumeration in a standalone correction rather than rewriting history.
  Rationale: the omitted files are bounded read/export consumers, but an exact
  ratification must retain truthful chronology. WP12 will compare the complete
  changed-file set with the accepted boundary before promotion.
  Date/Author: 2026-08-27 / project operator and Codex.

## Outcomes & Retrospective

The implementation candidate is complete at `b31eeb625`, independently Ready,
and fully validated locally. No WP12C Forest restart or expanded-profile run has
occurred yet. The package remains open for the accepted audit correction,
governance confirmation, reader-first rollback-floor proof, and live Forest
provider/create/reopen evidence.

## Context and Orientation

WP12B introduced the canonical locale inventory in
`wepppy/nodb/locales/locale_profiles.py`, provider catalogs in
`climate_catalog.py` and `landuse_catalog.py`, and immutable schema-v2 graphs in
`capability_graph.py`. WP12C now builds closed schema-v3 graphs for five profiles,
stores the selected graph in each new run, and makes both the resolver and
frontend select the locale-keyed graph. Historical schema-v2 authority remains
frozen and schema-v1/legacy update preview fails before live registry loading.

A capability graph is the complete set of data/method choices and the adjacency
rules between them. A provider-backed component is a deterministic Builder
component synthesized from the typed domain catalog, not a hand-maintained
duplicate TOML allowlist.

## Plan of Work

First amend the current project-owned config contract, roadmap, and ADR, receive
two independent contract reviews, disposition findings, and commit those files
alone. Then extend `LocaleProfile` with climate IDs and make the five exposed
profiles complete. Add the missing Australia land-cover catalog identity.

Generalize capability graph construction and immutable validation around a
closed per-profile specification while leaving old Continental-US v2 graphs
valid. Add schema-v3 Climate Station Database authority. Generate the locale,
data, station-database, and capability components for exposed profiles from
typed authorities, preserving dynamic WEPP provider identity.
Make resolver selection and config writes use the chosen profile graph.

Extend the Builder description with a locale-keyed graph mapping, update the
browser controller to select that graph before rendering dependent choices,
and validate the same graph on submission. Add focused Python and JavaScript
tests for every profile, bad cross-profile selections, malformed graphs,
historical v2 bytes and update semantics, description-version negotiation, and
defaults. Refactor the CLIGEN resolver so database/PAR-root selection is
instance-local and prove real concurrent Legacy/2015/GHCN isolation.

Finally run canonical gates, obtain correctness/governance/security review,
restart the development stack on exact host `forest` without image rebuild, and
prove provider availability plus create/reopen behavior for Europe, Canada,
Australia, and Earth. WP12C does not deploy production.

## Milestones

Milestone 1 is the standalone contract checkpoint. Amend only current canonical
contracts, ADR, roadmap, package governance, and review artifacts; receive and
disposition two independent contract reviews plus the security contract review;
run Markdown and diff gates; and commit those documentation files without any
implementation file. The checkpoint commit must be an ancestor of every WP12C
implementation commit.

Milestone 2 is typed backend authority. Add the complete profile dataset lists,
provider identities, generated components, immutable graph contracts, and
locale-selecting resolver. Make CLIGEN station database/PAR-root selection
instance-local. Focused Python tests must demonstrate all five profiles,
unchanged historical Continental-US v2 behavior, and real concurrent station
resolver isolation.

Milestone 3 is API and user interface parity. Add the locale-keyed graph mapping
to the Builder response and make all dependent controls select it. Route and
frontend tests must demonstrate valid transitions and cross-locale rejection
without mutation.

Milestone 4 is release evidence. Pass broad local gates and independent
implementation/security reviews. On exact host `forest`, first deploy the
candidate reader with creation disabled and prove all five stored graph
fixtures; record that revision as the rollback floor. Then enable the existing
development Builder flag and create/reopen one run per new profile with real
provider execution. Close and push WP12C only after all evidence is accepted.

## Concrete Steps

Run from `/home/workdir/wepppy`:

    wctl run-pytest tests/nodb/test_locale_capability_authority.py
    wctl run-pytest tests/nodb/test_project_config_builder_snapshot.py
    wctl run-pytest tests/climates/test_cligen_station_catalog_isolation.py
    wctl run-pytest tests/microservices/test_rq_engine_builder_routes.py
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1

Use `wctl doc-lint --path` for every changed Markdown document. Record exact
test counts and Forest commands/results in package artifacts as they occur.

## Validation and Acceptance

Description must advertise exactly five Builder locale IDs and a complete graph
for each. Choosing a locale must immediately constrain every data axis. Each
valid profile resolves deterministic config bytes whose runtime locale and data
provider values match the matrix. Every cross-locale choice must return a
field-addressable 4xx response without creating or mutating a run.

On host `forest`, provider probes and representative real execution must pass for
every advertised dataset/provider family. One run for each newly exposed
profile must be created, reopened, and shown to use its stored graph. Canada
must show runtime locale `canada`, global data providers, Vanilla CLIGEN plus
Daymet, a Vanilla CLIGEN default, and the GHCN station database. Continental-US
acceptance must exercise Legacy, 2015, and GHCN station database resolution.

## Idempotence and Recovery

Registry loading, description, validation, and tests are read-only and
repeatable. Deployment to `forest` restarts existing development services without an
image build. A failed create must leave no ready run. Before any expanded-profile
run exists, the implementation commit may be reverted. Afterwards rollback must
retain the multi-profile schema-v3 reader and historical schema-v2 reader; no
run bytes are rewritten.

## Artifacts and Notes

The contract decision and locale matrix live in this package's `artifacts/`
directory. Review and Forest acceptance artifacts will be filled with
revision-bound evidence.

## Interfaces and Dependencies

`LocaleProfile` gains `climate_sources: tuple[str, ...]` and
`climate_station_databases: tuple[str, ...]`. `BuilderSelections` gains a
`climate_station_database` stable ID and the component kind gains a distinct
climate-station database value. The Builder
description schema version 2 gains a `capability_graphs_by_locale` mapping while
retaining the frozen Continental-US schema-v2 `capability_graph` for parsing,
and gains `components_by_locale` while retaining its matching historical
`components` population. Validation and creation require the description
version. Graph construction accepts one stable profile ID and the runtime
WEPP provider inventory. Stored validation accepts historical schema v2 and
uses immutable schema-v3 profile contracts for new projects, never current
provider catalogs.

Revision note: initial plan created 2026-08-27 to preserve the user's final
Canada-inclusive scope and sequence a contract checkpoint before implementation.

Revision note: amended 2026-08-27 to make Vanilla CLIGEN the explicit default
for every locale, define Builder description negotiation, freeze schema-v2
update behavior, and require instance-local CLIGEN station resolution after
independent review findings.
