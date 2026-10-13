# ADR-0089: agfields wepp 261010 default

Status: accepted; implementation pending. Date: 2026-10-13.

## Decision and rationale

New projects using ag-fields.cfg change [ag_fields] bin from wepp_260714 to wepp_261010. Existing persisted selections and historical parent fallback are unchanged. Align current help and onboarding with that selection; do not claim the old executable corpus results validate the new release.

The operator selected this behavior in response to the primary onboarding audit. Keeping the prior default/admission policy was rejected because it contradicts that explicit decision. Automatic migration or guessed classifications are outside scope.

## Provenance

Decision venue: repository coding conversation, 2026-10-13 (America/Los_Angeles; exact message time unavailable). Participants: requesting operator and Codex. Decision owner: requesting operator. Implementer: Codex. Evidence: docs/investigations/20261013_primary_onboarding_audit/dispositions.md and docs/work-packages/20261013_onboarding_audit_corrections/artifacts/2026-10-13_contract_decision.md.

## Compatibility, risk and rollback

No persisted schema migration. Validate the changed surface with config readback or native raster artifact/regression checks as applicable. Executable changes can change results; no scientific parity claim is made. Unassigned pixels remain excluded by existing export semantics until assigned; users must inspect assignments. Restore the previous literal/admission conditional to roll back future behavior; do not overwrite saved user choices.
