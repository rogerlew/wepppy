# PRISM spatialization temperature ordering

**Status**: Closed 2026-10-14 UTC (2026-10-13 Pacific) — implemented and development-stack validated
**Timezone**: UTC

## Overview

Independent PRISM monthly offsets can produce daily Tmin above Tmax. Implement the operator-accepted midpoint repair in every current spatialization writer, preserving valid daily values and existing non-temperature behavior. This is a generic PRISM correction; EDDE future-climate experiments supplied the initial reproducible failures.

The operator authorized execution after planning. All four writers and the targeted native extension are implemented and validated. The [implementation report](report.md) records acceptance, exact artifact identities and gate limitations; deployment remains separate.

## Decision and scope

[ADR-0092](../../adrs/ADR-0092-prism-temperature-inversion-midpoint-proposal.md) owns the scientific decision and rationale. Apply existing monthly offsets first. For finite adjusted extrema, if Tmin > Tmax set both to `Tmax / 2 + Tmin / 2`; otherwise preserve the pair. Do not invent a positive minimum range, swap extrema, redistribute the correction to other days, or change monthly offsets. Preserve the arithmetic midpoint before serialization; disclose existing output rounding and small monthly-mean changes. Do not label that midpoint a measured daily mean.

Implement the same behavior in these paths:

| Repository | Writer | Consumer |
| --- | --- | --- |
| wepppyo3 | `cli_revision/src/lib.rs:rust_cli_revision` | WEPPcloud daily Multiple PRISM via `wepppyo3.climate.cli_revision` |
| wepppy | `wepppy/nodb/core/climate_build_helpers.py:cli_revision`, breakpoint branch | WEPPcloud breakpoint Multiple PRISM |
| wepppy | `wepppy/climates/prism/__init__.py:prism_revision` | Public Python revision API |
| wepppy | `wepppy/climates/edde/cligen.py:revise_prism` | Experimental EDDE revision, currently rejects inversions |

Include focused regression tests, build/release provenance for the affected native module, existing workflow correction diagnostics, and developer/operator documentation. Reuse a narrow Python numerical helper where useful; keep daily production transformation in owned Rust.

Exclude new EDDE application integration, bias correction, changes to radiation/wind/dewpoint/storm fields, CLIGEN guard or rounding redesign, precipitation changes, automatic existing-project rebuilds, infrastructure changes, and deployment. Historical source climates may be regression fixtures; EDDE application scope remains future only.

## Compatibility and artifact plan

Preserve import paths, function arguments/returns, NoDb keys, climate file columns, dates, and public error contracts. No project-data schema migration is planned. For valid adjusted extrema, output must match the same writer before the patch; compare non-temperature content against that writer's existing serialization rather than the unserialized source. An invalid source climate is distinct from an inversion introduced by spatialization: preserve existing validation and never silently repair malformed or nonfinite inputs.

Surface correction count, maximum inversion, and maximum temperature adjustment through existing workflow logs. Reuse the EDDE `.prism.json` manifest for additive repair provenance and rounding/mean-change metrics, without removing current keys. Define exact optional fields and legacy-manifest handling in the contract checkpoint before code changes. Retain a visible per-output `.temperature-ordering.log` beside each climate, with working/completed status, because process stdout is not reliably captured by project logs. This is a bounded diagnostic file, not a new storage mechanism. Do not create hidden artifacts or change Rust public returns.

Existing projects remain unchanged until an ordinary requested climate rebuild. In a scratch project, trace the generated `.cli` through the normal copy/preparation into `wepp/runs/`, compare exact hashes and parsed content, run WEPP, and read the fresh user-facing climate/output artifacts. Retain controls, source normals, source/binary identities, generated/consumed hashes, diagnostics, and failures in the package evidence or normal visible climate directories.

## Complexity budget

Reuse existing PRISM equations, NumPy, Rust/PyO3 writer, CLIGEN parser/serializer, climate orchestration, and WEPP fixtures. Permit only the bounded temperature projection, shared Python helper if needed, tests, diagnostics, and the affected native build artifact/provenance. No new dependency, service, queue, datastore, protocol, permissions, or Python replacement for the Rust path. The simplest candidate already repaired all retained failures; any broader change requires evidence that it misses a real acceptance condition.

## Milestones

### M1 — Contract checkpoint

Follow the [completed ExecPlan](prompts/completed/prism_temperature_ordering_execplan.md). Read both repositories' nearest guidance. Record source revisions, affected contracts, exact behavior and diagnostic deltas, compatibility plan, scope/security triage, and regression matrix in `artifacts/<date>_contract_decision.md`. Promote a generic spatialization contract under `docs/schemas/` and amend the EDDE contract and ADR-0091's former no-clamping/inversion-rejection language precisely for this accepted rule. Do not waive other guards. Obtain the two independent read-only reviews required by the contract-first standard, disposition findings, and commit a standalone contract ancestor before editing NoDb-coupled implementation. This planning commit is not that reviewed checkpoint.

### M2 — Matched Rust and Python implementation

Implement the repair in all four writers with identical finite-value ordering semantics and meaningful diagnostics. Retain the owned Rust daily path and existing breakpoint layout/records. Add analytical and serialized regression coverage before refreshing the native extension. Verify all callsites; merely adding a helper is not completion.

### M3 — Native build and consumer validation

Use the existing wepppyo3 build/release process and update `docs/release-provenance.md` and `docs/module-registry.md`. Identify source commit, toolchain, build command, artifact hash, and the extension actually imported by the development container. Refresh only the affected climate extension through the canonical mechanism; do not assume a source checkout is the loaded binary. Run Rust tests, Python parity tests, real breakpoint/daily writers, the 24 retained revisions, and fresh WEPP executions. Include at least one non-EDDE source climate to demonstrate generic behavior. Record before/after native-writer timings on the same representative fixture; no new performance threshold or architecture change is implied.

### M4 — Review and handoff

Complete correctness review using the repository template, close medium/high findings, run required gates, and update package/tracker/ExecPlan and durable documentation. Report implemented, wired, locally/environment validated, and deployed as separate claims. A known unrelated regression may be recorded as a limitation; do not silently turn a failed broad gate into a pass. Deployment and affected-project repair remain separate work.

## Success criteria

- [x] Reviewed contract ancestor and accepted ADR precede implementation.
- [x] All four writer paths implement the rule; valid/equal pairs remain unchanged.
- [x] Positive/negative temperatures, narrow/large inversions, month boundaries, rounding ties, nonfinite input, and invalid-source states have meaningful coverage.
- [x] Daily and breakpoint serialization preserves ordering; non-temperature fields and valid days match the corresponding unpatched writer.
- [x] Rust/Python numerical behavior agrees; unavoidable serializer tie differences are measured and cannot yield inverted output. No claim of byte-identical serialization across different preexisting writers is required.
- [x] All 15 retained inversions are corrected; 21 previously accepted revisions retain their numerical content; the three repaired 20-year climates pass WEPP with exact consumed-input evidence.
- [x] Actual scratch-project build uses the rebuilt extension, persists/reloads required state, prepares the corrected climate in `wepp/runs/`, and yields fresh parsed outputs under the development stack's configured identity/mounts/umask.
- [x] Correction provenance, monthly drift, and historical/future signal effects are measured and visible. Candidate measurements are reference observations, not universal numerical thresholds.
- [x] Focused tests, Rust tests, API/stub checks, docs lint, full-suite disposition, correctness review, and binary provenance are retained.

## Review and operational boundaries

**Parameterization change**: yes. **ADR required**: yes; [ADR-0092](../../adrs/ADR-0092-prism-temperature-inversion-midpoint-proposal.md), accepted and development-stack conformance verified.

**Security impact**: low; bounded numerical arithmetic and existing artifact/log paths, with no new egress, parser format, authorization, queue, or subprocess interface. **Dedicated security review required**: no under current scope. Contract reviews and correctness review must check noninterference and binary provenance. Re-triage if scope introduces new boundaries. Do not spawn reviewers merely because this package exists; the contract standard's explicit independent-review requirement applies at M1 execution.

**Stakeholders**: operator/scientific decision owner; WEPPpy climate and NoDb maintainers; wepppyo3 climate maintainer; contract/correctness reviewers.

This is a permanent targeted correction, not a temporary retry/fallback layer. The existing EDDE blanket inversion rejection is retired only after the bounded repair and generated-artifact checks pass; unrelated rejection conditions remain. Health signals are zero post-repair inversions, unchanged valid days, finite WEPP output, and explicit correction counts. Danger signals include altered precipitation/auxiliary weather, broad daily-range changes, hidden nonfinite repair, stale extension loading, or changed build performance. Observe these over the complete acceptance matrix; any production monitoring window belongs to a later deployment plan. Revert paired Python/Rust changes and restore prior EDDE rejection if regression evidence requires rollback; retain diagnostics.

## Dependencies and evidence

Depends on the [EDDE feasibility evidence](../20261013_edde_v2_feasibility/report.md#follow-up-proposed-prism-inversion-repair), not on completion of EDDE application integration. The [EDDE integration package](../20261013_edde_v2_weppcloud_integration/package.md) can consume the corrected writer once validated; this package does not resolve its other future-weather decisions.

Candidate commit `3a455437d` validated 24 revisions, repaired 15 days, and passed three fresh 20-year WEPP runs. Largest per-extreme correction was 0.25 C before serialization; maximum individual calendar-month mean change was 0.00968 C. These are prototype results, not implementation acceptance. Source archives, scripts, hashes, and exact consumed files remain in the feasibility package.

**Current delivery**: matched Rust/Python writers, tests, native release refresh, visible diagnostics and retained consumer evidence. **Highest supported claim**: implemented, wired and development-stack validated; not deployed. Contract ancestor `7bd7707c2`, native source `d3e51c2`, native release `0515272`. Broad-suite and typing/tooling limitations are dispositioned in [report.md](report.md), not counted as passing gates.

## M1 review amendments

Native stdout/module logging is not reliably captured in project climate.log. The smallest retention correction is the per-output visible log specified in the canonical contract, published and archived with its climate; this supersedes the initial logs-only assumption. Verify real canonical archive/restore and browser/download access for complete and failed examples. Preserve the existing Historic PRISM downstream dewpoint floor on the repaired Tmin; writer-level auxiliary preservation does not prohibit that existing downstream effect.

## Closure

Independent final correctness/artifact review passes with no open findings. Focused tests pass 80, Rust tests 23; the retained 24-case study and real 200-hillslope scratch project pass exact generated-to-consumed checks and seven fresh WEPP runs. Paired native timing medians differ by about 0.9%. Full-suite disposition retains the unchanged SBS metadata failure. Deployment, source-project repairs, EDDE application integration and the observed same-process cache-lifecycle investigation remain separate follow-up work. Durable rules are in ADR-0092 and the canonical temperature-ordering contract.
