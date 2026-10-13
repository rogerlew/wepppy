# Tracker — EDDE v2 feasibility

## Quick status

**Started / last updated**: 2026-10-13 21:15 UTC  
**Current phase**: Scoped; ready for an implementation ExecPlan  
**Security impact**: high for planned implementation; dedicated review required before implementation closeout.  
**Plan**: [Package scope and acceptance](package.md). Execution plan to be authored before implementation.

## Task board

### Done

- [x] Record operator scope, package split, spatialization decisions, and review/evidence gates (2026-10-13 21:15 UTC).

### Ready / backlog

- [ ] M1: Author ExecPlan; inventory source records; build bounded client and query command.
- [ ] M2: Retain actual-location coverage matrix, historical quality study, and acquisition benchmarks.
- [ ] M3: Implement and validate single-location CLIGEN and Multiple PRISM workflows.
- [ ] M4: Complete reviews, scientific ADRs, and evidence-based integration disposition.

### In progress

None; this session scopes future work only.

### Blocked

No external blocker established. Data access cost, scientific quality, and CLIGEN mapping remain feasibility questions.

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
