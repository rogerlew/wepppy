# Contract decision: Roads modeled-area response mixture

**Date**: 2026-10-22 UTC  
**Status**: Operator direction approved; final independent checkpoint reviews pending

Starting WEPPpy: `38df23fbf5696b9cc5b5cdbbd6f15fa297a5286e`.
Starting native: `3b630643ba06bd40262285f206112c9d3ee32b21`.

## Authority and normative delta

Roger authorized authoring and implementing the contract across native/WEPPpy,
task-scoped commits, area correction before routing, and expanded modeled footprint.
Latest clarification: keep complete MOFE areas; geographic overlap is unnecessary.
This supersedes geographic-union and boundary-injection proposals.

Canonical authority amended by this checkpoint:

- `docs/schemas/roads-water-accounting-contract.md` (new exact matrix).
- `docs/adrs/ADR-0102-roads-modeled-area-accounting.md` (scientific rationale).
- `docs/schemas/output-scope-contract.md` (derived accounting resource selection).
- `docs/schemas/hillslope-water-aggregation-contract.md` (bounded Roads source rule).
- `wepppy/nodb/mods/roads/specification.md` (PASS construction/report amendment).

For point sources B=max(A-C,0), T=B+C; keep all complete contributors. Replacement
uses summed strip/remainder source areas with baseline excluded and existing
precedence. Continuous areas come from stationary source WAT; single-storm areas
come from native PASS headers. Each product uses represented/source-product area.
Record expansion and serialized source-area differences. No geographic inputs.

Rebuild canonical PASS once before routing, using a Roads weighted strategy that
preserves existing first-header particle semantics. Keep AgFields strict.
Water accounting preserves native terminals and optional source-support weighting.
TotalWatSed Q diagnostics use original profiles. Dedicated marked equivalent WAT
serves average-hillslope reporting with physical Q and canonical IDs. Raw views
remain diagnostic. Corrected readiness and cache fingerprints require ledger/source
provenance, not file existence or timestamps.

## Compatibility, security and regression

Intended scientific behavior change, not a conformance-only fix. Public columns,
units, baseline APIs and AgFields behavior remain. Untouched PASS and baseline
files retain bytes. Legacy raw reports remain historical, not newly certified;
corrected results require reconstruction and fresh routing. No queue/auth changes.

Security impact high for selected source/publication boundaries: review aliasing,
source isolation, staged output behavior, and runtime identity evidence. Dedicated
security and correctness artifacts required. No new service or dependency.

Tests: C<A/C=A/C>A; zero roads; multi-OFE native terminal selection; replacement
remainder and mixed precedence; differing particle headers; missing/empty/legacy
metadata; skipped vs failed runs; malformed dates/area/terminal/schema; optional
absent/empty/partial observations; literal-Q versus physical-Q; cache freshness
with equal timestamps; unchanged baseline; native API and real UM1 fresh routing.
Retain original source hashes and exact prepared PASS/model output/report readback.

## Review disposition

Earlier review findings on area authority, particle headers, replacement T,
optional support weighting, Q meaning and stale geographic documents are addressed
in the current draft. Final independent confirmation is pending. Commit the
checkpoint alone after both reviews; runtime implementation has not begun.
