# Tracker — Staley M3 Soils

## Quick Status

**Started / updated**: 2026-09-09 02:17 UTC
**Phase**: Scaffold ready; implementation not started
**Next milestone**: Audit/acquire soil inputs and draft interval/source contract
**Security impact**: high for planned file/database/acquisition boundaries
**Dedicated correctness and security reviews**: pending execution

## Task Board

- [x] Scope, ExecPlan, fresh-agent handoff, and artifact catalog scaffolded.
- [ ] M1: Audit data readiness, freeze minimal soil fixtures, draft ADR/protocol.
- [ ] M2: Resolve and test interval/component/catchment policies.
- [ ] M3: Implement reproducible offline artifact builder and fixture propagation.
- [ ] M4: Compare SSURGO against original STATSGO on fixed 10 m catchments.
- [ ] M5: Independent reviews, source recommendation, durable docs, closeout.

## Decisions

- **2026-09-09 02:17 UTC** — User requested the M3 soil work package after
  completing terrain tooling and the 10 m recommendation. Reuse that panel;
  isolate soil-source effects rather than repeat terrain-resolution evaluation.
- **2026-09-09 02:17 UTC** — Keep live soil rebuilds and production UI/NoDb/RQ
  changes outside scope. Deliver executable offline derivation and evidence
  without masking unresolved empirical source substitution.

## Discoveries and Risks

At scaffold time, the supplied three 10 m project paths have no `soils/`
directory. The committed WBT terrain fixtures contain no soil cache tables.
Do not assume the earlier existence of `soils.nodb` proves populated horizons.
The fresh agent must inventory available sources and perform any needed bounded
acquisition into a separate study workspace, never silently rebuild live runs.

Source THICK semantics, duplicate/gapped horizons, bedrock designations,
component weights, substitutions, and missing spatial coverage remain open.
Original STATSGO retrieval and metadata still need verification. Fixed-depth
substitution, zero fill, and automatic fallback are not accepted policies.

## Validation and Handoff

Scaffold validation is documentation-only. No soil records were acquired or
modified and no derivation or scientific comparison has run. Start with
[start_here.md](prompts/active/start_here.md); maintain this tracker and the
ExecPlan at each milestone. Record actual input availability rather than
claiming a complete study from synthetic data alone.
