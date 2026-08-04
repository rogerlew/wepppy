# Project-Owned Configuration Implementation Roadmap

> **Status:** Ratified 2026-08-04 by WP00R for implementation on the
> noncanonical initiative branch; package folders are created only when their
> execution begins.
>
> **Noncanonical initiative branch:** `feature/project-owned-config`
>
> **Contract:**
> [`project-owned-config-contract.md`](project-owned-config-contract.md)

## 1. Purpose

This roadmap decomposes the project-owned configuration contract into
dependency-ordered work packages. It assigns one closure owner to every
contract requirement while allowing implementation work to cross package
boundaries when the repository requires it.

The roadmap prevents two failure modes:

1. a downstream package stalls because an upstream package delivered an API or
   artifact without the behavior needed by its consumer; and
2. a requirement is mentioned by several packages but owned and verified by
   none.

The contract remains authoritative for behavior. This roadmap is authoritative
for implementation ownership, sequencing, evidence handoff, and final closure.

## 2. Execution Rules

Every package listed here MUST be scaffolded according to
[`docs/work-packages/README.md`](../work-packages/README.md) when execution
begins. Each package MUST contain `package.md`, `tracker.md`, and an active
ExecPlan. The ExecPlan MUST be written from the contract and this roadmap, not
from chat history.

### 2.1 Initiative branch and promotion boundary

All roadmap scaffolding and implementation MUST use the shared integration
branch `feature/project-owned-config`. This branch is explicitly noncanonical:
its presence on the remote does not mean its behavior is released, supported,
or approved for production. `master` remains the canonical release branch.

Every package `package.md`, `tracker.md`, active ExecPlan, handoff, and review
artifact MUST state:

```text
Initiative branch: feature/project-owned-config
Canonical branch: master
Promotion policy: merge only at the roadmap promotion gate
```

Before editing or executing a package, its agent MUST verify and record that
`git branch --show-current` returns `feature/project-owned-config` and that the
local branch tracks `origin/feature/project-owned-config`. Package commits and
pushes target that branch. Agents MUST NOT create a package-specific branch or
merge package work into `master` unless this roadmap is amended by the operator.

WP11 MUST deploy and record an exact commit from the feature branch for Forest
acceptance. WP12 is the first promotion boundary: after all WP11 gates pass, it
merges the reviewed feature-branch revision into `master` and deploys the
resulting canonical revision to production. Before WP13 begins, the feature
branch MUST be synchronized to that promoted `master` revision. WP13 performs
shared-alias retirement on the same feature branch and uses a second reviewed
merge into `master` for the later retirement release.

A package may be complete on the feature branch while remaining unpromoted.
Package status and evidence MUST distinguish `implemented on feature branch`,
`Forest accepted`, and `promoted to master`.

### 2.2 Requirement closure ownership

- Every requirement has exactly one **closure owner** in section 5.
- A closure owner is accountable for the final contract test, integration
  evidence, documentation, and disposition, even when another package writes
  some of the code.
- A contributing package MUST identify the affected requirement IDs in its
  tracker and deliver code/tests/evidence to the closure owner.
- A package MUST NOT close a requirement as “handled downstream” unless the
  ownership ledger names the accepting package and that package records the
  transfer in its tracker.
- Existing behavior or previously completed work counts only when the closure
  owner records a concrete evidence link and verifies it against the current
  contract.
- Final closure states are `verified`, `accepted-existing`, `not-applicable`, or
  `transferred`. “Probably covered” and “tested elsewhere” are not closure
  states.
- A `transferred` record MUST name the source package, receiving package,
  affected requirement IDs, artifact/commit, acceptance timestamp, and
  receiving-owner status. The source package cannot close on that disposition
  until the receiving owner explicitly accepts it in the receiving tracker.

### 2.3 Cross-package leakage

Implementation agents are authorized to make the smallest required change
outside their package's primary subsystem when that change is necessary to
satisfy an owned requirement or preserve compatibility. They MUST:

1. record the leaked scope and affected requirement IDs in both relevant
   trackers;
2. preserve the receiving subsystem's contracts and nearest `AGENTS.md` rules;
3. add or update tests at the actual behavior boundary;
4. notify the requirement's closure owner; and
5. leave the closure decision with that owner.

If the upstream package is still open, the work SHOULD be incorporated there.
If it is closed, the discovering package MAY implement the minimal repair
rather than block on package taxonomy. A new remediation package is required
only when the repair is independently high-risk or would materially expand the
current package.

Behavior discovered during implementation that changes this contract MUST be
ratified in the contract before the changed behavior ships. Package boundaries
never authorize silent contract drift.

### 2.4 Feature flags and promotion

- Reader compatibility lands before any flattened-config writer is enabled.
- Every flattened-config writer remains disabled until secret sanitization,
  canonical source normalization/serialization, manifest, compatible-reader,
  and WP10 lifecycle-integrity gates pass.
- Config Builder UI exposure remains disabled until its schema, validation,
  capability enforcement, creation, and idempotency surfaces pass together.
- User-initiated config updates remain disabled until WP08 preview/apply auth,
  locking, and recovery, WP09 UI review, and WP10 fork/archive consistency pass
  together.
- A package may merge dormant code behind a default-off server feature flag;
  merging dormant code is not production acceptance.

## 3. Dependency Graph

```text
WP00R contract ratification/checklist
  ├─> WP00A secret sanitization ───────────┐
  ├─> WP00B canonical normalization ──────┼─> WP03 registry/serializer ─┐
  └─> WP01 defaults compatibility ─> WP02 reader/manifest ─────────────┼─> WP04 preset writer
                                                                      │          │
                                                                      │          ├─> WP05 capabilities
                                                                      │          │          │
                                                                      │          │          └─> WP06 builder API ─> WP07 builder UI
                                                                      │          │
                                                                      └──────────┴─> WP08 update backend ─> WP09 update UI
                                                                                         │
WP04 preset writer ──────────────────────────────────────────────────────────────────────┴─> WP10 lifecycle integrity

all WP00R-WP10 prerequisites ─> WP11 Forest acceptance ─> WP12 production cutover ─> WP13 alias retirement
```

After WP00R, WP00A, WP00B, and WP01 may run in parallel. WP02 and WP03 may
overlap after their own prerequisites pass. WP07 and WP08 may run in parallel.
No overlap changes the exit gates or closure ownership below.

## 4. Work-Package Sequence

| ID | Proposed work-package folder | Primary scope | Depends on | Security | Exit gate |
| --- | --- | --- | --- | --- | --- |
| WP00R | `20260804_project_config_contract_ratification` | Run the contract-first approval checkpoint; freeze the contract/roadmap revision; generate the paragraph-level normative requirement checklist; map every `MUST`, `MUST NOT`, and section-15 regression bullet to a PC row and tracker owner; record security/governance review. No implementation. | None | High | Approval artifact is signed/dispositioned; the exhaustive checklist has no unmapped requirement; implementation packages are authorized to start. |
| WP00A | `20260804_project_config_secret_sanitization` | Inventory and remove stale/live credentials from shared configs; move live secrets to runtime secret boundaries; classify and reject secret/runtime-host-bound values; add enforceable materialization scanning. | WP00R | High | Shared sources contain no materializable secrets; runtime secret resolution remains functional; scanner/security evidence covers generated projects and archives. |
| WP00B | `20260804_project_config_source_normalization` | Inventory accepted lexical forms; ratify canonical scalar/list encodings; normalize shared defaults/presets; reject ambiguous/unsupported values; add canonical round-trip and byte-identity golden fixtures. | WP00R | Low | Every shared source parses under the typed inventory and produces stable canonical bytes without guessed types. |
| WP01 | `20260804_defaults_cfg_compatibility` | Move the real shared `_defaults.toml` to `_defaults.cfg`; create the relative compatibility symlink; implement project-local/shared dual-name precedence; update direct consumers/tests; execute the defaults compatibility Forest gate for contract Phase 3 items 1-5 plus older-reader proof. | WP00R | Low | New and legacy readers resolve identical effective values; the symlink works for an older-reader fixture; defaults compatibility Forest evidence is recorded for WP11 consumption. |
| WP02 | `20260804_project_config_reader_foundation` | Add flattened marker/schema detection, no-shared-fallback loading, manifest-v1 parsing, structured digest warnings, invalid/newer-manifest degraded behavior, top-level run-root authority, nested/PUP inheritance, and reader feature flags. No writers. | WP00R, WP01 | High | Local reader inventory and fixtures cover every web/RQ reader; legacy resolution is unchanged; nested inheritance and warning behavior are tested. Deployed-fleet and rollback proof remain WP11 scope. |
| WP03 | `20260804_project_config_registry_serializer` | Implement real-TOML registry/schema/resolver, stable IDs, ordered contributor writeover, canonical `.cfg` serializer, initial continental-US matrix, component validation, and deterministic builder descriptions. No project creation. | WP00R, WP00B | Low | Registry validation and deterministic serialization pass; all initial descriptors resolve; unsupported combinations fail explicitly; no writer is enabled. |
| WP04 | `20260804_project_config_preset_snapshot` | Snapshot new Interfaces-created projects using their original preset token/filename; write normative manifest and immutable parent chain; normalize/materialize allowlisted query overrides; add 24-hour creation idempotency and incomplete-initialization cleanup; keep writer default-off. | WP00R, WP00A, WP00B, WP02, WP03 | High | Every supported preset passes schema/capability completeness; create/replay/conflict/failure tests pass; existing Interfaces links/tokens remain unchanged; no secrets enter project artifacts. |
| WP05 | `20260804_project_config_capability_enforcement` | Populate stable climate/soil/land-use capability IDs and make resolved capabilities authoritative for newly presented and submitted choices at explicitly inventoried UI/server endpoints; preserve the non-contractual legacy persisted-selection carve-out. | WP02, WP03, WP04 | High | Each affected endpoint is inventoried; UI visibility and server validation use the same IDs; hidden choices cannot be newly invoked; legacy persisted routing behavior is unchanged. |
| WP06 | `20260804_project_config_builder_api` | Implement rq-engine builder description/validation and synchronous creation; registry-revision staleness, field errors, role-enforced cell-size override, fixed `config.cfg` token, idempotency reuse, manifest output, and canonical response/security contracts. | WP04, WP05 | High | API contract, auth, stale-schema, cell-size, idempotency, and creation tests pass; one complete proposed project can be created with the writer still deployment-gated. |
| WP07 | `20260804_project_config_builder_ui` | Add the optional one-page Config Builder while preserving Interfaces; dependent controls, derived capabilities, review summary, duplicate-submit protection, responsive behavior, keyboard/focus/status accessibility, and actionable errors. | WP06 | High | Frontend unit/lint and browser accessibility flows pass; review matches server resolution; successful creation navigates to `/config/`; Interfaces remains unchanged. |
| WP08 | `20260804_project_config_update_backend` | Implement read-only availability/preview and owner-or-Admin/Root apply routes; opaque/stale preview handling; async RQ merge-only job; project lock, pending journal/recovery, manifest amendment, digest-mismatch provenance, worker-time reauthorization, and queue wiring/catalog updates. | WP02, WP03, WP04 | High | Checks never write; reviewed applies add only missing registered values; failures recover a consistent pair; concurrent applies deduplicate; canonical RQ/auth/error and queue-graph gates pass. |
| WP09 | `20260804_project_config_update_ui` | Add async page-load availability check, run-header notice, authenticated nonblocking digest-warning state/UI, accessible preview modal, explicit apply/status/error flow, and nested-run linkage to the top-level authority. | WP08 | High | No read-triggered mutation occurs; users can review the full delta; digest warning is visible without blocking and is deduplicated at the page-load boundary; only authorized apply is offered; stale/conflict/job states and accessibility tests pass. |
| WP10 | `20260804_project_config_lifecycle_integrity` | Integrate config/update locks with fork and archive; recover pending updates before consistent copy; preserve config/manifest through fork/download/restore; verify nested/PUP authority, invalid/newer manifest restore, read-only/public behavior, and byte preservation. | WP04, WP08 | High | Create/reopen/fork/archive/restore and concurrent-update fixtures prove one consistent authority; legacy archives retain fallback; no pending journal is used as archive recovery. |
| WP11 | `20260804_project_config_forest_acceptance` | Deploy the complete default-off reader/writer stack to Forest; consume WP01 defaults evidence; validate mixed-version readers, all four initial DEM/backend combinations, named preset and builder flows, climate/soil/land-use paths, updates, restart, fork/archive/restore, rollback, and operator evidence. | WP00R, WP00A, WP00B, WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08, WP09, WP10 | High | Every contract regression item has evidence or an explicit blocking disposition; only validated combinations are enabled; deployed worker/revision and rollback-target compatibility are proven. |
| WP12 | `20260804_project_config_production_cutover` | Merge the WP11-accepted feature-branch revision into `master`; deploy that canonical revision; perform staged feature-flag enablement, health/danger observation, rollback verification, documentation/operator runbooks, and handoff of deployed/rollback revision inventory plus observation evidence. | WP11 | High | The reviewed merge commit and production revision are recorded; production validation and observation pass; supported revisions read `_defaults.cfg`; project-owned writer/update flags are safely enabled; alias-retirement prerequisites are handed to WP13. |
| WP13 | `20260804_defaults_toml_alias_retirement` | Synchronize the feature branch to promoted `master`; revalidate deployed and supported rollback revisions in the next planned release; remove only the shared `_defaults.toml` symlink on the feature branch; retain project-local legacy-reader support; run the final audits; merge the reviewed retirement revision into `master`. | WP12 | High | The retirement merge and production revision are recorded; shared symlink is absent; project-local legacy `_defaults.toml` still resolves; every checklist item and PC row has an accepted closure state; roadmap is closed. |

## 5. Requirement Ownership Ledger

The status `contracted` means the behavior is specified but implementation
evidence has not yet been accepted. Work-package trackers replace this status
with one of the closure states in section 2.2.

| Requirement ID | Contract scope | Closure owner | Contributing packages | Required closure evidence | Initial status |
| --- | --- | --- | --- | --- | --- |
| PC-00 | Contract-first ratification and exhaustive normative requirement mapping (contract status and section 16) | WP00R | Every package | Approval artifact plus checklist mapping every normative paragraph/regression bullet to a PC row and tracker task. | Verified by WP00R, 2026-08-04 |
| PC-01 | Project-owned file naming, flattened marker, and project-local authority (sections 5, 6.1, 7.1, 7.3) | WP02 | WP04, WP06 | Loader and creation fixtures for preset basename and builder `config.cfg`; no shared fallback after marker recognition. | Contracted |
| PC-02 | Legacy local/shared fallback and dual defaults-name precedence (sections 6.2-6.3) | WP01 | WP02, WP11 | Full four-location precedence matrix and legacy reopen equivalence. | Contracted |
| PC-03 | Shared `_defaults.cfg` move, relative symlink compatibility, and dual-name evidence (sections 14.1-14.3) | WP01 | WP02, WP11 | Move/symlink commit, older-reader proof, defaults compatibility Forest evidence, permanent project-local legacy reader test. | Contracted |
| PC-04 | Secret removal, snapshot-safe classification, and no secret-bearing project/archive artifacts (sections 5, 10, 13, 14.0) | WP00A | WP04, WP06, WP10, WP11, WP12 | Sanitization inventory, secret scanner/gate, security review, generated project and archive inspection. | Contracted |
| PC-05 | Canonical byte serialization and source normalization (section 8.1) | WP00B | WP03, WP04, WP10 | Ratified type encodings, normalized sources, golden byte fixtures, deterministic round trip, archive byte preservation. | Contracted |
| PC-06 | Declarative real-TOML registry, stable IDs, ordered writeover, validation, and current-definition update semantics (sections 5.1, 8, 8.2) | WP03 | WP04, WP08 | Registry/schema tests, contributor collision/writeover tests, stable-ID failure behavior, provenance fixtures. | Contracted |
| PC-07 | Initial continental-US DEM/backend/representation/soil/land-use/climate/no-mod matrix and cell-size rules (sections 7.2, 7.5) | WP03 | WP05, WP06, WP07, WP11 | Descriptor tests plus Forest evidence for every exposed combination and privilege matrix. | Contracted |
| PC-08 | Normative manifest-v1 shape, immutable creation chain, amendments, digest warning, and invalid/newer-manifest behavior (sections 6.1, 10) | WP02 | WP04, WP08, WP09, WP10 | Schema fixtures, builder/preset/fork manifests, structured warning and nonblocking authenticated header UI, update-disable behavior, restore compatibility. | Contracted |
| PC-09 | Named-preset snapshot stability, query-override allowlist/provenance, and developer completeness responsibility (section 7.1) | WP04 | WP03, WP05, WP11 | All-preset validation, override rejection/materialization tests, unchanged Interfaces route/token tests. | Contracted |
| PC-10 | Creation durability, readiness boundary, idempotency, replay/conflict, and cleanup (sections 7.4, 7.6, 11) | WP04 | WP06, WP07, WP11 | Success replay, concurrent/different-payload conflict, failed-init cleanup, no partial-ready project. | Contracted |
| PC-11 | Capability IDs and enforcement for newly presented/submitted choices, with legacy persisted behavior explicitly unchanged (section 9) | WP05 | WP03, WP04, WP06, WP07 | Endpoint inventory and paired UI/server tests; before/after legacy routing characterization. | Contracted |
| PC-12 | Builder API, registry staleness, fixed token, auth, errors, and privileged cell-size override (sections 7.2-7.6, 13-13.1) | WP06 | WP03, WP04, WP05 | Route/OpenAPI tests, role matrix, stale revision, canonical errors, generated manifest/config. | Contracted |
| PC-13 | Optional one-page Config Builder UX and accessibility while preserving Interfaces (section 7.4) | WP07 | WP05, WP06 | Frontend tests, keyboard/zoom/announcement evidence, duplicate-submit test, Interfaces regression. | Contracted |
| PC-14 | User-initiated merge-only availability/preview/apply and no read-triggered writes (section 5.1) | WP08 | WP09 | Read-only check, complete preview, explicit enqueue, stale preview, merge-only and no-overwrite tests. | Contracted |
| PC-15 | Update authorization, locking, recovery journal, concurrency, provenance, and RQ behavior (sections 5.1, 10-11, 13.1) | WP08 | WP09, WP10 | Owner/Admin/Root and public denial tests, worker reauth, crash-point recovery, queue graph/live tree evidence. | Contracted |
| PC-16 | Top-level run-root authority and nested/PUP inheritance with legacy child-local preservation (section 6.4) | WP02 | WP09, WP10, WP11 | Resolver precedence tests and real nested create/reopen/fork/archive/restore evidence. | Contracted |
| PC-17 | Fork/archive/restore/download consistency, update-lock coordination, and read-only/public behavior (section 12) | WP10 | WP08, WP11 | Concurrent update/copy tests, archive inspection, restore/reopen, public/read-only mutation denial. | Contracted |
| PC-18 | Reader-first mixed-version rollout, feature flags, Forest gate, and rollback proof (sections 14.2-14.5) | WP11 | WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08, WP09, WP10 | Deployed revision inventory, reader/writer flag evidence, complete Forest matrix, restart and rollback results. | Contracted |
| PC-19 | Production rollout, observation, feature enablement, and alias-retirement handoff (section 14.4) | WP12 | WP11 | Production health/danger evidence, supported rollback inventory, operator runbook, accepted WP13 handoff. | Contracted |
| PC-20 | Shared alias retirement with permanent project-local legacy support (sections 6.2, 14.4) | WP13 | WP01, WP11, WP12 | Production observation, rollback-target audit, shared symlink absence, project-local legacy reader test. | Contracted |
| PC-21 | Required regression evidence, synchronized user/operator/developer documentation, and complete initiative closure (sections 15-16 and repository standards) | WP13 | Every package | Per-package test/doc handoffs plus exhaustive normative-checklist audit, final ledger with no unowned/unresolved row, and broad pre-handoff gates. | Contracted |

## 6. Package Handoff Contract

WP00R MUST create an initiative-level normative checklist artifact by
enumerating every contract paragraph containing `MUST`/`MUST NOT` and every
section-15 regression bullet. Each checklist entry MUST identify its contract
location, PC row, closure owner, contributing tracker task, evidence type, and
current disposition. Summary PC rows do not replace this checklist.

When a package is scaffolded, its tracker MUST import every checklist entry it
owns or contributes to. Package closeout updates those entries with exact
evidence or an acknowledged transfer. WP11 adds Forest dispositions, and WP13
performs the final no-unmapped/no-unresolved audit.

Each package MUST publish a handoff artifact or tracker section containing:

- exact feature-branch commit/revision, upstream tracking state, and feature-
  flag state;
- requirement IDs implemented, partially implemented, or affected;
- API/file/schema outputs delivered to downstream packages;
- test commands and summarized results;
- security review disposition when required;
- compatibility assumptions and supported rollback revision;
- incomplete work with an accepting closure owner; and
- newly discovered cross-package leakage and its disposition.

A downstream package MUST validate its prerequisite artifacts rather than
assuming the upstream package is complete because its tracker says “Done.” A
failed ingress check reopens the owning requirement or records a blocking
remediation; it does not silently weaken downstream acceptance.

## 7. Per-Package Mandatory Gates

Every package applies the repository-standard checks relevant to its changes.
In addition:

- Package scaffolds, trackers, ExecPlans, and handoffs MUST name and verify the
  initiative branch as required by section 2.1.
- Pure UI or UI-coupled packages MUST preserve contract-first sequencing and
  run frontend lint/tests plus targeted browser accessibility checks.
- Rq-engine or queue-wiring packages MUST update
  `wepppy/rq/job-dependencies-catalog.md`, run `wctl check-rq-graph`, and inspect
  a representative live job tree.
- NoDb mutation packages MUST follow the persistence/concurrency contract and
  exercise lock/cache behavior.
- High-security packages MUST produce a dedicated security review artifact and
  close all medium/high findings.
- Packages changing user, operator, or developer workflows MUST update those
  docs in the same change set.
- Any package that changes a parameterization default, formula, threshold,
  conversion, or fallback MUST satisfy the parameterization ADR gate before
  merge. Merely materializing an unchanged existing value does not create a new
  parameterization decision.

No package may substitute the final Forest acceptance package for its own
targeted tests. WP11 validates integration; it does not retroactively supply
missing unit, contract, security, or accessibility evidence.

## 8. Forest and Production Closure

WP11 owns the integrated requirement checklist. For every PC row it MUST record
the contributing package revision, the targeted evidence, and the Forest
result. A failed row blocks only the affected feature flag or builder
combination when isolation is safe; it blocks the whole promotion when reader,
manifest, security, archive consistency, or rollback safety is affected.

WP12 owns production cutover, observation, and the explicit retirement handoff.
It MUST leave the shared `_defaults.toml` symlink present and provide WP13 with
the deployed/rollback revision inventory and observation evidence.

WP13 owns final roadmap closure. It MUST audit every normative-checklist entry
and requirement row, resolve or formally transfer every residual, and confirm
that no package is being closed solely because another package was expected to
notice the same requirement. It removes the shared `_defaults.toml` symlink
only after the contract's production and rollback gates pass.
