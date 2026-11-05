# ADR-0133: Per-OFE native water coefficient ownership

Date: 2026-11-02

Status: Accepted; native ownership implemented at `b581352b6`, with bounded
consumer, full-history and application readback evidence. Deployment excluded.

## Decision and provenance

Decision venue: Codex repository session, 2026-11-02, America/Los_Angeles.
Participants present: requesting repository operator and Codex. Decision owner:
the operator, through the request for a contract-first native implementation fix
and revision of undeployed `wepp_261029`. Implementer: Codex.

Store and consume FC and HK by layer and OFE. Preserve the existing FC/HK formulas,
constants, domain guard, retention defaults and initialization schedule. This is
an ownership correction, with numerical consequences, not parameter retuning.
The selected release already sizes PMET by plant-definition capacity and maps
EVAPPM through `itype(nowcrp,iplane)`; verify those contracts rather than changing
working code to address an older checkout's defects.

## Rationale and alternatives

S01 observed OFEs 1/2 consuming OFE3's coefficients under both retention policies.
Correct producer files cannot repair native shared-array ownership. Keeping the
shared arrays, capping producer scenarios to six, switching retention defaults or
requiring homogeneous materials would either leave the defect or impose unrelated
behavior. Recomputing all coefficients every call would change initialization
semantics and is outside this correction.

## Evidence and consequences

The [native coefficient contract](../schemas/native-mofe-coefficient-contract.md)
and [MIPA-02 checkpoint](../work-packages/20261102_mofe_input_producer_audit/artifacts/20261102_native_contract_decision.md)
define required before/after evidence. Historical S01 coefficient discrepancies
are not measured hydrograph corrections. Quantify fresh runoff, drainage, storage
and ET changes before release; disclose unresolved physical/calibration limits.

## Risk and rollback

COMMON layout changes require a clean matched executable rebuild. Preserve old
binaries, sidecars and outputs; never mix regenerated hill passes with an older
watershed executable. Roll back the entire matched pair if gates fail. Historical
projects remain unchanged. Revision6 is a local undeployed same-name revision;
no production deployment or default switch is authorized.
