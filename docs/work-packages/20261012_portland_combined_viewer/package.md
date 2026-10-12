# Portland group access and combined watershed viewer

**Status**: Open — forest implementation complete; final validation in progress (2026-10-12)
**Created**: 2026-10-12 08:21 UTC  
**Security impact**: high; independent security and correctness reviews required

## Overview

Portland group members must be able to open the watershed collections linked from the Portland interface and inspect their modeled results. The combined viewer currently rejects these legacy runs for lacking `PUBLIC` markers; its old result endpoints also no longer exist. This package restores authorized access and delivers a functional Deck.gl collection viewer without making the runs public.

The operator subsequently authorized forest implementation through rollout readiness, including required local commits, forest data preparation, stack restarts, and dev-agent permission changes. Production deployment and production data writes remain outside this authorization. The [ExecPlan](prompts/active/portland_combined_viewer_execplan.md) describes subsequent execution; [tracker](tracker.md) records readiness.

## Accepted intent and rationale

On 2026-10-12 the operator clarified: “portland group is suppose to be able to see those runs.” The existing landing page checks the `PortlandGroup` Flask-Security role in `wepppy/weppcloud/routes/locations.py`. Reuse that existing identity mechanism unless investigation establishes an authoritative replacement; do not create a similarly named feature group or infer membership from run names.

Membership grants read access only to the authoritative Portland run collection, including downstream resources needed to render it. It does not grant unrelated private-run access, model execution, membership administration, or public publication. Each supplied run must be authorized independently. Preserve independently authorized public/owner/admin access according to applicable contracts; classify existing anonymous legacy access before proposing any restriction.

The rejected `PUBLIC`-marker workaround would publish data instead of honoring group access. Simply removing validation or changing the URL to viewer2 would leave authorization gaps and obsolete data calls. A prefix such as `portland_` is not sufficient proof of resource membership.

## Scope and complexity budget

- Inventory the nine Portland collection links, actual configurations, membership mechanism, and server-owned run associations.
- Prepare a contract-first checkpoint for bounded Portland read access across viewer, generator, geometry, query-engine, reports, and any consumed browse/download surfaces.
- Prepare missing legacy artifacts from retained outputs, with semantic parity and recovery evidence.
- Reuse the existing Deck.gl renderer and multi-run identity support for arbitrary authorized collections; preserve existing shared-link parameters.
- Repair generator entry, submission, encoding, configuration resolution, and combined bounds; connect the Portland links to the repaired path.
- Update affected user/operator/developer documentation and validate production behavior after a separately authorized deployment.

New queues, services, datastores, dependencies, privileges, protocols, and deployment topologies: none. Start with a bounded shared authorization decision, an existing conversion path, and an adapter into existing Deck.gl components. Retain evidence of failed real acceptance before proposing escalation. No forced BatchRunner migration, model reruns, general authorization rewrite, Seattle migration, default/formula changes, or role-to-feature-group migration is included.

## Implementation fidelity and evidence

Target: **faithful extraction** of the existing collection workflow onto the current renderer/data path, with the operator's group-access correction. The implementation is wired on forest; production rollout is a separate milestone. Preserve runoff, subsurface runoff, baseflow, loss, available phosphorus, English/SI units, ranges, title, bounds, and run-specific drilldown. Source behavior is in `combined_ws_viewer.htm`, `combined_ws_viewer2.htm`, and `combined_watershed_viewer_generator.py` under `wepppy/weppcloud/`.

Generated-output and browser evidence are required. Distinguish implemented, wired, locally validated, environment validated, deployed, repaired, and incident resolved. The current claim is implemented and forest environment validated for all nine collections, with final broad-test, identity and provenance receipts still being completed. No production repair or incident-resolution claim is made.

## Generated artifact validation and compatibility plan

Before run writes, record source paths/checksums, schemas, identifier types, units, output scope, converter revision, expected destinations, and rollback ownership. Use a copy of one affected run first. Preserve original NoDb and model outputs; add derived artifacts without renaming/removing existing keys or columns. Do not run conversion from a viewer GET.

Trace the requested collection through reloaded run association/configuration, generated geometry and summary/WEPP Parquet, query-engine's exact consumed files/catalog, returned rows, and rendered values. Compare IDs, row counts, missing values, and numeric values/units to legacy output with justified tolerances. Parse content rather than checking only file existence. Validate run-scoped downstream consumers and established browse/archive visibility. No fresh model simulation is required unless retained output proves insufficient and a rerun is separately authorized.

## Success criteria

- [ ] A current PortlandGroup member can open all nine linked collections; the seven-run current-condition map displays correct results and drilldown.
- [ ] Every collection entry validates each requested run; unrelated private and mixed unauthorized collections are rejected. Downstream consumers preserve existing independent grants, including the confirmed ownerless legacy access, without a new data embargo.
- [ ] Removal of membership ends group-derived access without requiring a process restart; independently granted access remains valid.
- [ ] Public and ordinary single-run/BatchRunner dashboard behavior remains compatible; no runs become public as a workaround.
- [ ] Old URLs retain selected variable, units, ranges, title, and location; generator loads empty and handles invalid submissions with actionable errors.
- [ ] Missing optional phosphorus is handled explicitly; missing required artifacts cannot appear as a successful empty/zero-valued map.
- [ ] Actual generated artifacts and all nine scenario links pass production-equivalent validation; authorized deployment and post-deploy recovery evidence are retained separately.
- [ ] Independent correctness and security reviews have no unresolved medium/high findings; canonical docs and module docs reflect delivered behavior.

## Security and review gates

High impact: private-resource authorization, session/token transport, arbitrary run-list input, and query/file surfaces. [Implementation security review](artifacts/2026-10-12_implementation_security_review.md) and [implementation correctness review](artifacts/2026-10-12_implementation_correctness_review.md) close all high/medium code findings; final environment evidence remains pending. Accepted contract ancestor: `d75460acc`. Two independent contract reviews and the required ancestor commit preceded runtime edits under `docs/standards/contract-first-change-standard.md`. [Contract decision](artifacts/2026-10-12_contract_decision.md) records accepted intent and the resolved access matrix.

## Hardening signals and recovery

Prior signatures: combined-viewer HTTP 403 with `Forbidden`, loss/runoff HTTP 404, empty generator HTTP 400. Health means authorized populated maps with numerically verified values; danger means anonymous/private leakage, silent partial maps, cross-run identifier collisions, wrong units, or lost ordinary access. Proposed observation window: deployment smoke plus seven days of existing error monitoring. No temporary bypass is planned. Rollback restores candidate code and only package-created derived files using retained manifests; it must not alter membership or public markers.

## Dependencies, ownership, and documentation

Owner: requesting operator; implementation: Codex on forest. Reviewers must be independent of the relevant change author. Coordinate with [feature access governance](../20261001_feature_access_governance/package.md) without extending its feature-action scope or claiming its milestones complete. The 63 copied runs and a real forest account exercise the member/nonmember transitions. Production rollout still requires an approved window and production-account acceptance.

Applicable authorities include `docs/schemas/feature-access-governance-contract.md`, `docs/schemas/weppcloud-browse-auth-contract.md`, `docs/schemas/weppcloud-csrf-contract.md`, `docs/schemas/output-scope-contract.md`, `docs/schemas/nodb-persistence-concurrency-contract.md`, and `docs/ui-docs/controller-contract.md`; inventory additional query-engine identity contracts before the checkpoint. Promote the bounded collection contract into `docs/ui-docs/contracts/combined-watershed-viewer-contract.md` before implementation. Reconcile `docs/dev-notes/endpoint_security_notes.md` with it.

Scientific parameterization is unchanged; conversions and display defaults are preserved. The bounded UI click-duration change is documented in [ADR-0087](../../adrs/ADR-0087-combined-viewer-pointer-duration.md). Deliverables are the contract/checkpoint, bounded authorization and collection UI, conversion evidence, regression/browser tests, operator recovery instructions, and review/deployment records. Production acceptance remains M5.

Forest operations and later production steps: [user/developer/operator guide](../../dev-notes/combined-watershed-viewer.md) and [rollout handoff](artifacts/rollout-handoff.md).
