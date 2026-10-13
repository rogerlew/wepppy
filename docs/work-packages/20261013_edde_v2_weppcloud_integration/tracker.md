# Tracker — EDDE v2 WEPPcloud integration

## Quick status

**Started / last updated**: 2026-10-13 21:15 UTC  
**Current phase**: Backlog; gated on feasibility  
**Security impact**: high for planned implementation; dedicated review required before implementation closeout.  
**Plan**: [Package scope and acceptance](package.md). Execution plan to be authored before implementation.

## Task board

### Done

- [x] Record operator scope, package split, spatialization decisions, and review/evidence gates (2026-10-13 21:15 UTC).

### Ready / backlog

- [ ] M1: Accept feasibility handoff; author ExecPlan and contract/state matrix.
- [ ] M2: Wire additive state, eligibility, and climate build orchestration.
- [ ] M3: Add locale-scoped UI and source provenance in reports/downloads.
- [ ] M4: Validate actual projects, legacy behavior, artifacts, reviews, and rollout handoff.

### In progress

None; this session scopes future work only.

### Blocked

Implementation awaits the feasibility package's accepted go/conditional-go disposition and executable workflow evidence.

## Decisions log

**2026-10-13 21:15 UTC — Operator direction, recorded by Codex.** Separate client/data/CLIGEN feasibility from WEPPcloud wiring. Filter by locale and then validate the actual project location; Canada is only partially covered. Require Multiple PRISM where supported by PRISM coverage. Exclude Multiple Interpolated initially because the 12 km grid does not establish useful finer-scale variation; retain this as a scope decision subject to evidence, not a scientific conclusion. Single-location feasibility does not establish PRISM eligibility. See package **Scope and decisions** for the authoritative contract and rationale.

## Risks and open questions

Source completeness and future endpoint, usable domain boundaries, model bias, CLIGEN storm construction, preservation of future signals under PRISM revision, and bounded multidecade acquisition all need retained evidence. Do not resolve these by undocumented defaults or silent fallback.

## Verification

- [ ] Applicable package success criteria and generated-artifact chain passed.
- [ ] Parameterization ADRs accepted before merging affected implementation.
- [ ] Correctness/security review artifacts complete with no unresolved medium/high findings.
- [ ] Required implementation tests and actual-project acceptance recorded.
- [ ] Durable contracts promoted before closure; package and root tracker updated.

## Progress notes

**2026-10-13 21:15 UTC:** Created package and tracker; implementation remains unstarted. Documentation validation is recorded in the planning handoff. No test or artifact acceptance is claimed for future code.

**2026-10-13 22:20 UTC:** Feasibility execution produced a working research client and conditional workflows. Production integration is held on material historical bias, station-derived auxiliary-field validation, CLIGEN quality-guard failures, and PRISM inversions. See the linked feasibility report and package entry gate; no integration work started.

**Operator scope clarification (2026-10-13):** The operator clarified that the application scope is future climate only. Historical EDDE runs are diagnostic baselines for source assessment and future-change checks, not a proposed historical climate method. Existing CLIGEN quality-guard failures and PRN/CLI quantization are known limitations; retain their reporting and current safeguards, but do not require this package to solve them as new integration blockers. This clarification does not approve a bias correction or decide how future auxiliary fields or PRISM temperature inversions should be handled. This supersedes the earlier tracker statement that CLIGEN guard failures themselves block integration. See package **Scope and decisions**.

**Operator PRISM clarification (2026-10-13):** Document inversions as a generic independent-temperature-offset limitation, not a separate EDDE integration blocker. The retained January/December Cascade normal pair shrinks daily range by 0.5 C. Other-dataset occurrence frequency remains unmeasured. Runtime behavior is unchanged; the experimental adapter still rejects affected revisions.

**2026-10-13 23:52 UTC:** Operator requested the dedicated [PRISM temperature-ordering implementation package](../20261013_prism_temperature_ordering/package.md) and accepted ADR-0092 design. All four writer paths and rebuilt-native consumer validation are planned there; this does not expand EDDE application scope or claim the repair is installed.
