# Tracker — EDDE v2 feasibility

## Quick status

**Started / last updated**: 2026-10-13 / 2026-10-14 UTC
**Current phase**: Closed — conditional-go handoff; stale SBS test corrected
**Security impact**: high for planned implementation; dedicated review required before implementation closeout.  
**Plan**: [Package scope and acceptance](package.md). [Completed ExecPlan](prompts/completed/edde_v2_feasibility_execplan.md).

## Task board

### Done

- [x] Record operator scope, package split, spatialization decisions, and review/evidence gates (2026-10-13 21:15 UTC).

### Ready / backlog

- [x] M1: Author ExecPlan; inventory source records; build bounded client and query command.
- [x] M2: Retain actual-location coverage matrix, historical quality study, and acquisition benchmarks.
- [x] M3: Implement and validate single-location CLIGEN and Multiple PRISM workflows.
- [x] M4: Complete reviews, scientific ADRs, and evidence-based integration disposition.

### In progress

M1–M3 executed: 120 model-years, 657,450 point-days, 69 successful full-period WEPP runs, and 59 pilot runs. Ten CLIGEN and three full-period PRISM rejections remain explicit. M4 independent correctness/security findings resolved; 25 focused tests pass.

### Blocked

No remaining feasibility blocker. The SBS expectation was stale relative to its existing contract and is now corrected; all 21 metadata-route tests pass. The original broad run failed and its continuation remains incomplete, not passing. Raw-projection and hybrid policies are accepted and PRISM repair is complete. Actual Canadian-project acceptance belongs to integration; see report.

## Decisions log

**2026-10-13 21:15 UTC — Operator direction, recorded by Codex.** Separate client/data/CLIGEN feasibility from WEPPcloud wiring. Filter by locale and then validate the actual project location; Canada is only partially covered. Require Multiple PRISM where supported by PRISM coverage. Exclude Multiple Interpolated initially because the 12 km grid does not establish useful finer-scale variation; retain this as a scope decision subject to evidence, not a scientific conclusion. Single-location feasibility does not establish PRISM eligibility. See package **Scope and decisions** for the authoritative contract and rationale.

## Risks and open questions

Measured coverage, endpoint, quality, acquisition, and generated-artifact evidence are in report.md and indexed archives. Scientific policies are accepted in ADR-0091. Actual Canadian-project acceptance remains integration work; no undocumented defaults or silent fallback are authorized.

## Verification

- [x] Applicable feasibility criteria and generated-artifact chain complete; broad-suite coverage limitation explicitly dispositioned.
- [x] Parameterization ADR-0091 records accepted research transformations and deferred production policies.
- [x] Correctness/security review artifacts complete with no unresolved medium/high findings.
- [x] Research implementation tests and artifact acceptance recorded; actual application acceptance transferred to integration.
- [x] Durable experimental contract promoted; package and root tracker updated.

## Progress notes

**2026-10-13 21:15 UTC:** Created package and tracker; implementation remains unstarted. Documentation validation is recorded in the planning handoff. No test or artifact acceptance is claimed for future code.

**2026-10-13 21:56 UTC:** Initial planning committed `03435abc5`. Live inventory limits NorESM SSP2-4.5 to 2079 and shows no NorESM SSP3-7.0. Topanga sampled cells are ocean-mask exclusions. Daily precipitation matches same-labeled hourly sums within 1.22e-6 mm over 465 point-days. Pilot: 19 focused tests pass, 59 fresh WEPP cases pass, one PRISM temperature inversion rejected. Full suite and multi-year studies remain running.

**2026-10-13 22:40 UTC:** Operator continued after the pending independent-review request. Correctness and security reviewers identified invalid PRISM source acceptance, companion provenance overwrite, and ambient netrc authentication; guards and regression coverage now address them. Added 36 seasonal PRISM wet-day/extreme comparisons. Planning commit remains `03435abc5`; implementation/evidence committed as `5dd665305` after both independent reviews passed. Study execution is complete, package remains open only for declared gates.

**Operator scope clarification (2026-10-13):** The operator clarified that the application scope is future climate only. Historical EDDE runs are diagnostic baselines for source assessment and future-change checks, not a proposed historical climate method. Existing CLIGEN quality-guard failures and PRN/CLI quantization are known limitations; retain their reporting and current safeguards, but do not require this package to solve them as new integration blockers. This clarification does not approve a bias correction or decide how future auxiliary fields or PRISM temperature inversions should be handled. See package **Scope and decisions** and report **Scope clarification**.

**Operator PRISM clarification (2026-10-13):** Document inversions as a generic independent-temperature-offset limitation, not a separate EDDE integration blocker. The retained January/December Cascade normal pair shrinks daily range by 0.5 C. Other-dataset occurrence frequency remains unmeasured. Runtime behavior is unchanged; the experimental adapter still rejects affected revisions.

**PRISM patch investigation (2026-10-13):** Operator requested a patch approach. Evaluated midpoint projection only on inverted adjusted extrema against all 24 retained revisions; 15 days repaired, 21 previously successful revisions unchanged, three fresh 20-year WEPP executions passed. Production daily spatialization uses Rust wepppyo3; Python breakpoint/public PRISM and EDDE paths also need coordinated implementation. See proposed ADR-0092 and the candidate evaluation artifacts. No production formula changed.

**2026-10-13 23:52 UTC:** Operator requested the dedicated [PRISM temperature-ordering implementation package](../20261013_prism_temperature_ordering/package.md) and accepted ADR-0092 design. All four writer paths and rebuilt-native consumer validation are planned there; this does not expand EDDE application scope or claim the repair is installed.

**2026-10-14 UTC — Accepted scientific policy:** Use EDDE future precipitation and temperature as provided, with source bias and the 12 km grid's limited representation of local elevation effects disclosed. Bias correction and additional elevation/lapse-rate correction are outside scope. Retain the established CLIGEN hybrid: station-generated storm structure/intensity, radiation, wind and dewpoint, with explicit field attribution. The operator accepts this precedented approach; deriving projected auxiliary fields is not an entry requirement. Existing unit conversion, PRN/CLI quantization, quality guards and optional Multiple PRISM spatialization (including ADR-0092 ordering repair) remain in scope and unchanged. Scientific method decisions are settled; integration remains unstarted. PRISM ordering repair is now completed and validated in its separate package, superseding the earlier progress notes. The unrelated SBS broad gate remains explicitly open; actual Canadian-project acceptance and operational decisions belong to integration.

Policy-update validation: scoped Markdown lint passed for all nine changed documents; no executable code changed and no runtime tests were required. Existing spelling suggestions outside the changed prose remain untouched.

**2026-10-14 UTC — Closed:** Identified SBS failure is stale test coverage from pre-EDDE contract/implementation commits `b4be200b4`/`69cfd68aa`. Corrected the single expected string; full metadata-route module passes 21 tests. [Disposition](artifacts/20261014_sbs_test_disposition.md) preserves original failed/incomplete broad results without claiming a complete suite pass. Scientific policy, retained climate/WEPP evidence and independent reviews support conditional-go handoff. No production change or deployment. This closure supersedes earlier open-gate progress notes.
