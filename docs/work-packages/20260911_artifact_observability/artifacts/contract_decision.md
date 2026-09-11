# Observability amendment

Base: 4305972a6. Operator explicitly requests installing an enforceable rule and
making post-fire intermediate artifacts user-facing and archivable. Authorization
includes correcting existing hidden records in addicted-reservist and the required
checkpoint. No legal conclusion about FERPA is asserted.

Canonical changes: artifact-observability standard; root AGENTS pointer; shared
contract-first and review gates; production_m1.md attempt layout, failure retention,
and explicit storage migration. Existing browser authentication/archive machinery
is reused; no global hidden-path bypass or secrets disclosure. Scope is a faithful
storage migration and artifact-retention fix, not model changes.

Implementation: production.directory visible attempts, visible retained dNBR and
publication work, migration helper + audit, filesystem/failure/archive tests.
No changes to formulas, numerical parameters, rainfall, terrain, or soil policy.
No queue topology or output schema changes. Root accepted results stay in place.

Compatibility: exact original metadata backed up visibly; binary rasters/tables
unchanged; path references and dependent JSON hashes rebased; NoDb signatures
updated under its lock. Only the exact known pre-change engine fingerprint may
be upgraded for these recorded storage-only changes. Unknown fingerprints stay
stale. No automatic read-side migration, hidden alias or symlink fallback.

State matrix: never used no-op; new/working/failed/completed all visible; valid
legacy migrated with provenance; mixed trees/active work rejected before mutation;
malformed historical diagnostics retained verbatim; altered accepted sources must
not become trusted by migration. Failure keeps visible migration status/backups.

Acceptance: direct unmocked writer/migration/retention/archive-restore tests;
byte checks for scientific payloads; current-state preservation for the known
engine; browser input/intermediate/failure/download evidence under normal worker
identity. Full Python suite remains on operator hold. No production fleet rollout.

Review clarifications: amend dnbr_upload.md, README/specification and local bundle
contracts; persist per-attempt receipts/error diagnostics, including historical
unknown status when no receipt survives. Migration uses the existing admission/
lifecycle lease, NoDb lock, ACTIVE-state and associated/active-RQ-job checks.
Add a dedicated artifact-observability CI guard through the existing forest
workflow generator, running real writer/failure/migration and archive tests.
