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
- [x] (2026-08-28 00:16Z) Commit the standalone documentation-only checkpoint
  as `596ff5758ca83e6077b97f953431c2c881219840`.
- [x] (2026-08-28 00:35Z) Implement and locally validate the append-only
  structural reader floor while keeping the capability-refresh writer absent.
- [x] (2026-08-28 00:41Z) Obtain Ready reader-floor correctness/security
  reviews, commit and push exact revision `80f4810b7`, and validate real
  schema-v2/v3 reopen on `forest` without rebuilding or exposing a refresh
  writer.
- [x] (2026-08-28 01:28Z) Write and pass inventory, legacy reopen, stored
  isolation, paired-boundary, additive/capability/combined refresh,
  acknowledgment, atomicity, recovery, and accessibility tests.
- [x] (2026-08-28 01:28Z) Implement exact config normalization, public Builder
  graph hotpath, stored-or-legacy authority composition, scoped consumers, and
  the acknowledged selection-preserving schema-v3 refresh transaction/UI.
- [x] (2026-08-28 02:05Z) Pass the complete Python gate with 7,110 tests
  passed and 63 skipped, plus focused frontend, lint, stub, exception, Vulture,
  diff, documentation, and RQ-graph gates.
- [x] (2026-08-28 02:45Z) Final correctness review confirmed live legacy
  authority must remain scoped to landuse, soil, and climate; keep legacy WEPP
  presentation/submission compatibility without expanding the source boundary.
- [x] (2026-08-28 03:33Z) Close the final review findings with complete
  selection-bearing refresh validation, strict durable amendment/recovery
  validation, native landuse/soil pre-mutation enforcement, diagnostic UI
  transport, exact OpenAPI models, and route-bound application revision.
- [x] (2026-08-28 03:33Z) Pass a clean complete Python gate with 7,147 tests
  passed and 63 skipped, the complete 801-test frontend suite, and the final
  lint, stub, exception, Vulture, diff, documentation, and RQ-graph gates.
- [x] (2026-08-28 05:32Z) Resolve all final correctness/security findings and
  obtain independent READY implementation reviews with no remaining in-scope
  High, Medium, or Low findings.
- [x] (2026-08-28 05:40Z) Bind terminal and immediate-recovered success to an
  immutable apply-time preview digest pair, and persist the climate catalog /
  mode relation under one NoDb lock with locked-snapshot concurrency and
  fault-rollback evidence.
- [x] (2026-08-28 05:32Z) Pass the final complete Python gate with 7,218 tests
  passed and 63 skipped, the complete 808-test frontend suite, and lint, stub,
  exception, Vulture, diff, documentation, and RQ-graph gates.
- [x] (2026-08-28 05:48Z) Commit and push the reviewed implementation as
  `d000b0cc4`, deploy that exact revision to `forest` without rebuilding the
  unchanged image, and complete an authenticated real-run refresh preview.
- [x] (2026-08-28 06:05Z) Diagnose the first acknowledged Forest apply before
  mutation as a fresh-worker circular import, preserve byte-identical run
  config/manifest state, and close it with lazy authorization import plus an
  atomic Redis compare-delete for single-flight release.
- [x] (2026-08-28 06:05Z) Pass 20 focused worker/route tests, fresh-process task
  resolution, live Forest Redis replacement-reservation evidence, and renewed
  independent correctness/security reviews with High 0, Medium 0, and Low 0.
- [x] (2026-08-28 06:13Z) Pass the exact hotfix complete Python gate with
  7,220 tests passed and 63 skipped, plus the refreshed stub, exception,
  Vulture, diff, documentation, and RQ-graph gates.
- [x] (2026-08-28 06:23Z) Deploy pushed hotfix `326f2138c` to exact host
  `forest` without rebuilding, prove the worker task now enters fail-closed
  authorization, and identify the browser-token actor sanitizer dropping its
  existing signed numeric `user_id` when `sub` is intentionally opaque.
- [x] (2026-08-28 06:25Z) Make sanitized user actors prefer the signed
  `user_id` claim with the established numeric-`sub` fallback and pass 116
  focused auth/token/route/worker tests; the failed apply again left config and
  manifest byte-identical and released its reservation.
- [x] (2026-08-28 06:45Z) Pass the exact identity-handoff complete Python gate
  with 7,221 tests passed and 63 skipped. A first attempt hit the previously
  documented unrelated same-size Climate fixture timing miss; that exact test
  passed immediately in isolation and in the clean complete rerun.
- [x] (2026-08-28 06:49Z) Deploy pushed identity revision `924813874` to
  `forest` without rebuilding and complete the authenticated acknowledged
  refresh: job `b591cd8b-18b4-4005-ae2e-8edec2d7f594` finished with the exact
  reviewed digest transition `92ed9605…0948` to `f41b0672…d7ca`.
- [x] (2026-08-28 06:55Z) Diagnose recurring post-apply manifest-only
  availability as comparison against immutable creation-chain revisions; use
  the newest validated capability amendment's resulting selected chain as the
  current baseline, retain creation-chain fallback, and pass 177 affected
  tests including settled post-apply unavailability.
- [x] (2026-08-28 07:02Z) Pass the final exact complete Python gate with
  7,221 tests passed and 63 skipped, plus an independently rerun combined
  post-apply settlement test and refreshed static/documentation gates.
- [x] (2026-08-28 07:08Z) Push and validate exact candidate `588608f1a` on
  `forest`, complete authenticated acknowledged apply and settled availability,
  roll back to reader floor `80f4810b7` without changing refreshed run bytes,
  and restore the candidate without production deployment.
- [x] (2026-08-28 09:54Z) Ratify audit-only amendment
  `PC-24/WP12D-20260828-4`, record the exact scope-vs-changed-files comparison,
  and carry the technically accepted candidate into the authoritative WP12
  roadmap gate without production deployment.
- [x] (2026-08-28) Reproduce the incomplete climate audit against
  `closing-plump/eu-disturbed`: its valid flattened schema-v1 preset carries a
  ten-mode coarse climate list that incorrectly broadens Europe.
- [x] (2026-08-28) Draft amendment `PC-24/WP12D-20260828-5` with the corrected
  five-locale climate matrix, complete locale land-cover envelopes, and bounded
  schema-v1 named-preset climate/land-cover projection.
- [x] (2026-08-28 10:45Z) Close advisory correctness/governance/security
  findings and record independent READY verdicts with no remaining High,
  Medium, or Low security findings and no remaining High/Medium contract
  findings.
- [x] (2026-08-28 16:29Z) Obtain exact operator ratification of amendment 5,
  preserving all commits/identities and reserving merge/production to WP12.
- [x] (2026-08-28 16:35Z) Obtain fresh binding correctness, governance, and
  security READY reviews with security High 0 / Medium 0 / Low 0.
- [x] (2026-08-28 16:36Z) Commit amendment 5's standalone canonical checkpoint
  as `baea9616df255d336807d0a91adf7be8f99367fe` and verify it is the ancestor
  before implementation.
- [x] (2026-08-28 17:03Z) Append and independently review the five exact
  amendment-5 identities, commit reader floor `d68d94816`, record its first-
  reader provenance in `83165fd1b`, and deploy that exact source revision to
  `forest` without rebuilding.
- [x] (2026-08-28 17:03Z) Reopen real historical schema-v2 and prior schema-v3
  runs, prove all five live Builder writers still emit their prior identities,
  and pass the 74-test reader suite on `forest`.
- [x] (2026-08-28 18:16Z) Implement the amendment-5 graph writers, strict
  schema-v1 named-preset climate/land-cover projection, and paired
  presentation/mutation authority.
- [x] (2026-08-28 18:16Z) Pass 584 focused and 7,269 complete Python tests
  with 63 skipped, 808 frontend tests, lint, stub, exception, Vulture, diff,
  and documentation gates; obtain independent correctness and security READY
  implementation reviews with no High, Medium, or Low findings.
- [ ] Commit and push the standalone amendment-5 writer checkpoint, then
  complete exact-host `forest` candidate/rollback acceptance.

## Surprises & Discoveries

- Observation: projecting only climate and landuse still leaked current soil,
  model, DEM, and locale defaults when the projected graph was composed into
  schema and orchestration documents; the consumers must filter both domains
  and defaults at the projection boundary.
  Evidence: schema/orchestration regression tests over materialized schema-v1
  named presets on 2026-08-28.
- Observation: preserving raw schema-v1 soil authority requires resolving the
  stored soil branch before any live registry lookup; otherwise a climate/
  landuse-only projection can make an unrelated soil read depend on the live
  registry.
  Evidence: zero-registry-access soil regression on 2026-08-28.
- Observation: the manifest and flattened config must each be read as one
  byte observation and carry the loaded digest through projection. Re-reading
  either file during one resolution admits a time-of-check/time-of-use split.
  Evidence: manifest/config mutation-between-read regressions on 2026-08-28.
- Observation: the amendment-5 reader floor can coexist with the already
  implemented acknowledged capability-refresh mechanism because all five live
  locale graph writers remain on their prior identities until the later writer
  commit.
  Evidence: exact-host `forest` resolver readback under `83165fd1b` on
  2026-08-28 17:03 UTC.

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
- Observation: `closing-plump/eu-disturbed` is a valid flattened schema-v1
  named preset whose stored coarse climate axis contains ten modes, including
  modes outside Europe; the existing compatibility rule therefore renders the
  broad list exactly as stored.
  Evidence: `/wc1/runs/cl/closing-plump/eu-disturbed.cfg`, its manifest, and
  `climate.nodb` on 2026-08-28.
- Observation: its manifest parent hashes still equal the current canonical
  `_defaults.cfg` and `eu-disturbed.cfg`, and replay through the canonical
  snapshot resolver reproduces its 2,606 config bytes exactly.
  Evidence: read-only SHA-256 and `resolve_preset_snapshot` check on 2026-08-28.
- Observation: the Builder graph currently conflates Continental-US land-cover
  selection with its graph envelope (`nlcd-2019` only), while the canonical US
  catalog contains 114 applicable annual NLCD, NLCD Ever Forest, and eMapR
  datasets. Canada graph data uses C3S, but the live landuse locale priority
  does not classify token `canada` and can fall through to US.
  Evidence: `locale_profiles.py`, `capability_graph.py`, and
  `landuse_catalog.py` on 2026-08-28.
- Observation: the existing amendment transaction adds only missing registered
  attributes and explicitly preserves every stored capability axis.
  Evidence: project-config contract section 5.1 and
  `project_config_update.py` stored-graph resolution.
- Observation: no capability structure changed between source revision
  `280cf7e84` and the ratified checkpoint; the current five schema-v3 locale
  graphs therefore retain their historical structural identities.
  Evidence: normalized structural payload comparison and the checked-in
  `wepppy/nodb/locales/capability_structures/catalog.json`.
- Observation: provider/source revisions in the selected Builder parent chain
  may change even when serialized capability sections do not.
  Evidence: refresh identity comparison now treats a selected-chain-only delta
  as an auditable manifest refresh with an unchanged config digest.
- Observation: code-quality telemetry classifies the expanded
  `project_config_update.py` as yellow by size/function length but reports no
  blocking threshold because the gate is observe-only.
  Evidence: `tools/code_quality_observability.py --base-ref origin/master` on
  2026-08-28; the bounded ratified writer remains in the already listed module
  instead of introducing an unratified production file.
- Observation: the WEPP run mutation path intentionally retains stored-only
  authority for legacy compatibility, while the first UI implementation used
  the resolved live graph for its WEPP binary options.
  Evidence: final correctness review against the ratified surface matrix; the
  fix is to separate scoped live domain authority from stored WEPP presentation
  inside the already-listed run route.
- Observation: the first final full-suite attempt stopped when an unrelated
  Climate test could not manufacture its timing-sensitive same-size rewrite
  fixture; that exact test passed immediately in isolation and in the clean
  complete rerun without a code change.
  Evidence: isolated one-test pass followed by 7,147 passed and 63 skipped in
  the complete rerun on 2026-08-28.
- Observation: structurally valid terminal job diagnostics are insufficient
  unless their prior/resulting digests equal the retained reviewed preview.
  Evidence: final security review found and closed a mismatched-pair success
  path; the browser now leaves that outcome indeterminate.
- Observation: a route that validates climate dataset and method as one
  authority relation must also persist them as one lock-scoped transaction.
  Evidence: deterministic concurrent writes plus an injected second-field
  fault now prove rollback restores the complete pair current at lock entry.
- Observation: importing `rq_engine.auth` from an RQ task at module load enters
  `rq_engine.__init__`, which registers the project-config route and imports the
  partially initialized task module again; already-running processes concealed
  the cycle, while a fresh Forest worker exposed it before task execution.
  Evidence: failed Forest job `d2db892f-7715-45e3-a955-ca86bb2246c9`, a
  fresh-process `rq.utils.import_attribute` regression, and successful live
  worker resolution after moving authorization import to the call boundary.
- Observation: releasing a single-flight reservation with separate Redis
  `GET` and `DELETE` operations can delete a replacement reservation if the
  original key expires between them.
  Evidence: the security re-review identified the race; one Lua compare-delete
  now preserves a replacement in both deterministic tests and live Forest
  Redis execution.
- Observation: browser RQ tokens deliberately support an opaque subject while
  carrying the canonical numeric account identity in the signed `user_id`
  claim, but actor sanitization previously read only `sub` and therefore
  omitted worker metadata for this supported token shape.
  Evidence: Forest job `76bde759-ef34-4a27-83a8-cecf963f60b8` entered the
  task with no `auth_actor`; the token-issuance contract already asserts an
  opaque subject plus numeric `user_id`, and the corrected sanitizer retains
  that identity while continuing to reject a token with neither numeric form.
- Observation: capability refresh correctly preserves the original manifest
  `parent_chain`, so comparing every later preview only to that creation-time
  chain makes the already-recorded selected-chain discontinuity appear new
  forever even when the stored graph and config are current.
  Evidence: the successful Forest refresh produced identical prior/resulting
  graph identities on its next preview but repeated only the old-to-current
  selected-chain revisions. Recovery and availability now read the newest
  validated capability amendment's `resulting.selected_parent_chain`, with the
  immutable creation chain used only when no such amendment exists.

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
- Decision: Classify flattened projects before the non-flattened legacy locale
  path. No-capability and schema-v1 projects remain compatibility-only except
  that a valid named preset with exactly one recognized Builder base projects
  current climate and land-cover authority.
  Rationale: preserve every unrelated historical v1 axis while correcting the
  demonstrated locale overexposure and using the same locale graph hotpath as
  Builder creation.
  Date/Author: 2026-08-28, Codex; supersedes the narrower 2026-08-27 decision.
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
- Decision: Treat a changed selected parent chain as a refresh even when the
  complete capability-section serialization is unchanged.
  Rationale: the manifest must record current selected-source provenance; an
  empty config delta must not conceal that explicit acknowledged discontinuity.
  Date/Author: 2026-08-28, Codex.
- Decision: Accept the post-implementation scope audit as an inventory-only
  amendment and make its comparison a mandatory parent WP12 promotion gate.
  Rationale: the three added entries are directly required support surfaces
  for already reviewed behavior; preserving chronology and repeating the audit
  at promotion is more accurate than rewriting existing commits or evidence.
  Date/Author: 2026-08-28, operator/Codex.
- Decision: Treat Builder Land-cover selection as a default rather than a
  capability restriction, and correct the climate matrix with DEP NEXRAD and
  Future CMIP5 for US plus User-Defined Climate for every exposed locale.
  Rationale: users must be able to change maps within the locale envelope, and
  Europe must not inherit modes merely because a coarse legacy catalog listed
  them.
  Date/Author: 2026-08-28, operator/Codex; exactly ratified 16:29 UTC.

## Outcomes & Retrospective

Amendment 3 is ratified and its canonical documentation-only checkpoint is
commit `596ff5758ca83e6077b97f953431c2c881219840`. The append-only structural
reader floor is implemented with the refresh writer absent and has passed its
local focused gates, independent reviews, and exact-host `forest` acceptance.
Revision `80f4810b7be59d90a64b4771f587eb360987a820` is the recorded WP12D
rollback floor. The bounded writer, exact locale normalization, paired runtime
authority, accessible acknowledgment, and idempotent reconciliation are now
implemented locally. Success is bound to an immutable apply-time digest pair,
and climate catalog/mode persistence is one lock-scoped, rollback-safe
transaction. The update-specific frontend suite passes 19 tests; the complete
frontend suite passes 808 tests across 107 suites; frontend lint, stubs,
Vulture, changed-file broad-exception enforcement, diff checks, and the RQ
graph pass. After the Forest worker-load, identity-handoff, and provenance-
settlement corrections, the exact complete Python suite passes with 7,221
tests passed and 63 skipped. Independent correctness and security reviews are
READY with no remaining in-scope finding. Exact-host authenticated writer,
settled availability, reader-floor rollback, byte-preservation, and candidate-
restore acceptance pass on unchanged image `6ac7e7103046`. The final scope
audit found three required but unlisted support entries. The operator ratified
audit-only amendment `PC-24/WP12D-20260828-4` exactly as documented, preserving
all existing commits. That candidate was Forest-accepted, but the demonstrated
climate/land-cover discrepancy reopens WP12D under proposed amendment 5. Parent
WP12 promotion is blocked until the correction has its standalone checkpoint,
reader-first implementation, reviews, and exact-host Forest acceptance.
Production deployment remains excluded from WP12D.

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

The current continuation starts from exact amendment-5 baseline
`0ad76c547145bbe323148bac73410ff9cfcd01ef`; the amendment-3 checkpoint and
reader-floor work described in earlier revisions is completed history and does
not satisfy any amendment-5 gate. First close the finite decision/canonical
diff, obtain advisory correctness/governance reviews, and request exact
operator ratification. Then record the ratification time and obtain fresh
binding correctness, governance, and dedicated security READY reviews in the
three exact amendment-5 review artifacts. Commit only the authorized
documentation as a new standalone checkpoint. Record its full revision and
prove it is an ancestor before editing any amendment-5 production or test code.

Next add failing prior/current/unknown structure tests and append all five
ratified resulting identities in a standalone schema-v3 structural reader
floor while leaving locale profiles, climate/land-cover catalogs, graph writers,
and schema-v1 projection unchanged. Review and commit that floor separately.
Deploy it to exact host `forest` and prove it opens historical schema-v2, every
prior schema-v3 identity, and fixtures for all five resulting identities before
implementing or exposing graph writing. Record its exact revision as the
minimum rollback floor for the amendment-5 writer candidate.

Next add failing evidence. Parse every named config after defaults; build
legacy-style run fixtures for all five exposed bases and for no-capability
flattened, non-Builder, overlay, Turkey, RHEM, schema-v1, schema-v2, and
schema-v3 modes; include stale persisted locale and both project-local defaults
filenames. For flattened no-capability and non-preset/invalid schema-v1, cover
absent, empty, unknown, and valid locale without consulting the live registry.
For valid named presets, prove current climate/land-cover projection and
preservation of every other v1 axis. Assert Turkey's exact serialized profile/catalog revision and Yasin
fixed-map behavior. Prove links remain plain, locale overrides fail before
publication, RQ discovery matches mutation, and direct unsupported submissions
do not mutate or enqueue.

Add failing capability-refresh evidence around the existing update flow. Prove
one locale-to-graph hotpath serves Builder creation, legacy live authority,
preview, and apply. Cover additive-only, capability-only, combined, invalid,
stale, missing-acknowledgment, crash-recovery, exact-current, preserved-
selection, and removed/incompatible-selection states before implementation.

Then update the exact locale/climate/land-cover graph sources and bounded
stored-or-live resolver. Keep the Builder-selected land-cover ID as runtime and
`capability_defaults` state while serializing the complete locale envelope.
Apply current climate/land-cover authority only to projection-eligible schema-
v1 named presets and the already-ratified non-flattened/refresh hotpaths. Update
only the exact production consumers in amendment 5. Leave global
`NoDbBase.locales`, files on existing runs, other schema-v1 axes, schema-v2/v3
stored-default authority, and exact-current recovery unchanged. Preserve
explicit 409/503 diagnostics and selection-preserving acknowledged refresh.

Finally run focused and broad gates, complete independent correctness/security
reviews, compare every changed path with the ratified list, push, and validate
the exact revision on exact host `forest` without rebuilding an image. WP12
retains every merge-to-master and production action.

## Milestones

Milestone 1 produces the amendment-5 standalone contract checkpoint descended
from `0ad76c547145bbe323148bac73410ff9cfcd01ef`. Acceptance requires exact
operator ratification, Ready binding correctness/governance/security reviews,
ADR-0047 and every canonical promotion target synchronized, and a commit
containing no `.cfg`, production, or test-code edits. Its full revision is a
mandatory ancestor of all later amendment-5 code.

Milestone 2 produces the amendment-5 structural reader floor without any
amendment-5 graph writer. Acceptance requires append-only authorization for the
five exact resulting identities, preservation of every prior production
identity and historical schema-v2, rejection of unknown structures, independent
review, and exact-host Forest reopen evidence before graph writing exists.

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
It must bind exact registry/provider/deployment revisions and execute real,
unmocked DEP NEXRAD, Future CMIP5, and User-Defined `.cli` upload/validation/
build paths. It must validate every advertised expanded-US land-cover year and
perform one real annual NLCD, NLCD Ever Forest, and eMapR vote fetch/build.
Earlier evidence may be reused only when all bound revisions exactly match.

## Concrete Steps

Work from `/home/workdir/wepppy`.

Initiative branch: feature/project-owned-config
Canonical branch: master
Promotion policy: merge only at the roadmap promotion gate

The initiative's historical start is
`5e04e0da9a23dd676e171f1857e14fa38cc9dfbe`; amendment 5 starts exactly at
`0ad76c547145bbe323148bac73410ff9cfcd01ef`. Canonical merge base remains
`6af9ecdd63921189804c5e292114a97253914cbb`. After ratification and binding
reviews, record the new amendment-5 standalone checkpoint revision here and in
the tracker. Verify that exact revision is an ancestor before editing any path
in amendment 5's production or test-code source boundary; the old
`596ff5758...` checkpoint does not satisfy this gate.

Iterate with:

    wctl run-pytest tests/nodb/test_locale_capability_authority.py tests/nodb/test_project_config_reader_foundation.py tests/nodb/test_project_config_registry_serializer.py tests/nodb/test_project_config_preset_snapshot.py tests/nodb/test_project_config_update.py tests/nodb/test_defaults_cfg_compatibility.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_climate_bp.py tests/weppcloud/routes/test_soils_bp.py tests/microservices/test_rq_engine_builder_routes.py tests/microservices/test_rq_engine_project_routes.py tests/microservices/test_rq_engine_project_config_update_routes.py tests/microservices/test_rq_engine_landuse_routes.py tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_soils_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py tests/microservices/test_rq_engine_orchestration_read_routes.py tests/rq/test_project_config_update_rq.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test

Before handoff, run the full Python suite, affected stubs, broad-exception
enforcement, vulture, `git diff --check`, scoped documentation lint, and exact
Forest checks. Record counts and revisions in the tracker.

The exact preexisting dirty paths excluded from every WP12D stage are:

- `code-quality-report.json`;
- `code-quality-summary.md`;
- `docker/validate-cap-runtime-contract.sh`;
- `docs/infrastructure/incident-2026-08-25-production-compose-partial-build.md`;
- `docs/standards/hardening-lifecycle-standard.md`;
- `docs/ui-docs/accessiblity.md`;
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
No-capability flattened and schema-v1 states outside the exact valid-preset
exception must preserve existing behavior for absent, empty, unknown, and
valid locale without live-registry access. Valid presets must use only current
climate/land-cover projection while present valid v1 axes otherwise remain
restrictive. Non-Builder, overlay, Turkey, and
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

Plan revision note (2026-08-28): exact operator ratification of audit-only
amendment `PC-24/WP12D-20260828-4` adds the export-only locale package surface,
append-only capability-structure authority, and bounded signed-identity
handoff to the audited support inventory. Existing commits are preserved, and
parent WP12 must repeat the comparison before merge or production promotion.

Plan revision note (2026-08-28): proposed amendment
`PC-24/WP12D-20260828-5` corrects the five-locale climate matrix, separates a
Builder land-cover default from the complete locale envelope, and gives valid
schema-v1 named presets a live climate/land-cover projection without rewriting
their stored provenance. It requires exact ratification and a new reader-first
Forest gate before implementation acceptance.
