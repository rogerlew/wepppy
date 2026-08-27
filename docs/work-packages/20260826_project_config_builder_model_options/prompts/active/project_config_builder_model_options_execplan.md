# Add compatible watershed representation and WEPP binary selections

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

A Config Builder user can create a WhiteboxTools watershed using either Single
or Multiple OFE representation and can select the WEPP binary recorded in the
project-owned configuration. Invalid backend, representation, and binary tuples
are never offered as silently valid and are rejected by the server if submitted.

## Progress

- [x] (2026-08-27 05:25 UTC) Ratified the default binary-list provider as the
  sole Builder availability authority and passed independent correctness and
  governance contract reviews.

- [x] (2026-08-27 03:36 UTC) Scaffold package and proposed contract checkpoint.
- [x] (2026-08-27 04:00 UTC) Obtain and disposition two independent contract reviews.
- [x] (2026-08-27 04:00 UTC) Commit checkpoint `95559bc6f` as a standalone ancestor.
- [x] (2026-08-27 04:20 UTC) Implement registry, resolver, snapshot, API, UI, maturity, and type-surface changes.
- [x] (2026-08-27 04:30 UTC) Add focused regression, generated-config, legacy-manifest, and real binary execution evidence.
- [ ] Run remaining Forest validation (completed: npm, focused and full pytest,
  stub, docs, broad exceptions; full pytest: 6,962 passed and 63 skipped).
- [ ] Ratify and implement the operator-superseding complete binary-provider
  availability contract.
- [ ] Complete correctness review, update tracker, and close the package.

## Surprises & Discoveries

- The original two-entry allowlist was superseded by the operator's designation
  of `get_linux_wepp_bin_opts()` as the canonical Builder availability source.
  Availability is deployment-dependent while defaults remain fixed.
- The operator selected the deployed `wepp_260803` release, rather than the
  older documented minimum, as the default and Multiple OFE Builder binary.

## Decision Log

- Decision: register `wepp_dcc52a6` and `wepp_260803` as the initial binary
  choices, default to `wbt` and `wepp_260803`, and require that pair for
  `multiple-ofe`.
  Rationale: this is the operator-ratified deterministic registry and default.
  Date/Author: 2026-08-27, Codex.
- Decision: classify every Builder-created project as Preview and leave old
  Builder manifests unmigrated and update-ineligible.
  Rationale: Builder has not crossed its production promotion gate, while the
  immutable legacy parent chain cannot truthfully acquire a binary component.
  Date/Author: 2026-08-27, Codex.
- Decision: supersede the two-entry allowlist with the complete canonical
  provider output, including `latest`, without a second Builder filter.
  Rationale: one provider owns availability; `wepp_260803` remains the explicit
  default and sole Multiple OFE binary.
  Date/Author: 2026-08-27, Codex.

## Outcomes & Retrospective

Pending implementation.

The initial bounded implementation is complete locally with explicit defaults,
server-enforced tuples, persisted binary provenance, dependency-aware UI, and
Preview maturity. The provider-list supersession is pending implementation.
Forest WBT Multiple OFE and provider-wide execution acceptance remain pending,
so the new registry must not be promoted to production.

## Context and Orientation

Component TOML files under `wepppy/nodb/config_builder/profiles/` form an
immutable allowlisted registry. `schema.py` defines component and selection
types, `registry.py` validates references, `resolver.py` composes `config.cfg`,
and `snapshot.py` parses browser payloads. Rq-engine Builder routes serialize
the description and validation result. `config_builder.htm` and its controller
render and submit server-described selections.

## Plan of Work

After the superseding standalone contract checkpoint, generate WEPP-binary
components from the canonical provider, incorporate provider state in the
registry revision, and retain the Multiple OFE representation profile. Extend
locale/capability definitions and resolver validation so
component requirements enforce WBT and the compatible binary. Add the required
payload field, provenance, review serialization, template control, and client
dependency handling. Derive Preview maturity for the fixed Builder config token
from its manifest. Preserve old manifest reading and execution, make update
availability explicit, and do not migrate runs.

## Concrete Steps

Work from `/home/workdir/wepppy`. Use `apply_patch` for edits. Run focused NoDb,
rq-engine route, WEPPcloud template, and controller tests during iteration.
Rebuild generated controller assets if the source controller changes.

## Validation and Acceptance

Focused tests must parse generated config bytes and observe `multi_ofe = true`
and `bin = "wepp_260803"` for the valid Multiple OFE tuple. Direct resolver and
API tests must reject TOPAZ plus Multiple OFE and Multiple OFE plus
`wepp_dcc52a6`. Browser tests must exercise backend and binary changes in both
directions and observe invalid downstream values cleared with an announced
reason. Unmocked role resolution and representative execution for every exposed
binary, plus a representative Forest WBT MOFE prep/run, are required before
exposure. Finish with canonical frontend and repository gates proportional to
the touched surface.

## Idempotence and Recovery

Registry generation is deterministic for a fixed provider state and the opaque
revision changes with provider output or `latest` target identity. Reverting the
implementation commit restores the prior Builder. No run migration or
destructive operation occurs.

## Artifacts and Notes

Review artifacts and final validation output live under this package's
`artifacts/` directory.

## Interfaces and Dependencies

No external dependency is added. Extend the existing immutable dataclasses,
TOML registry, rq-engine JSON contract, and Builder controller. Do not use
runtime directory scanning for accepted Builder values.

Plan revision note (2026-08-27): initial contract-checkpoint and implementation plan.
