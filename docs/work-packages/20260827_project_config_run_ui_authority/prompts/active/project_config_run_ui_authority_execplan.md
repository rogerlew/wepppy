# Make effective config locale authoritative for run controls

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.

## Purpose / Big Picture

After WP12D, an established Interface carries its locale in its effective
`.cfg`, not in its link. Opening an old run without a flattened project config
uses that locale to show the same bounded landuse, soil, and climate choices as
the current Builder profile. A Builder-created run remains frozen to its stored
graph. An eligible complete schema-v3 project may adopt the current same-locale
graph only when an authorized end user reviews and acknowledges an explicit
capability refresh. Schema-v2 refresh is unavailable. No run is silently
migrated.

## Progress

- [x] (2026-08-27 20:31Z) Inventory the run-control presentation and paired
  mutation/build surfaces.
- [x] (2026-08-27 20:31Z) Draft the original link-query proposal and obtain
  advisory reviews.
- [x] (2026-08-27 21:18Z) Confirm Builder configs already store locale, inspect
  legacy config resolution, and inventory 128 named configs/71 omissions.
- [x] (2026-08-27 21:24Z) Supersede the unratified link-query proposal with
  `.cfg`-owned amendment `PC-24/WP12D-20260827-2`.
- [x] (2026-08-27 21:28Z) Replace the summary inventory with all 128 rows and
  close Turkey, project-local/query, no-capability, scoped-runtime, RQ
  discovery, error-transport, and rollback findings.
- [x] (2026-08-27 21:35Z) Obtain Ready advisory correctness and governance
  reviews of amendment 2.
- [x] (2026-08-27 22:01Z) Supersede amendment 2 with the operator-directed
  explicit capability-refresh design in amendment 3.
- [x] (2026-08-27 22:23Z) Obtain Ready advisory correctness and governance
  reviews of the corrected amendment 3.
- [x] (2026-08-27 22:23Z) Obtain exact operator ratification of amendment 3.
- [x] (2026-08-28 00:14Z) Amend canonical contracts/ADR and obtain binding
  correctness, governance, and security READY reviews with no unresolved High
  or Medium findings; correctness and security also reported no Low findings.
- [ ] Commit the standalone checkpoint.
- [ ] Write failing inventory, legacy reopen, stored isolation, and paired
  boundary tests.
- [ ] Implement exact config normalization and authority composition.
- [ ] Pass focused/full gates and independent correctness/security reviews.
- [ ] Push and validate exact candidate on `forest`; hand it to WP12 without
  production deployment.

## Surprises & Discoveries

- Observation: Builder locale selection already writes
  `[general] locales = [runtime_token]` into the flattened config.
  Evidence: `wepppy/nodb/config_builder/registry.py` in
  `_synthesized_builder_components`.
- Observation: 71 of 128 named configs omit a literal locale, and shared
  `_defaults.cfg` currently has no locale default.
  Evidence: complete `wepppy/nodb/configs/*.cfg` inventory on 2026-08-27.
- Observation: current established US omissions include `0`, `13`, `baer`, and
  all three Revegetation configs; all specialized displayed presets already
  declare locale.
  Evidence: `interfaces.htm` form inventory and named config reads.
- Observation: Canada configs still say `earth`; five Portland configs and
  `rhem_rap.cfg` omit their specialized locale; Tenerife uses overlay-first
  order.
  Evidence: exact config list in the contract decision.
- Observation: persisted `Ron._locales` currently takes precedence in
  `NoDbBase.locales`, so editing shared configs alone cannot prove correct old-
  run reopening.
  Evidence: `wepppy/nodb/base.py` `locales` property.
- Observation: `yasin.cfg` is Turkey-specific despite omitting locale, while
  `general.cfg` has stale Seattle display metadata but Continental-US config
  semantics.
  Evidence: exact config values and row-level inventory.
- Observation: run endpoint documents, pipeline, and readiness currently read
  stored authority directly and would diverge from live legacy enforcement.
  Evidence: `schema_defaults_routes.py` and `orchestration_read_routes.py`.
- Observation: historical flattened schema-v1/no-capability snapshots can omit
  or carry old locale state that shared defaults cannot reach.
  Evidence: canonical capability compatibility rules and flattened snapshot
  loading.
- Observation: the existing amendment transaction adds only missing registered
  attributes and explicitly preserves every stored capability axis.
  Evidence: project-config contract section 5.1 and
  `project_config_update.py` stored-graph resolution.

## Decision Log

- Decision: Locale belongs to effective config, not Interfaces navigation or
  feature-registry metadata.
  Rationale: executable configuration must have one durable source.
  Date/Author: 2026-08-27, operator/Codex.
- Decision: Use the live Builder graph only for legacy runs whose config is one
  exact Builder-exposed base profile.
  Rationale: these runs lack a frozen graph; specialized/overlay profiles do
  not have complete Builder graphs and must retain current catalogs.
  Date/Author: 2026-08-27, Codex.
- Decision: Keep the stored graph reader stored-only and add a clearly named
  composition layer.
  Rationale: this preserves the accepted WP12C reader boundary and makes
  registry drift semantics explicit.
  Date/Author: 2026-08-27, Codex.
- Decision: Add US to shared defaults plus exact specialized overrides rather
  than mechanically editing all 71 omissions.
  Rationale: this preserves the historical US baseline while keeping every
  effective config nonempty and specialized identities explicit.
  Date/Author: 2026-08-27, Codex.
- Decision: Leave global `NoDbBase.locales` unchanged and update only the exact
  landuse, soil, and climate consumers plus run UI/RQ boundaries.
  Rationale: this bounds runtime effects and keeps discovery, validation, and
  provider dispatch aligned in the requested domains.
  Date/Author: 2026-08-27, Codex.
- Decision: Classify flattened projects before the new non-flattened legacy
  locale path. No-capability/schema-v1 projects receive no new locale
  validation and never consult the live Builder registry.
  Rationale: preserve the versioned compatibility of historical snapshots and
  every present valid v1 axis.
  Date/Author: 2026-08-27, Codex.
- Decision: Add Turkey as a classification-only supported-non-Builder base
  with source revision `WP12D-1` and empty closed dataset axes.
  Rationale: Yasin's fixed maps are config-owned inputs outside Builder
  dataset authorization, so inventing stable dataset IDs would broaden scope.
  Date/Author: 2026-08-27, Codex.
- Decision: Stored capability authority remains frozen by default but may be
  explicitly replaced with the current same-locale graph after complete
  preview and an exact end-user acknowledgment.
  Rationale: old projects must be reusable with new maps and capabilities, but
  the UI and manifest must disclose and record the resulting provenance
  discontinuity and unstable-feature risk.
  Date/Author: 2026-08-27, operator/Codex.
- Decision: Refresh updates the capability envelope but preserves project
  `capability_defaults`, `nodb.mods`, and `climate.cligen_db`; an incompatible
  preserved selection makes refresh unavailable.
  Rationale: capability adoption cannot silently reset Daymet to Vanilla or
  substitute any other current Builder default for the user's project state.
  Date/Author: 2026-08-27, Codex.
- Decision: Authorize schema-v3 structures by append-only deterministic hashes,
  require exact Builder manifest/config congruence, and deploy a WP12D reader
  floor without the refresh writer before refresh exposure.
  Rationale: old graphs must survive future map additions, and rollback code
  must understand every structure a writer can persist.
  Date/Author: 2026-08-27, Codex.

## Outcomes & Retrospective

Amendment 3 is ratified and its canonical diff has passed binding correctness,
governance, and security review. Config and implementation changes remain
blocked only until that exact documentation-only diff is committed as the
standalone checkpoint.

## Context and Orientation

`wepppy/nodb/base.py` loads shared defaults followed by a named or project-local
config for legacy runs. `Ron` initially copies `[general] locales` into
persisted state, and other controllers expose locale through
`NoDbBase.locales`. Builder-created projects instead contain a flattened
project-owned config with a complete schema-v2/v3 capability graph.

`wepppy/nodb/project_config_capabilities.py` is the accepted stored-authority
reader. `wepppy/nodb/config_builder/resolver.py` creates the same per-locale
graphs used by Builder description and creation. WP12D must compose these at a
new run-authority boundary without changing stored-reader semantics.

`wepppy/nodb/project_config_update.py` currently resolves missing attributes
under the project amendment lock but passes stored capability authority back to
Builder resolution. WP12D extends that transaction with an explicit graph-
replacement update class. The prior graph stays authoritative until the config
replacement commit point; after that point crash recovery deterministically
rolls the complete result pair forward before reload.

The run page builds landuse, soil, and climate context in
`wepppy/weppcloud/routes/run_0/run_0_bp.py`. Flask climate/soil setters live in
`wepppy/weppcloud/routes/nodb_api/`; rq-engine build/set routes live in
`wepppy/microservices/rq_engine/`. Presentation and submission must resolve the
same authority.

The Config Builder's own validated create payload necessarily carries its
selected Builder locale ID and its existing provenance snapshot may record the
selection. The navigation non-change applies to established-Interface links
and config-token forms; the durable runtime locale written by Builder is
`[general] locales` in the flattened config.

## Plan of Work

First ratify amendment 3. Amend the exact canonical sections and ADR named in
the decision artifact, obtain independent correctness, governance, and
dedicated security reviews of that diff, resolve all High/Medium findings in
their artifacts, and commit only governance/package documents as a standalone
ancestor checkpoint.

Then write the failing historical/current/unknown structure tests, implement,
and review the append-only schema-v3 structural reader as a separate reader-
floor commit with the capability-refresh writer absent and existing additive
behavior unchanged.
Deploy that exact reader floor to `forest` and prove it opens both the real
current production identities and stored schema-v3 fixtures before implementing
or exposing refresh writing. Prove `280cf7e84` and current share an identity,
and use a test-only distinct structural pair for evolution mechanics. Record
the reader floor's exact revision as the minimum rollback floor for the writer
candidate.

Next add failing evidence. Parse every named config after defaults; build
legacy-style run fixtures for all five exposed bases and for no-capability
flattened, non-Builder, overlay, Turkey, RHEM, schema-v1, schema-v2, and
schema-v3 modes; include stale persisted locale and both project-local defaults
filenames. For flattened no-capability/schema-v1, cover absent, empty, unknown,
and valid locale and preserve present v1 axes without consulting the live
registry. Assert Turkey's exact serialized profile/catalog revision and Yasin
fixed-map behavior. Prove links remain plain, locale overrides fail before
publication, RQ discovery matches mutation, and direct unsupported submissions
do not mutate or enqueue.

Add failing capability-refresh evidence around the existing update flow. Prove
one locale-to-graph hotpath serves Builder creation, legacy live authority,
preview, and apply. Cover additive-only, capability-only, combined, invalid,
stale, missing-acknowledgment, crash-recovery, exact-current, preserved-
selection, and removed/incompatible-selection states before implementation.

Then add the public Builder locale-graph reader and the stored-or-legacy run
resolver. Normalize only the exact config files listed in the ratified
decision, including Turkey's canonical supported-non-Builder identity. Update
only the enumerated landuse/soil/climate core consumers, run context, paired
routes, and RQ discovery to use the resolved authority. Leave global
`NoDbBase.locales` unchanged. Preserve exact-current recovery and explicit
409/503 diagnostics. Extend the project-config update modal/API/job/transaction
to preview the complete graph delta, require the exact acknowledgment, replace
the capability envelope atomically around unchanged project selections, and
append a reversible provenance-discontinuity record. Refuse refresh rather
than substituting current Builder defaults for incompatible selections.

Finally run focused and broad gates, complete independent correctness/security
reviews, compare every changed path with the ratified list, push, and validate
the exact revision on exact host `forest` without rebuilding an image. WP12
retains every merge-to-master and production action.

## Milestones

Milestone 1 produces a standalone contract checkpoint. Acceptance requires the
ratified canonical diff, Ready independent correctness/governance/security
reviews, ADR-0047 amendment, and a commit containing no `.cfg` or
implementation edits. The implementation candidate requires a fresh dedicated
security review rather than reusing checkpoint approval.

Milestone 2 produces the structural reader floor without a refresh writer.
Acceptance requires append-only authorization for current production schema-v3
structures, proof that `280cf7e84` shares the current identity, a test-only
genuine two-identity evolution case, rejection of unknown structures, stored
selection preservation, independent review, and exact-host Forest reopen
evidence before refresh writing exists.

Milestone 3 produces failing evidence and the bounded writer implementation.
Acceptance requires the 128-row inventory to validate, five legacy profile
matrices and RQ discovery to match Builder, stored graphs to ignore live
changes, eligible complete schema-v3 projects to adopt the exact current graph
only through acknowledged refresh, schema-v2 refresh to remain unavailable,
project-local/query compatibility to pass, and every paired
submission/build/update test to pass.

Milestone 4 produces integration evidence. Acceptance requires broad local
gates, Ready correctness/security reviews, exact changed-file scope, a pushed
candidate, and exact-host Forest reopen/build evidence with no production
action. Forest evidence must include an acknowledged schema-v3 refresh and
reopen, followed by rollback to the recorded WP12D reader floor proving the
refreshed config and manifest remain readable and byte-for-byte unchanged.

## Concrete Steps

Work from `/home/workdir/wepppy`.

Initiative branch: feature/project-owned-config
Canonical branch: master
Promotion policy: merge only at the roadmap promotion gate

Starting/upstream revision is
`5e04e0da9a23dd676e171f1857e14fa38cc9dfbe`; canonical merge base is
`6af9ecdd63921189804c5e292114a97253914cbb`. Verify the standalone checkpoint is
an ancestor before editing config or implementation files.

Iterate with:

    wctl run-pytest tests/nodb/test_locale_capability_authority.py tests/nodb/test_project_config_reader_unit.py tests/nodb/test_project_config_preset_snapshot.py tests/nodb/test_project_config_update.py tests/nodb/test_defaults_cfg_compatibility.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_climate_bp.py tests/weppcloud/routes/test_soils_bp.py tests/microservices/test_rq_engine_project_routes.py tests/microservices/test_rq_engine_project_config_update_routes.py tests/microservices/test_rq_engine_landuse_routes.py tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_soils_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py tests/microservices/test_rq_engine_orchestration_read_routes.py tests/rq/test_project_config_update_rq.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test

Before handoff, run the full Python suite, affected stubs, broad-exception
enforcement, vulture, `git diff --check`, scoped documentation lint, and exact
Forest checks. Record counts and revisions in the tracker.

The exact preexisting dirty paths excluded from every WP12D stage are:

- `docker/validate-cap-runtime-contract.sh`;
- `docs/infrastructure/incident-2026-08-25-production-compose-partial-build.md`;
- `docs/standards/hardening-lifecycle-standard.md`;
- `docs/ui-docs/cap-js-captcha-auth.md`;
- `docs/work-packages/20260823_session_cookie_namespace_migration/artifacts/rollout_runbook.md`;
- `docs/work-packages/20260823_session_cookie_namespace_migration/prompts/active/session_cookie_namespace_migration_execplan.md`;
- `docs/work-packages/20260823_session_cookie_namespace_migration/tracker.md`;
- `docs/work-packages/20260825_cap_runtime_deploy_hardening/package.md`;
- `docs/work-packages/20260825_cap_runtime_deploy_hardening/prompts/active/cap_runtime_deploy_hardening_execplan.md`;
- `docs/work-packages/20260825_cap_runtime_deploy_hardening/tracker.md`; and
- `services/cap/canary.js`.

## Validation and Acceptance

Opening each of the five named legacy base profiles must show exactly the live
Builder graph axes. Changing the live registry in a test must change only
legacy options and update availability; stored schema-v2/v3 options must remain
byte-for-byte stable. Only an eligible complete schema-v3 project may change
through acknowledged refresh; schema-v2 refresh remains unavailable.
An old run with stale persisted locale must resolve its effective `.cfg`
without modifying any file. Missing project-local locale must use the explicit
compatibility value, while an explicit local value remains authoritative.
No-capability flattened and schema-v1 fixtures must preserve existing behavior
for absent, empty, unknown, and valid locale without live-registry access;
present valid v1 axes remain restrictive. Non-Builder, overlay, Turkey, and
RHEM fixtures must preserve existing behavior. RQ schemas/defaults/errors,
operation documents, pipeline, and readiness must match paired mutation
authority.

Capability preview must expose a complete reversible delta, canonical support
state where defined, and the preserved project selections. Apply must remain disabled until
the exact warning is acknowledged; the API must enforce the same revision.
Successful apply atomically replaces the envelope, keeps every project
selection canonical value unchanged, and records the discontinuity without
personal identity. A removed or incompatible selection makes preview
unavailable with diagnostic stable IDs. Failed, stale, unacknowledged, or
incompatible requests rejected before reservation preserve the prior graph and
leave no queue or file side effect. Once enqueued, the job remains observable;
fault recovery preserves the prior pair before config replacement and rolls the
result pair forward after it, with terminal UI/job state reporting the recovered
outcome.
Historical amendments infer additive/null-preview reconciliation fields. Only
the latest matching non-null preview ID is idempotent; exact HTTP/RQ recovered
results must not enqueue or append a duplicate amendment.

Both Config Builder links must remain `/interfaces/`, and the Interfaces page
must remain unfiltered. A different unsupported selection must fail before
mutation or enqueue, while an unchanged exact-current build succeeds.

## Idempotence and Recovery

Config parsing, availability, and preview are read-only. Reapplying the same
normalization is stable. Only an explicit acknowledged apply rewrites a
project-owned graph; no test or deploy silently rewrites user runs. Forest service
recreation uses the existing source-mounted development stack with `--no-build
--no-deps --force-recreate`. Rollback restores an exact recorded code/config
revision; it never deletes projects.

## Artifacts and Notes

Keep contract reviews, the full config-locale inventory, correctness/security
reviews, validation transcripts, Forest evidence, and scope comparison under
this package. Do not record credentials, tokens, personal identity, or
production run IDs.

## Interfaces and Dependencies

No external dependency is added. Preserve project-config reader, NoDb locking,
RQ response, CSRF/auth, queue, and route contracts. Public Builder/run-authority
helpers require matching stubs. The existing update enqueue signature and its
catalog evidence may change, so `wepppy/rq/job-dependencies-catalog.md` and
`wepppy/rq/job-dependency-graph.static.json` are both in scope for synchronized
evidence. Queue topology and dependency edges remain excluded; discovering
another needed consumer stops work for amendment and re-ratification.

Plan revision note (2026-08-27): replaced the unratified link-query design with
the operator-corrected `.cfg` locale authority, exact normalization inventory,
live-legacy/frozen-stored graph split, no-migration reopen behavior, and ADR
gate.

Plan revision note (2026-08-27): fresh amendment-2 advisory findings produced a
closed 128-row inventory, explicit Turkey and project-local/query rules,
no-capability/source-kind coverage, scoped core consumers, RQ agent-contract
parity, exact error transports, and corrected atomic rollback semantics.

Plan revision note (2026-08-27): amendment 3 keeps stored authority frozen by
default and adds a same-locale, previewed, explicitly acknowledged capability
refresh through the existing atomic amendment flow. The manifest records the
provenance discontinuity; silent migration remains prohibited.

Plan revision note (2026-08-27): governance disposition limits refresh to
eligible complete schema-v3 projects, names the generated RQ dependency graph,
and requires exact-host refresh/reopen plus reader-floor rollback evidence for
the new persistence shape.

Plan revision note (2026-08-27): correctness disposition defines refresh as a
selection-preserving envelope rebase. Current Builder defaults never overwrite
project defaults or selectors; removed/incompatible selections make refresh
unavailable with diagnostics.

Plan revision note (2026-08-27): final correctness disposition adds exact
delta/provenance encoding, append-only schema-v3 structure identities, Builder-
source locale/selection congruence, existing transaction commit semantics, and
a WP12D reader floor without the refresh writer for safe rollback.
