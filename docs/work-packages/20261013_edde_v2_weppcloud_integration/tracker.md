# Tracker — EDDE v2 WEPPcloud integration

## Quick status

**Started / last updated**: 2026-10-13 21:15 UTC / 2026-10-14 UTC
**Current phase**: Closed — implementation and environment acceptance complete; not deployed
**Security impact**: high; dedicated correctness/security reviews passed with no open findings.
**Plan**: [Package scope and acceptance](package.md). [Completed ExecPlan](prompts/completed/edde_v2_weppcloud_integration_execplan.md).

## Task board

### Done

- [x] Record operator scope, package split, spatialization decisions, and review/evidence gates (2026-10-13 21:15 UTC).

### Completed milestones

- [x] M1: Accept feasibility handoff; author ExecPlan and contract/state matrix.
- [x] M2: Wire additive state, eligibility, and climate build orchestration.
- [x] M3: Add locale-scoped UI and source provenance in reports/downloads.
- [x] M4: Validate actual projects, legacy behavior, artifacts, reviews, and rollout handoff.

### In progress

None. Implementation and development-environment acceptance are complete.

### Follow-up

Production rollout is separate. The preexisting opt-in WBT conditioning-diagnostics probe still fails; normal broad selection skips it. Retained in the [acceptance report](report.md), without changing WBT behavior.

## Decisions log

**2026-10-13 21:15 UTC — Operator direction, recorded by Codex.** Separate client/data/CLIGEN feasibility from WEPPcloud wiring. Filter by locale and then validate the actual project location; Canada is only partially covered. Require Multiple PRISM where supported by PRISM coverage. Exclude Multiple Interpolated initially because the 12 km grid does not establish useful finer-scale variation; retain this as a scope decision subject to evidence, not a scientific conclusion. Single-location feasibility does not establish PRISM eligibility. See package **Scope and decisions** for the authoritative contract and rationale.

## Risks and open questions

Raw source bias/coarse elevation representation, station-generated auxiliary fields and automatic-seed reproducibility limits remain disclosed. Acquisition/cache ownership, live choices and actual-project eligibility are implemented and validated. Rollback must retain EDDE-aware climate readers/calendar behavior in addition to the capability graph floor; no full rollback deployment was tested.

## Verification

- [x] Applicable package success criteria and generated-artifact chain passed.
- [x] Parameterization ADRs accepted before merging affected implementation.
- [x] Correctness/security review artifacts complete with no unresolved medium/high findings.
- [x] Required implementation tests and actual-project acceptance recorded.
- [x] Durable contracts promoted before closure; package and root tracker updated.

## Progress notes

**2026-10-13 21:15 UTC:** Created package and tracker; implementation remains unstarted. Documentation validation is recorded in the planning handoff. No test or artifact acceptance is claimed for future code.

**2026-10-13 22:20 UTC:** Feasibility execution produced a working research client and conditional workflows. Production integration is held on material historical bias, station-derived auxiliary-field validation, CLIGEN quality-guard failures, and PRISM inversions. See the linked feasibility report and package entry gate; no integration work started.

**Operator scope clarification (2026-10-13):** The operator clarified that the application scope is future climate only. Historical EDDE runs are diagnostic baselines for source assessment and future-change checks, not a proposed historical climate method. Existing CLIGEN quality-guard failures and PRN/CLI quantization are known limitations; retain their reporting and current safeguards, but do not require this package to solve them as new integration blockers. This clarification does not approve a bias correction or decide how future auxiliary fields or PRISM temperature inversions should be handled. This supersedes the earlier tracker statement that CLIGEN guard failures themselves block integration. See package **Scope and decisions**.

**Operator PRISM clarification (2026-10-13):** Document inversions as a generic independent-temperature-offset limitation, not a separate EDDE integration blocker. The retained January/December Cascade normal pair shrinks daily range by 0.5 C. Other-dataset occurrence frequency remains unmeasured. Runtime behavior is unchanged; the experimental adapter still rejects affected revisions.

**2026-10-13 23:52 UTC:** Operator requested the dedicated [PRISM temperature-ordering implementation package](../20261013_prism_temperature_ordering/package.md) and accepted ADR-0092 design. All four writer paths and rebuilt-native consumer validation are planned there; this does not expand EDDE application scope or claim the repair is installed.

**2026-10-14 UTC — Accepted scientific policy:** Use EDDE future precipitation and temperature as provided, with source bias and the 12 km grid's limited representation of local elevation effects disclosed. Bias correction and additional elevation/lapse-rate correction are outside scope. Retain the established CLIGEN hybrid: station-generated storm structure/intensity, radiation, wind and dewpoint, with explicit field attribution. The operator accepts this precedented approach; deriving projected auxiliary fields is not an entry requirement. Existing unit conversion, PRN/CLI quantization, quality guards and optional Multiple PRISM spatialization (including ADR-0092 ordering repair) remain in scope and unchanged. Scientific method decisions are settled; integration remains unstarted. PRISM ordering repair is now completed and validated in its separate package, superseding the earlier progress notes. The unrelated SBS broad gate remains explicitly open; actual Canadian-project acceptance and operational decisions belong to integration.

Policy-update validation: scoped Markdown lint passed for all nine changed documents; no executable code changed and no runtime tests were required. Existing spelling suggestions outside the changed prose remain untouched.

**2026-10-14 UTC — Feasibility handoff complete:** The stale SBS assertion is corrected against the existing upload contract; 21 metadata-route tests pass. Feasibility closed with conditional-go and explicit broad-suite coverage limits. No remaining scientific correction/auxiliary-field study is required. Author the integration ExecPlan and contracts before runtime work; retain full-suite and actual U.S./Canadian acceptance gates.

**M1 checkpoint (2026-10-14 UTC):** Contract ancestor `75b47f61f`; standalone reader floor `26c9e86ca`. Four additive US/Canada ordinary/single-input structures registered; all 18 older entries unchanged. Capability suite passes 79 tests after updating exact catalog-count/hash expectations. No live writer exposure yet.

**M2/M3 and live acceptance (2026-10-14 UTC):** Runtime, API discovery, UI, reports and operator documentation implemented. Canadian Single and US Multiple PRISM builds passed real acquisition through authenticated RQ requests. Canadian full WEPP completed: 53 prepared CLI hashes and 53 parsed water-balance outputs match 2060 daily precipitation. US 83 prepared climates match publication; full WEPP awaits missing source-project soil setup. Five hostile/invalid requests return 400 without changing climate state or published CLI bytes; unauthenticated submission is rejected. Reader-floor reopen passes eight cases. Frontend 980 tests, lint, stubtest and stub inventory pass; latest targeted Python run passes 97 tests. Broad Python suite and final artifact/review gates remain open.

**M4 consumer/archive acceptance:** Canadian Single (53 hillslopes) and US Multiple PRISM (83 hillslopes) now complete full WEPP job trees after finishing the previously unbuilt US soil and landuse inputs through existing APIs. Every prepared CLI matches publication; every parsed daily water-balance output has 366 finite rows and matching 2060 precipitation. Browser downloads match exact local bytes. Canonical archive/restore preserves 104 completed-case and 117 failed-case climate members, including attempt directory mode 0700. Live Canadian PRISM rejection preserves prior publication. Actionable EDDE errors now identify projection, period or scaling corrections.

**Final reviews:** Both independent reviews pass runtime `d2ca5821b` with no unresolved findings. Security independently reran 59 focused tests. Successful rebuild preserves all 100 prior completed/failed attempt files. Only the broad Python gate and final documentation closeout remain.

**Final audit amendment:** Preserve published simulation length and active CLI calendar across failed period changes. Live request2061–2062/input_years99 retained published2060/one year/hash. Focused regressions:62 passed. Broad initial run:2,783 passed/48 skipped/one stale ag-fields default assertion, corrected against ADR-0089; complete affected module:34 passed. Segmented broad continuation excludes only previously completed files and remains running. Original failed run remains failed.

**Closeout (2026-10-14 UTC):** Final default-selection continuation: 2,813 passed, 4 skipped in 310.65 seconds. Normal broad-suite coverage is complete across recorded segments; all encountered default-suite failures have passing corrected-module reruns. This is not one uninterrupted full-suite pass. The unrelated opt-in real-WBT conditioning-diagnostics failure remains unresolved and is retained as a follow-up. No production deployment. Actual 136-hillslope WEPP readback, browser and archive acceptance, both reviews, published-calendar correction and rollback-reader distinction are documented in the report. Durable contracts reside in EDDE-WEPP-01 and the user/operator guide.
