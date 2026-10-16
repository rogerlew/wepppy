# ADR-0095: Preserve strict least-cost breach through the terrain helper

Status: accepted for implementation, 2026-10-16 UTC.

## Decision and rationale

When `derive_flow_stack` receives `breach_least_cost` with `blc_fill=false`,
forward `blc_fail_on_unresolved=true` to the emulator. Previously the helper
omitted the flag, selecting the emulator's false default and producing
artifacts rejected by the existing diagnostics validator. Other conditioning
modes and existing distance/cost/fill defaults remain unchanged.

This restores the existing [diagnostics contract](../schemas/wbt-conditioning-diagnostics-contract.md),
which requires no fallback filling and failure on unresolved depressions.
Do not relax diagnostics or silently enable filling to make integration pass.
No new configuration setting is necessary.

## Alternatives

Skipping the real WBT tests hides a confirmed runtime defect. Permitting
unresolved depressions or weakening diagnostics changes the accepted terrain
contract. Adding another user-facing flag duplicates the existing strict choice.

## Provenance and evidence

Venue: repository operator/Codex conversation, 2026-10-16 UTC.
Participants: Roger Lew and Codex. Owner: existing diagnostics contract;
implementation correction authorized by the operator's CI failure repair request.
Implementer: Codex. Hosted run 38825109720 exposed two failing real WBT tests
when selected individually; the broad suite normally skips their opt-in path.
Focused correction passes both tests and the helper unit test with real WBT
artifacts and unchanged diagnostics validation.

## Risk and rollback

Inputs with unresolved depressions now fail at the WBT boundary rather than
later diagnostics rejection. No successful fallback artifacts become accepted.
Revert the helper forwarding change if parity fails, retaining diagnostics and
recording the unsupported helper path; do not suppress the integration tests.
