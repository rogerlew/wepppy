# FA-02: Share results without granting feature operation

## Status and authority

Prepared 2026-10-02 UTC against implementation checkpoint `458557219`.
Operator intent is approved in the user-agent conversation. Independent
correctness/security contract reviews passed with zero unresolved findings;
the standalone ancestor commit is pending. Runtime changes
are not part of this checkpoint. M3 remains incomplete and undeployed.

The operator clarified: “the point of the embargo/internal is prevent
unauthorized use. but permitted users may want to share the results more broadly
which should be permitted”. This resolves the reserved result-sharing question.
It authorizes broader result sharing, not making every private resource public.

Canonical authority is the [FA-02 amendment in the feature-access contract](../../../schemas/feature-access-governance-contract.md),
[governance policy](../../../../wepppy/weppcloud/routes/usersum/weppcloud/feature-maturity-and-release-governance.md),
[ADR-0001](../../../adrs/ADR-0001-time-limited-publication-embargo-for-omni-contrasts.md),
[ADR-0080](../../../adrs/ADR-0080-feature-access-governance-amendment.md),
[registry specification](../../../../wepppy/weppcloud/feature_registry/specification.md),
[browse auth contract](../../../schemas/weppcloud-browse-auth-contract.md) and
[RQ response contract](../../../schemas/rq-response-contract.md).
The [query-engine README](../../../../wepppy/query_engine/README.md) and
[feature-access records](../../../dev-notes/feature-access-records.md) explain
implementation status and remaining conformance work. Token provenance, TTLs,
scopes, CSRF, account records and scientific parameterization are unchanged.

## Normative delta and rationale

Discrepancy classification: operator-approved policy amendment. The earlier
checkpoint enforced the then-retained read embargo; it now needs reconciliation
with clarified intent. Earlier findings remain evidence of their original scope.

Internal/publication-embargo labels restrict feature operation. Public retained
results, including contrast/PATH-CE results, are readable under existing
resource/endpoint rules without the originating feature membership. Permitted
users may redistribute/export those results. Sharing grants no restricted
activation, configuration, acquisition, analysis, retry, cancellation or deletion.
Ordinary anonymous functionality stays unchanged.

Private projects, private Batch/Culvert grouped roots, sensitive files and
account/audit records retain their existing access rules. No universal D-Tale
login requirement or new private-sharing credential/UI is introduced. A removed
feature member loses future restricted actions, not the right to read results
that are publicly shared. Private grouped reads retain their separate live
workflow membership requirement; the public Batch exception remains.

Queries, report rendering and export/ZIP packaging of retained outputs are
sharing under existing endpoint authorization. If a report/export actually
executes restricted scientific analysis, gate that operation. PATH-CE execution
still needs PATH-CE permission. Reading retained contrast inputs is not execution
of Omni Contrasts; a composed operation that invokes contrasts needs the latter's
action permission too. No automatic dependency membership is introduced.

This replaces FA-01's feature-derived result embargo, which obstructed the
operator's intended sharing. Output names, contrast ancestry or feature maturity
alone do not justify read denial. Fork/archive/restore/export need no persistent
contrast marker and no blanket contrast-child rejection. Private resource and
filesystem containment remain independently enforceable.

## Bounded implementation surface

After the reviewed ancestor exists, reconcile the M3 checkpoint in these existing
surfaces; no new service, queue, datastore, signing key, token scope or dependency
upgrade is authorized:

- Shared decisions/adapters: `utils/feature_access*.py`, RQ `feature_access.py`
  and `helpers.authorize`. Remove feature-derived read dependencies; retain
  actual restricted-action and private workflow admission.
- Registry/run UI, `run_0`, GL dashboard, Omni/PATH-CE reports and disabled
  action controls: expose retained shared results without enabling actions.
- Browse/download/GDAL/D-Tale launch, files/listings, dedicated downloads,
  query web/MCP, exports and fork/archive routes: remove contrast-only data
  classification/filtering and inherited copy restrictions. Keep existing
  private resource, token, scope, path and sensitive-file checks.
- RQ `feature_results.py`, job routes and orchestration reads: remove
  contrast-only response redaction; preserve normal response/error contracts.
- Tests and operator/user documentation: replace superseded negative read tests
  with positive shared-read plus negative restricted-action/private-read cases.

M3's historical M0 matrix remains source/route inventory evidence. FA-02
supersedes only its feature-derived read/contrast-ancestry restrictions. Keep
that old snapshot and the interim review intact rather than rewriting evidence.

## Review finding disposition to verify

| Prior item | FA-02 disposition |
| --- | --- |
| Fork lineage question | Superseded: no inherited feature-result embargo; no marker/refusal needed. |
| S01 public inspection / S02 explicit configuration errors | Keep compatible behavior; shared result inspection must not depend on feature account lookup. |
| S03 private Batch/Culvert query roots | Retain private resource checks and public Batch exception. |
| S04 SQL effective file access | Public contrast reads are permitted. Review confirms a source-supported private Batch/Culvert-file escape through undeclared SQL expressions; retain as a separate High implementation finding pending bounded reproduction/remediation. No DuckDB upgrade is approved by this amendment. |
| S05 grouped D-Tale/GDAL contrast reads | Retire contrast-only denial; preserve underlying grouped/private resource checks. |
| S06 aria2c contrast listings | Retire contrast-only filtering; preserve sensitive/private file rules. |
| S07 missing polling children | Preserve ordinary missing-child behavior when removing the now-unneeded result projector. |
| S08 cached D-Tale access | Sharing public retained tables is permitted, including after action membership removal. Review confirms private Batch/Culvert tables can enter the same unguarded downstream cache; retain that separate High implementation finding pending bounded reproduction/remediation. |
| S09 legacy contrast child aliases | Remove read/ancestry-only denial. Gate restricted actions actually performed through every alias; preserve normal baseline operations. |
| S10 raw catalogs / copied representations | Retire feature-only result hiding; preserve private/sensitive-source constraints. |

The [interim security review](2026-10-02_m3_security_review.md) remains historical
NOT PASSED evidence. Reclassification is not technical closure. A final M3
review must separately disposition any reproduced private-resource escape.

## Compatibility and regression plan

Public absent/never-used, empty, populated and supported legacy feature states
must render without creating restricted controller state or starting analysis.
Malformed input/path/state keeps its existing explicit failure boundary.

For public populated contrast/PATH-CE results, exercise anonymous readers where
permitted by the existing endpoint, authenticated nonmembers, members and removed
members. Verify listings, raw/catalog data, selectors, reports, query results,
D-Tale representations, byte-correct downloads/ZIPs, forks/restores and recursive
polling remain readable. Preserve existing authenticated-only endpoints.

For restricted actions, exercise anonymous/nonmember/removed/expired principals,
legacy Dev and Root separately, group-only OpenET/Batch/Culvert, acknowledged and
unacknowledged members, and registered service credentials. Denials must precede
writes, external calls, preparation timestamps and enqueues. Test composed
execution separately from queries over already retained inputs.

Verify private ordinary runs, private grouped roots, run/SID claims, revoked and
expired JWTs, root-only files, CSRF and readonly still deny inappropriate access.
A public shared table is a positive case; a private-source SQL/D-Tale escape is
a distinct negative case. Preserve Culvert scope/TTL and ordinary anonymous
creation/edit/model/session behavior. No dependency upgrade or shared account
mutation is needed to validate this documentation checkpoint.

## Independent reviews and checkpoint

The independent [correctness review](2026-10-02_fa02_correctness_review.md) and
[security review](2026-10-02_fa02_security_review.md) assess the prepared contract,
not runtime conformance. Author disposition accepts all wording findings:
registry read entitlement, retained-input dependency language in policy/plan,
and the stale prohibition on formatting retained report artifacts. All three
were corrected in canonical documents and supporting guidance. Both reviewers
independently confirmed closure; the prepared-contract gate passes.

Validation: all 15 changed/new Markdown files passed scoped `wctl doc-lint`;
relative Markdown targets and whitespace checks passed. Spelling previews were
reviewed; existing references to the axe accessibility tool and unrelated prose
were retained. No runtime tests were needed or claimed for this docs-only delta.

Only after review disposition and the standalone ancestor commit may M3 code
reconciliation begin. The prior M3 commit authorization produced `458557219`;
this document does not assert that a new contract commit already exists.
