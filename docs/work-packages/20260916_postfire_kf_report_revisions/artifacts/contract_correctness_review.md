# Correctness and user-experience contract review

## Metadata and scope

- Reviewer: independent `contract_correctness` agent, 2026-09-16 UTC.
- Starting revision: `5f98c577a8cc0dfe5cb0be78f40c231a0d0c8a18`.
- Scope: checkpoint decision, ADR-0068, canonical `docs/kf_source.md`, report
  amendment, linked M1/M3 compatibility and feature/control amendments, source
  policy and retained original aggregation metadata.
- This is a pre-implementation contract review. No production changes or runtime
  acceptance are claimed. Security review and final implementation review are
  separate gates.

## Findings

| ID | Severity | Evidence and required action | Status |
| --- | --- | --- | --- |
| COR-01 | Low | The initial checkpoint and ADR still described absent delegation/commit authority despite the owner's explicit continuation. Record the latest authorization and preserve scaffold restrictions only as dated history. The author's concurrent amendment now does so in `20260916_contract_decision.md`, Authority, scope and rationale, and ADR-0068, Execution research. | Resolved by readback during review |
| COR-02 | Low | `wepppy/nodb/mods/postfire_debris_flow/docs/kf_source.md`, UI, feature registry and queue obligations, originally omitted the owner's observed temporary controller disappearance. Required amendment: removing RUSLE leaves postfire enabled and visible immediately, after the first reload, and after subsequent reloads. The author added this case to the Kf, control and feature contracts and required both frontend propagation and registry metadata changes. | Resolved by post-fix readback |

No high or medium correctness/compatibility finding was identified.

## Source and numerical assessment

The retained original `source-evidence/ussoils-original.xml` contains the
aggregation source: layer-thickness weighting, exclusion of missing-layer
thickness, component-percentage weighting, missing-component renormalization,
and final -0.1 missing sentinel. Its KFFACT and PERM fields are distinct. The
proposed policy reflects these procedures and consumes the already aggregated
product rather than reconstructing it. The standalone `setussoils.sas` file is
a retained failed HTTP response; it was not used as the aggregation oracle.

The retained independent comparison reports exact float32 agreement for
301,379 cells across two regions. This supports the stated field interpretation,
not an upstream metadata correction, contemporary survey accuracy, or historical
probability parity. The contract preserves that distinction, customary units,
nearest-neighbor alignment and a common support mask. No scalar calibration or
unrecorded fallback is authorized.

Schema 3 is additive; v1/v2 retain POLARIS labels and freshness. New M1 excludes
unrelated RUSLE/POLARIS/WEPP Soils fingerprints. Accepted source identity remains
the recorded snapshot without a network currentness probe. Failed replacement
preserves the accepted bundle; rollback does not claim old software reads v3.

Post-fix review also includes the new Concrete interfaces and advisory projection
section: explicit production Kf selection preserves default offline callers;
the accepted NoDb/Redis soil-policy projection dispatches legacy and Kf task
freshness independently. Unknown policy cannot claim completion, M3 rules are
preserved, and the advisory projection cannot replace local artifact validation.
Implementation coverage must test both a fresh Kf acceptance and a subsequent
failed attempt so the projection still describes the prior accepted result.

The curve uses accepted predictors and the scalar engine, retains negative/zero
response semantics, and bounds sampling to 101 uniform points plus at most four
design points and one P50 point. Unit conversion is presentation-only. Arithmetic
failure is explicit and does not discard usable saved tables. Rainfall origin
comes from the accepted snapshot; dates alone cannot create observation claims.

## Valid-state and input assessment

| State | Contracted outcome | Evidence obligation |
| --- | --- | --- |
| Optional source/module absent | Local read remains usable; Run creates attempt-owned preparation | Direct absent-state read and normal Run |
| Empty or partial attempt | Never accept incomplete preparation; preserve evidence and allow a new attempt | Writer/failure and retry boundary |
| Complete source | Validate policy, grid, hashes and common-mask mean before acceptance | Real raster and publication checks |
| Supported legacy acceptance | Read old values/provenance without rewrite; source-specific freshness | Real v1/v2 bundle checks |
| New attempt fails | Keep prior accepted identity and report usable | Failed-replacement hash comparison |
| Malformed/hostile artifacts | Explicit bounded failure; no overwrite or silent substitution | Independent security review and unmocked boundaries |
| Accepted predictors unavailable | Curve unavailable; otherwise valid saved sections remain usable | Unavailable predictor regression |
| Accepted identity replaced | 409 rather than mixed tables, curve or export | Race test and browser behavior |
| Archive/restore | Visible inputs, partial records and provenance preserve their bytes | Normal archive member/hash verification |

Separate input dimensions include schema/policy, source identity mutation, units,
grid, support availability, duration, rainfall origin, zero/negative response,
eligibility/read-only changes, and assessment pinning. The checkpoint enumerates
these dimensions sufficiently for implementation; this review does not claim
exhaustive executable coverage.

## Verdict and residual risk

Contract design gate: pass. Open findings: high 0, medium 0, low 0. Both low
findings were resolved during independent review; no additional scientific
mechanism is needed. Post-fix confirmation: 2026-09-16 UTC.

Implementation release remains unapproved until direct transport/filesystem/
publication/archive checks, generated-output propagation, browser/export/reload
checks and the named forest restart plus nervous-mesquite run succeed. The
research windows are not substitutes for the two required real basin workflows.
Numerical and transport behavior, immediate menu synchronization, and production
process freshness remain untested at this checkpoint.
