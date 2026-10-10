# FDC-01 independent contract security review

Reviewer: `/root/fdc_contract_security` (dedicated security reviewer).  
Reviewed: 2026-10-10 21:20 UTC.  
Starting implementation revision: `189d10649793f0be1bdae5aeb90e8af9a810d977`.  
Scope: read-only review of the [contract](../../../ui-docs/contracts/gl-dashboard-flow-duration-contract.md),
[ADR-0085](../../../adrs/ADR-0085-gl-dashboard-flow-duration.md), package and
[checkpoint](20261010_contract_decision.md), plus existing route, query and
rendering boundaries. Only this review artifact was authored by this reviewer.

## Findings and disposition

| ID | Severity | Finding and evidence | Required disposition | Status |
| --- | --- | --- | --- | --- |
| FDC-SEC-01 | Medium | Source existence alone does not prove scenario ownership. `query_engine/core.py:355` resolves from `catalog.root`; `_dataset_source_sql` honors entry `fs_path`, and `_resolve_dataset_path` allows parent-run assets. A copied or stale catalog can return baseline values under an Omni label while a child file exists. Query responses carry no physical-source provenance. | Require resolved catalog root to equal the verified scenario root, effective entry path to equal the owned canonical daily source, and escaping paths/symlinks to be unavailable. | Resolved in contract, Execution boundary and valid states. Implementation evidence pending. |
| FDC-SEC-02 | Medium | GL supports `output_scope=roads` under the output-scope contract. Baseline-only FDC without an explicit Roads state could silently compare baseline output inside a Roads dashboard. | Make FDC unavailable with an explanation for Roads context; do not silently substitute baseline. | Resolved in the final paragraph of Execution boundary and valid states. Implementation evidence pending. |

No unresolved high or medium contract findings. The earlier scaffolding-only
statement was removed so execution authority is consistent with the operator's
request and required checkpoint sequencing.

## Security triage and verdict

Security impact is **high** under the repository's public-route and filesystem
boundary classification. The intended surface is additive metadata in the
authorized dashboard route and existing scenario-aware queries, not a new query
endpoint, raw file endpoint, privilege, service or persistence mechanism.

**Pass for the preimplementation contract checkpoint.** This approval permits
implementation after both independent reviews are dispositioned and committed
as an ancestor. It is not a runtime security approval, deployment approval, or
replacement for correctness/UX review. The dedicated implementation security
gate remains required after correctness and QA review.

## Surface review

- Authorization and session behavior remain unchanged: preserve the route's
  `authorize(runid, config)` call and existing Query Engine transport and
  authorization behavior. No credentials, token minting, CSRF exception or
  external network integration are introduced.
- Daily source ownership is narrower than existing Query Engine parent-asset
  allowance. Validate the actual catalog root and effective source, not only
  a logical dataset key. Check containment before reading a catalog reached
  through symlinks. Bootstrap JSON must not expose physical absolute paths.
- Scenario labels, error details and hover values must retain established safe
  text rendering (`textContent`, canvas text, and template JSON serialization).
  Fixed dataset paths and verified numeric outlet identifiers prevent user
  labels from becoming arbitrary file paths or SQL fragments.
- Read-only topology discovery must avoid structure accessors that persist
  generated files. Shared topology metadata may retain existing authorized
  parent-run lineage; daily flow files must belong to the selected scenario.
- Raw daily populations remain complete. Late requests must not replace a
  newly selected source; failed requests are not retained as successful cache
  entries. Reusing cache for presentation changes avoids repeated costly reads.
- Queue, worker, subprocess, dependency, CI, secret and deployment wiring are
  outside this code change. The separately authorized forest restart does not
  justify unrelated topology or runtime identity changes.

## Valid-state noninterference

The contract distinguishes no Omni, a missing optional source, present-empty
source, warm-up-exhausted record, legacy runs without chanwb, and populated
writable/readonly scenarios. Missing one source or invalidating one curve leaves
other valid curves usable. READONLY is not a completion predicate.

An absent catalog is different from a present malformed or mismatched catalog:
existing Query Engine activation may handle absence, without adding writes to
the dashboard GET. A readonly source with a usable catalog remains readable;
an unavailable catalog must receive its concrete availability/query explanation.
Escaping paths, mismatched catalogs and malformed inputs do not gain permission
through these expected-absence rules. Archived data continues to use the
existing restore workflow.

## Required implementation evidence

The final gate must inspect actual code and retain direct, unmocked filesystem
tests for valid writable/readonly sources, missing optional outputs, absent
catalogs, child-file and directory symlink escapes, catalog symlink escapes,
foreign catalog roots, parent/sibling `fs_path` substitution, and a stale entry
despite a present owned file. Prove that unrelated curves and existing graphs
remain usable and Roads does not display baseline FDC data.

Also retain scenario-label output-escaping coverage, a denied run access check,
real authorized browser-to-query integration for both daily sources, and stale
response/cache tests. Keep query bodies scenario-scoped and source-specific;
do not bypass the existing query resolver to satisfy a test.

This contract review executed read-only code and actual catalog inspection.
The example baseline and undisturbed catalogs currently have correct roots
and owned entries for both daily sources; that observation is not evidence for
the hostile cases. No runtime or boundary tests were executed during this
preimplementation review.

## Residual risk and review limits

Bootstrap provenance and page-local caching are snapshots. Replacing outputs or
catalogs during an open page can invalidate that snapshot; the contract requires
reloading after regeneration and explicitly does not promise a query-time
filesystem race guarantee. Existing Query Engine authorization/activation and
parent-asset capabilities remain unchanged and are not certified wholesale by
this bounded review. No unresolved medium/high security risk is accepted for
implementation closeout.

Rain-on-snow is visibly unavailable pending verified classification, avoiding
unsupported scientific filtering. Independent records and shown coverage retain
the operator's performance choice without claiming periods are identical.
