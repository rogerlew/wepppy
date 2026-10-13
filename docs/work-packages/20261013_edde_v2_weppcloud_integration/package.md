# EDDE v2 WEPPcloud integration

**Status**: Backlog — feasibility recommends holding production integration (2026-10-13)
**Timezone**: UTC

## Overview

Expose a validated EDDE v2 future-climate method in WEPPcloud after the [feasibility package](../20261013_edde_v2_feasibility/package.md) establishes a usable client, scientific assumptions, and executable CLIGEN/WEPP workflows. Integration must make model, scenario, period, location eligibility, and spatialization explicit while preserving existing climate workflows.

## Scope and decisions

The operator clarified that the application scope is future climate only. Historical EDDE runs are diagnostic baselines for source assessment and future-change checks, not a proposed historical climate method. Existing CLIGEN quality-guard failures and PRN/CLI quantization are known limitations; retain their reporting and current safeguards, but do not require this package to solve them as new integration blockers. This clarification does not approve a bias correction or decide how future auxiliary fields or PRISM temperature inversions should be handled.

The operator's 2026-10-13 decision is to separate data/workflow feasibility from application integration. The feasibility package's **Scope and decisions** section governs scientific and spatial scope until its accepted contracts are promoted. Locale-level method availability is the first filter; per-project validation against the selected grid, required locations, and available records is mandatory. Neither locale membership nor a bounding rectangle is proof of eligibility.

Offer the validated single-location workflow and Multiple PRISM where PRISM coverage and the feasibility evidence support it. Multiple Interpolated is outside the initial scope because finer spatial detail is not established for the 12 km source. Show explicit explanations for unavailable methods or spatializations; do not silently switch modes. Preserve the distinction between historical model simulations, future projections, and observations.

## Feasibility handoff (2026-10-13)

The [feasibility report](../20261013_edde_v2_feasibility/report.md) demonstrates a reusable extraction client and successful experimental CLIGEN/WEPP paths, but recommends holding general production integration. Remaining decisions concern the interpretation of raw future projections, attribution/validation of station-derived auxiliary weather, and documentation of generic PRISM daily temperature inversions. The operator directed that inversions be documented rather than treated as a separate EDDE integration blocker; current adapter rejection behavior remains explicit. Known CLIGEN guard and quantization behavior is retained, not a new blocker. Independent correctness/security reviews passed for the standalone research implementation. Exact current source availability is narrower than the registry summary: NorESM has SSP2-4.5 only, through 2079; MPI has both scenarios through 2099. Locale candidates are `us`, `canada`, and separately evaluated legacy `bc-ca`; none is enabled by the feasibility change.

## Entry gate

Implementation starts only after an accepted go or conditional-go disposition identifies supported locale/model/scenario/period/spatial-mode combinations and remaining limitations. Require client API and error contracts, generated CLIGEN/WEPP evidence, acquisition measurements, scientific ADRs, and provenance fields. A conditional-go permits only combinations whose required evidence passes. A no-go leaves this package deferred.

Before implementation, author `prompts/active/edde_v2_weppcloud_integration_execplan.md` using `docs/prompt_templates/codex_exec_plans.md`; read nearest AGENTS instructions and `docs/standards/contract-first-change-standard.md`. Update authoritative UI/data contracts before coupled production code. No method enum value, default model/scenario/period, or locale identifier is reserved by this planning document.

## Milestones

### M1 — Contracts and additive state

Map validated client inputs into climate capability/catalog and locale configuration, NoDb state, API request/response validation, and report provenance. Inspect `wepppy/nodb/core/climate.py`, `climate_build_router.py`, and adjacent build services, plus `wepppy/weppcloud/controllers_js/climate.js` and applicable route/RQ contracts. Identify exact catalog and locale owners during discovery. Publish a field/error/state matrix covering absent, empty, populated, legacy, and hostile inputs. Write a compatibility and regression plan before state/schema edits; retain existing keys, enum values, defaults, and legacy run behavior.

### M2 — Build and eligibility wiring

Reuse the feasibility client and climate adapter in the existing climate build orchestration. Enforce selected-model grid eligibility and requested records on the server before expensive acquisition, and validate all locations required by the chosen spatialization. Distinguish unsupported locale, out-of-domain project, missing source records, missing PRISM coverage, and retrieval errors. Preserve NoDb locking, cancellation/supersession, cache guards, and the canonical RQ response contract. Invalidate eligibility/results when location, source selection, period, or spatial mode changes.

### M3 — UI and reporting

Add accessible controls only for validated model/scenario/period choices and supported spatial modes. Scope presentation by locale while retaining server authority. Explain partial Canadian coverage and separate PRISM eligibility. Make selected source, model, scenario, period, generation method, and bias/spatial-revision assumptions inspectable in reports and downloads. Verify switching to/from existing climate modes and reopening older projects.

### M4 — Actual-project acceptance and handoff

Use eligible U.S. and Canadian projects, an out-of-domain project, and projects with/without PRISM coverage. Exercise UI submission through durable state, live worker acquisition, generated climate, hillslope assignment, WEPP execution, and report/download readback. Validate single-location and Multiple PRISM, stale requests, unavailable records, and mode switching. Retain exact candidate revision and production-equivalent identities, groups, mounts, umask, configuration, and orchestration. Deployment is a separate recorded action after acceptance; a passing job status alone is insufficient.

## Complexity budget

Reuse existing climate clients/adapters, capability/configuration ownership, routes, NoDb, RQ workers, and reports. Permit additive integration into those mechanisms; no new service, queue, datastore, daemon, dependency, privilege, or deployment topology. Retain an actual failed simpler acceptance test and operational/recovery costs before any escalation. No redesign of other climate modes, Canada-wide coverage promise, or silent bias correction.

## Success criteria and generated artifact gate

- [ ] Feasibility entry gate met and accepted contracts promoted outside closed work packages.
- [ ] Locale presentation and per-project/per-location server eligibility agree, including Canadian and PRISM-negative cases.
- [ ] Only validated source combinations and Single/Multiple PRISM choices can build; unsupported selections return clear contract-compliant errors.
- [ ] Saved selections reload correctly; actual source records, normalized intermediates, exact CLIGEN/WEPP inputs, fresh outputs, and displayed/exported provenance agree.
- [ ] Generated files in the run and `wepp/runs/` carry the correct scenario/period and hillslope climate assignments, demonstrated through semantic readback and fresh execution.
- [ ] Existing runs, defaults, switching behavior, access checks, and prior climate methods pass regression coverage.
- [ ] Focused tests, `wctl run-pytest tests --maxfail=1`, `wctl run-npm lint`, and `wctl run-npm test` pass. Run stub gates for changed API surfaces; update `wepppy/rq/job-dependencies-catalog.md`, run `wctl check-rq-graph`, and inspect live job trees if queue wiring changes.
- [ ] Actual-project acceptance, independent correctness/security reviews, affected user/operator/developer docs, and rollback guidance complete; no open medium/high findings.

Follow `docs/standards/generated-artifact-validation-standard.md`; report implemented, locally validated, environment validated, and deployed separately. Record missing evidence instead of overstating completion.

## Parameterization and security gates

Reuse accepted feasibility ADRs without changing formulas or scientific defaults. Any additional parameterization, conversion, threshold, or fallback requires an ADR before merge under `docs/standards/parameterization-adr-standard.md`.

**Security impact**: high; **dedicated security review required**: yes. Routes, worker execution, downloaded files, and egress are in scope. Create `artifacts/<date>_security_review.md` using the security template and a separate correctness artifact. Preserve run access, session/CSRF, path safety, locks, and serialization safeguards. This planning change has no runtime effect.

**Stakeholders**: operator/scientific decision owner; climate, NoDb, RQ, frontend, and reporting maintainers; independent correctness and security reviewers during implementation.

## Dependencies and current outcome

- **Depends on**: [EDDE v2 feasibility](../20261013_edde_v2_feasibility/package.md).
- [Tracker](tracker.md).
- Canonical references: `docs/schemas/rq-response-contract.md`, `docs/schemas/nodb-persistence-concurrency-contract.md`, `docs/schemas/weppcloud-csrf-contract.md`, and `docs/schemas/climate-parquet-lineage-contract.md`.

Backlog scope only. Nothing is implemented, wired, validated in a running application, or deployed.
