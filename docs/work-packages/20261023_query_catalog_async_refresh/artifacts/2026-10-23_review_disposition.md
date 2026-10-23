# Contract review disposition

Primary author: Codex `/root`. Date: 2026-10-23 UTC. No production implementation changed. All findings accepted and independently confirmed closed at 2026-10-23 20:20 UTC. Correctness approves checkpoint preparation; security approves contract design. No unresolved findings.

| Finding | Disposition and revised contract section | Verification obligation |
| --- | --- | --- |
| C1 high | Accepted. Reader freshness and caches now mandates targeted receipt/source validation and context reload before producer migration; matrix wave 1 updated. | Existing-membership schema/fs_path/alias changes; no stale immediate report/query. |
| C2 high | Accepted. Recovery and liveness now requires recurring source reconciliation even without receipts, with visible full-cycle progress and capacity gate. | Kill after artifact rename before receipt; convergence without new user action. |
| C3 medium | Accepted. Lifecycle and visibility excludes exactly `_query_engine/refresh/**` from query indexing only. | No maintenance datasets in full/subtree catalog; normal browse/archive retained. |
| C4 medium | Accepted. Publication distinguishes legacy sync best-effort return/errors from strict async acknowledgment/barrier readback. | Malformed asset cases in both APIs. |
| S1 high | Accepted. Publication uses stable external `/wc1/query-engine-coordination/locks/` owner guard, retained lock inode and explicit ordering before existing config/Roads guards. All lifecycle/publish entry points join before migration. | Cross-host NFS exclusion; old-holder/new-inode, restore/delete/recreate races. |
| S2 medium | Accepted. Reserve `query_catalog_refresh_<UUID>` with pre-deserialization classification; fixed sanitized shape and missing/import-failure/recursive/rollback behavior in domain and RQ contracts. | Poll every listed case with no path/request/traceback disclosure. |
| S3 medium | Accepted. Canonical domain and combined-viewer contract cross-link the preserved offline READONLY manifest-owned exception. | Positive offline maintenance and negative generic refresh cases. |
| S4 medium | Accepted. Identity and admission mandates protocol/storage/root/coordination compatibility across eligible shared batch consumers and execution revalidation. | Incompatible companion/off-host consumer blocks admission, retains pending intent. |
| C5 medium (post-fix) | Accepted. Publication defines standalone synchronous local-guard mode outside managed roots/identity, no Redis or /wc1 requirement, and forbids managed-root fallback. | Ordinary tmp directory and rejected managed-root local-mode cases. |
| S5 low (post-fix) | Accepted. Full sanitized shape applies to job-info; successful jobstatus preserves its status-only schema with sanitized errors. | Existing jobstatus success compatibility plus failure redaction. |

## Additional author decisions

- Native GIL release is prerequisite for retained web-serving synchronous scans; async producer migration alone does not protect auto-activation readers.
- Durable immutable receipt sets implement no-lost-update acknowledgment without requiring a cross-store generation increment. Recurring source reconciliation closes the distinct pre-receipt crash gap; its capacity cost is explicit.
- GL flow-duration session rule clarified in its canonical contract: background publication may invalidate a held snapshot; existing reload/refusal semantics remain, with no silent provenance substitution.
- Runtime security and artifact evidence remain pending; reviewed design is not implementation conformance.
