# FA-02 sharing contract security review

## Metadata

- Reviewer: `/root/contract_security`, 2026-10-02 UTC; independent read-only
  contract and supporting source review. Only this artifact was written.
- Base: `45855721906bb40ea26195a5ae8b20daa3f6d116`; reviewed prepared documentation
  changes and the [FA-02 checkpoint](2026-10-02_fa02_sharing_checkpoint.md).
- Authority: the operator's explicit clarification that internal/embargo status
  prevents unauthorized feature use while permitted users may share results
  broadly, recorded in the checkpoint and
  [canonical contract](../../../schemas/feature-access-governance-contract.md).
- Scope: governance/ADRs, canonical access/browse/polling contracts, registry
  specification, query README, records guide and active package/ExecPlan.
- The [earlier M3 review](2026-10-02_m3_security_review.md) is unchanged. It
  assessed FA-01 and remains evidence of that policy and implementation state.

## Security Triage Decision

Security impact: **high**; dedicated review required. FA-02 deliberately removes
feature-derived result confidentiality, while retaining restricted operation
and actual resource privacy. Treating the removed confidentiality rule as still
mandatory would contradict the operator's authority. Treating all private data
as implicitly published would also exceed that authority.

The threat model distinguishes publicly shared output, retained data in a
private resource, and an operation that runs a restricted feature. Existing
identity, token scope/resource, expiry/revocation, session, CAP, readonly,
CSRF and sensitive-file checks remain independent of feature maturity.

## Findings

| ID | Severity | Surface | Finding and evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| FA02-S01 | Low | Canonical rendering rule | The initial `docs/schemas/feature-access-governance-contract.md:154` prohibited regenerating "protected artifacts" in inspect-only views, whereas `:91,168` permitted formatting/rendering retained results. The stale wording could preserve an unintended report/export gate. | Author replaced the artifact-based prohibition with the ban on optional feature initialization and restricted scientific execution. Reviewer independently confirmed the corrected text and retained formatting/cache permission. | Resolved |

No unresolved **documentation conflict** remains: High **0**, Medium **0**, Low
**0**. The two source-supported
implementation findings below remain separate from this contract verdict.
No risk acceptance is proposed or recorded.

## Authority and Boundary Assessment

The revised policy consistently permits public retained contrast/PATH-CE state,
reports, raw data, catalog entries, exported bundles and cached representations
under existing endpoint/resource rules. Neither absent feature membership nor
later removal retracts public shared results. Existing authenticated-only
endpoints remain authenticated-only. The amendment introduces no sharing UI,
credential, private-resource public switch or universal D-Tale login.

Restricted activation, configuration, acquisition, analysis, retry, finalization,
cancellation and deletion still require action entitlement. HTTP method or a
report/export label cannot excuse restricted execution. Formatting, querying,
packaging or copying retained results does not itself execute the originating
restricted feature. PATH-CE needs its own action permission; contrast action
permission is additionally required only when the composed operation actually
activates/executes contrasts, not merely when it consumes retained inputs.

Private Batch/Culvert access still requires the corresponding live workflow
membership and applicable resource/token checks. The public Batch exception and
registered Culvert service path remain explicit. A group or copied result does
not grant unrelated private-run access. Feature-only public-read gates may be
removed without removing these private-resource checks.

No contrast lineage marker or contrast-child fork prohibition is necessary for
FA-02. Source and destination retain their actual resource rules; restricted
operations at either destination remain gated. Ordinary baseline modeling is
not forbidden because its inputs or run ancestry originated from a contrast.

The polling amendment removes only contrast/PATH-CE membership-based redaction.
It preserves the existing polling admission modes and ordinary result/error
contracts. It does not authorize a new global private-job authentication policy;
existing sensitive-data exclusions and sanitization remain applicable.

## Reassessment of the M3 Findings

The absence of a feature-derived result embargo removes the public-contrast
exploit premise for S04 and S08. It does **not** remove their independently
identifiable private-resource paths:

| Retained implementation issue | Source-backed private-resource path | Required bounded follow-up |
| --- | --- | --- |
| M3-S04, High: SQL effective-source containment | `query_engine/payload.py:114–163` accepts computed SQL; `core.py:343–358` inserts expressions; `executor.py:35–49` permits external file reads. `app/feature_access.py:69–81` authorizes declared dataset sources only. A scalar `read_parquet` expression over a private Batch/Culvert file can accompany an ordinary authorized declared dataset, bypassing the private workflow-root check. | Reproduce with synthetic private/public files through the actual request/executor boundary, retain the separate issue, and agree the smallest compatible remediation. Preserve public queries and valid expressions. FA-02 does not authorize a DuckDB upgrade. |
| M3-S08, High: cached private D-Tale data | `webservices/dtale/dtale.py:192–200` explicitly loads Batch/Culvert sources; `:186–189` derives deterministic dataset IDs; `:1072–1099` serves cached rows without caller/resource admission. Only `/internal/load` checks its internal token. `docker/caddy/Caddyfile.wepp1:193–206` exposes the downstream UI/data routes. A private table loaded by an authorized caller remains reachable by another caller at its dataset URL. | Reproduce with a synthetic private dataset, including removed membership and downstream representations; settle conditional private-resource handling while preserving shared public tables. Merely opening the existing viewer is not a new authorized private-to-public sharing operation. No universal login or service-authentication redesign is approved here. |

These are source findings, not claims of a successful production exploit.
This reviewer made no runtime requests against private data and did not run a
new exploit harness in this documentation task. A changed public read policy is
neither technical remediation nor acceptance of actual private-source leakage.
The checkpoint and plan correctly require separate reassessment and preserve
the requirement to close Medium/High issues before implementation closeout.

Disposition of the other earlier items is consistent with FA-02: preserve S01
public-read independence, S02 explicit configuration failure, S03 private
workflow-root admission and S07 missing-child compatibility. Retire S05/S06/S10
contrast-only data hiding. For S09, remove ancestry-only admission but retain
checks for restricted operations actually invoked through legacy/composite
aliases. Earlier tests must be revised by behavior, not simply deleted until
the suite becomes green.

## Surface Checks

- **Valid states/UX:** the checkpoint explicitly covers absent, empty, populated
  and legacy views, plus anonymous/nonmember/member/removed shared readers and
  malformed input. Optional views cannot initialize restricted controllers.
- **Auth/session/CSRF:** no claim identity, accepted token class, TTL, revocation,
  resource, CSRF or account authority is broadened. Current private-workflow
  membership and operation acknowledgment remain; group changes stay auditable.
- **Secrets and sensitive files:** sharing does not include credentials,
  Root-only paths, account details or audit reasons. No secret was accessed or
  introduced by this review.
- **Files/artifacts:** shared outputs need no feature taint or inherited marker.
  Existing path containment and actual resource privacy remain. Byte-correct
  downloads and archive/restore are explicit acceptance requirements.
- **Queues/subprocesses:** new restricted admissions remain gated before writes,
  preparation, external requests or enqueue. Existing admitted-job completion,
  ordinary polling and error contracts are preserved.
- **MCP/integrations/network:** query scopes and run limits remain additive;
  Culvert operation and returned browse credentials remain separate. Neither
  service redesign nor deployed credential renewal follows from this amendment.
- **Supply chain:** dependency versions are unchanged; no DuckDB upgrade is
  approved. A private-source remedy needs its own bounded evidence and review.
- **Integrity/observability:** no migration, account mutation or history rewrite
  is proposed. Prior review evidence is retained; shared outputs stay visible
  through established tools under their resource rules.

## Verdict

- **Prepared contract gate:** **pass**; FA02-S01 is resolved and there are no
  unresolved contract findings.
- **M3 implementation gate:** remains **NOT PASSED**. Runtime reconciliation,
  private-source findings, final independent review and production-equivalent
  service/browser evidence are outstanding.
- **Recommendation:** record independent review disposition before the
  standalone FA-02 ancestor commit. That checkpoint
  permits the already scoped reconciliation; it is not deployment, dependency
  upgrade, service-authentication redesign or security-risk acceptance.

## Validation Evidence

Reviewed the prepared diff, checkpoint, unchanged token/session contracts and
supporting query/D-Tale source. No runtime code was edited. No application test,
service deployment, account mutation or production data read was performed.
`wctl doc-lint --path` passed for this artifact: one file, zero errors/warnings.
The `uk2us` preview returned no changes.

## Residual Risk and Sign-off

- Accepted residual risks: none.
- Security reviewer: `/root/contract_security`, 2026-10-02 UTC; contract-only
  verdict as stated above.
- Package owner: root orchestrator to retain separate implementation findings
  and link this review from the checkpoint/tracker. FA02-S01 closure was
  independently confirmed before this final contract verdict.

## Artifact Observability Gate

The proposed correction improves access to shared retained artifacts instead of
creating hidden-only output or silently incomplete ZIPs. Real output, download,
archive/restore and browser evidence remain implementation acceptance gates.
This documentation review proves policy consistency, not generated-artifact
correctness or deployed enforcement.
