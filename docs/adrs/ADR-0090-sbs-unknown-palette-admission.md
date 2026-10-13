# ADR-0090: sbs unknown palette admission

Status: accepted; implemented 2026-10-13. Date: 2026-10-13.

## Decision and rationale

Readable SBS color tables no longer require a recognized burn color for admission. Leave unknown colors unassigned for explicit mapping; preserve known classifications, source masks and existing unassigned export semantics. Do not alter numerical breakpoints, infer burn severity, or relax structural/native failure checks.

The operator selected this behavior in response to the primary onboarding audit. Keeping the prior default/admission policy was rejected because it contradicts that explicit decision. Automatic migration or guessed classifications are outside scope.

## Provenance

Decision venue: repository coding conversation, 2026-10-13 (America/Los_Angeles; exact message time unavailable). Participants: requesting operator and Codex. Decision owner: requesting operator. Implementer: Codex. Evidence: docs/investigations/20261013_primary_onboarding_audit/dispositions.md and docs/work-packages/20261013_onboarding_audit_corrections/artifacts/2026-10-13_contract_decision.md.

## Compatibility, risk and rollback

No persisted schema migration. Validate the changed surface with config readback or native raster artifact/regression checks as applicable. Executable changes can change results; no scientific parity claim is made. Unassigned pixels remain excluded by existing export semantics until assigned; users must inspect assignments. Restore the previous literal/admission conditional to roll back future behavior; do not overwrite saved user choices.
