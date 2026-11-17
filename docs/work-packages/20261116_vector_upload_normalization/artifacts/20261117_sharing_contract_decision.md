# Sharing and copy accounting contract checkpoint

Starting source: `0ba4be47b`. Operator reply on 2026-11-17:
“that's on the original owner if they make it public or add team members.
I don't see an problem here”. This explicitly resolves the discussed new-owner
fork finding; ordinary authorized public/team forks may inherit all project
records. The proposed exclusion of originals from copies is rejected.

Canonical delta: `docs/schemas/vector-upload-normalization-contract.md`,
“Sharing, copies, and existing workspace resets”. Direct source browsing/download
restrictions, parser confinement, quarantine no-interpretation, original bytes,
source SHA and existing authentication/CSRF remain unchanged. Public/team copy
permission is the bounded exception; it is not new anonymous direct-download
permission. Reclassify privacy finding VUN-CORRECTNESS-RESUME-01 / SEC-RESUME-01
as resolved by operator-approved policy, not an implementation exploit to fix.

Remaining conformance work: physical copied bytes inside the configured run
filesystem need quota admission and exact accounting; existing reset/removal
semantics need the durable accounting lifecycle. Existing original-upload actor and source provenance stay unchanged. Additive
`retention_actor` attributes physical copied bytes to the verified copy initiator
(or existing unattributed bucket for legacy/automated callers), preventing a
public copier from exhausting the source uploader's principal budget. Copied
receipts cannot claim fresh upload or conversion. Offline profile exports are outside this run-filesystem ledger;
reentry into a managed workspace is charged. No numeric defaults, services,
queues, identities, mounts, or destructive user workflow options change.

Compatibility/regression plan: absent, empty, terminal, malformed, active and
legacy source/destination states; all five retained roots; source originals and
canonical inputs preserved; authorized public/team copy bytes retained;
quota rejection before destination mutation; exact source/destination/principal
readback; unrelated reservations preserved; partial copy/removal and retry;
managed reentry from an offline snapshot. All confirmed consumers are mapped in
`20261117_vector_retention_copy_reset_inventory.md`. Independently review this
checkpoint before the accounting implementation; no rollout/publication allowed.

Security checkpoint disposition: COPY-ACCOUNTING-01 is addressed by distinct
copy-charge attribution, without changing original actor provenance, thresholds
or access. Reconciled terminal incomplete evidence remains copyable. External
exports require an explicit existing call-site boundary, never missing-config
fallback.
