# FA-02 runtime reconciliation security review

## Metadata and authority

- Reviewer: `/root/contract_security`, independent security reviewer, 2026-10-02 UTC.
- Base: accepted FA-02 ancestor `102c810667f56ea0339b204ed3528eddecdc2944`; reviewed the uncommitted reconciliation.
- Scope: shared evaluator/adapters, retained Flask views, browse/download/GDAL/D-Tale launch, query dataset admission, exports, fork/archive, polling and cancellation. Production source review only; no deployment or private-data requests.
- Authority: [feature-access contract](../../../schemas/feature-access-governance-contract.md) and [FA-02 checkpoint](2026-10-02_fa02_sharing_checkpoint.md).
- Related evidence: [runtime correctness/UX review](2026-10-02_fa02_runtime_correctness_review.md), [FA-02 contract security review](2026-10-02_fa02_security_review.md), and the unchanged [historical M3 security review](2026-10-02_m3_security_review.md).
- Reviewer write scope: this artifact only. No runtime, account, credential, dependency or environment changes.

## Findings

Line references identify the reviewed working snapshot and may move during disposition.

| ID | Severity | Evidence and consequence | Required action | Status |
| --- | --- | --- | --- | --- |
| M3-S04 | High | `wepppy/query_engine/payload.py:114–163`, `core.py:343–358`, and `executor.py:35–49` permit caller expressions to perform undeclared external file reads. `app/feature_access.py:59–65` checks declared logical and physical dataset sources, not every source reached by SQL. An ordinary declared dataset can therefore accompany an expression reading private Batch/Culvert files outside its authorization. | Retain separate synthetic private-source reproduction and a bounded, reviewed remedy that preserves valid public queries. FA-02 authorizes public contrast reads, not unrelated private reads or a dependency upgrade. | Open; carried forward independently of result sharing |
| M3-S08 | High | `wepppy/webservices/dtale/dtale.py:186–200` assigns deterministic dataset IDs and supports private grouped sources. `:1072–1099` serves loaded rows without current caller/resource admission; only the internal load boundary checks its service token. Caddy exposes downstream D-Tale routes. An authorized private-table launch can leave cached rows available to another caller. | Retain private-dataset reproduction and resolve conditional private-resource handling, including downstream representations, without imposing a universal login on shared public tables. Launching a private viewer is not an authorized private-to-public publication action. | Open; carried forward independently of result sharing |
| FA02-RS01 | Medium | The new cancellation task loop passed every `node.runid` to project-context loading. Culvert dispatcher/finalizer jobs enqueue `args=[culvert_batch_uuid]` with batch metadata (`culvert_routes.py:579–586,736–742`); `wepppy/rq/job_info.py:105–120` reports that bare UUID as `runid`. `rq_engine/feature_access.py:46` then attempts ordinary Ron project resolution, so a valid registered-service cancellation can fail. Batch root/finalizer jobs likewise use a bare batch name. | Preserve feature admission but omit fabricated Ron context for batch-level dispatcher/finalizer identifiers. Keep actual composite child-run context. Cover producer-shaped valid service/human cases and restricted-action denial. | Resolved: source fix independently confirmed at `job_routes.py:519–523`; owner reports 59 passing jobinfo cases, and independent correctness review records 84 passing route/helper cases |

The author corrected RS01 during this review: Batch/Culvert task identifiers
without a composite run delimiter now use context-free feature admission.
Composite child run IDs still supply their actual context. The same feature
decision runs for human and integration callers; this is not a new service
exemption. Four producer-shaped regression cases were added at
`tests/microservices/test_rq_engine_jobinfo.py:837`.

No additional action, private-resource or sensitive-file bypass was identified
in the reviewed removal of feature-derived result gates. This bounded statement
does not close S04/S08 or establish complete M3 acceptance.

## Security triage and verdict

- Security impact: **high**; dedicated review required because authorization and delivery boundaries change.
- Overall M3 security gate: **NOT PASSED**. Unresolved findings: High **2**, Medium **0**, Low **0**. RS01 is resolved; no risk acceptance is recorded.
- Bounded reconciliation review: no unresolved new concrete security finding after RS01 disposition. This does not close the carried-forward private-source findings.
- Release recommendation: **hold M3 completion and rollout**. This review does not replace correctness, UX, artifact, browser or service acceptance.

The controlling distinction is between executing a restricted feature and
sharing retained output under existing resource rules. Public contrast/PATH-CE
data, catalogs, archives, reports and cached tables need no originating feature
membership. Actual private projects/grouped roots, sensitive files, token
resources/scopes, CSRF and existing endpoint restrictions remain independent.

## Surface checks and source conclusions

| Surface | Reviewed conclusion and practical limit |
| --- | --- |
| Shared decisions and identity | Public `inspect` returns existing-read admission without account lookup. Action checks retain group-only versus role-or-group composition, live identity/membership, acknowledgment, readonly and capability checks. Required configuration validation remains. Token minting/parsing/provenance is not changed by this delta. |
| Restricted execution and cancellation | Direct restricted execution guards remain. PATH-CE keeps its own action guard while reading retained contrast inputs. The corrected cancellation classifier covers OpenET, AgFields, contrast/PATH and workflow tasks, then checks retained restricted descendants before invoking cancellation. Ordinary baseline operations on contrast-child paths are intentionally permitted. Correctness review RC01 records the original omission and its separate disposition. |
| Optional/public retained state | Omni report now uses `tryGetInstance` and a not-generated response for absence. `Omni.contrasts_report` delegates to `omni_artifact_export_service.py:489`, which reads retained parquet and formats the report; this path does not execute contrast analysis. PATH status/results use retained optional state. Public readonly/backend mismatch does not itself bar retained reads. |
| Private grouped transports | `browse/auth.py:436–520` retains token class, identifier binding, applicable service groups, session marker, live workflow membership and Root-only checks. The public Batch exception remains explicit. Query `require_root` retains grouped-root admission for resolved aliases and logical/physical catalog sources. S04 remains the separate undeclared-source limitation. |
| Delivery and sensitive paths | Deleted browse/GDAL/D-Tale/export/download helpers classified contrast origin only. Existing root authorization, traversal/containment, hidden/Root-only path checks, range handling and endpoint restrictions remain in the inspected source. Removing bundle/catalog contrast classification is intentional sharing, not authority to include unrelated private files. S08 remains downstream of D-Tale launch. |
| Fork/archive and aliases | Removed checks tested contrast content or ancestry. Existing project/token/lifecycle and path checks remain. No inherited result marker is needed; restricted operations still require their actual action permission. |
| Polling and errors | Removing contrast/PATH projection preserves ordinary result/error/queue payloads and `None` children. Existing polling admission remains; this change does not introduce a global private-job authentication rule. Sensitive-data protections outside the removed contrast projector remain separate requirements. |
| Secrets, integrations and supply chain | No new signing key, scope, TTL, dependency, network service, credential or deployment change in this delta. Culvert token expiry is unchanged. No secrets were inspected or retained during this review. |
| Integrity and concurrency | No scientific formula, artifact schema, NoDb lock or group-history transaction changed. Cancellation side effects remain in the existing implementation; this review is not a new comprehensive queue-race audit. |
| Logging and recovery | No new logging/exfiltration mechanism observed in the removals. Current 5xx/configuration behavior remains separate from shared-read permission. Runtime is uncommitted and undeployed; production recovery was not exercised. |

## Validation and observability evidence

Independent review traced removed helper definitions/callers and searched
production/tests for stale `feature_access_data`, `project_job_results`,
`require_data_access`, `contrast_decision`, `visible_data` and
`consumes_contrasts` references; none remained. Reviewed tests cover public
retained queries, private grouped roots, ordinary child aliases, unprojected
polling including missing children, restricted cancellation denial and the
RS01 producer-shaped contexts. Source/test inspection is not execution proof.

No application tests or exploit harness were run by this reviewer in this
bounded task. Earlier M3 counts do not prove this amended snapshot. Post-fix
evidence supplied by other reviewers/author is explicitly attributed:

- Package owner: **59 passed** for jobinfo after the batch-context fix, including
  its producer-shaped cases; **275 passed** across focused delivery/export tests.
- Independent correctness reviewer: **84 passed** across
  `test_feature_access_data.py`, `test_rq_engine_jobinfo.py` and
  `test_omni_bp_routes.py`. That artifact records the command and test-double
  limits; these overlapping runs are not additive coverage totals.
- Package owner reports synthetic reproduction of S04 through actual
  `run_query` after declared-dataset admission: an anonymous public query read
  the private Batch parquet canary. For S08, the actual D-Tale internal loader
  admitted a synthetic private Batch CSV, and a fresh anonymous client received
  the canary from `/dtale/data/<id>` with HTTP 200. No shared user data was used;
  retained reproduction evidence is being recorded separately by the owner.
- Reviewer artifact validation: documentation lint passed with zero errors and
  warnings; spelling-normalization preview and `git diff --check` were clean.

No full-suite pass is claimed. Full regression, byte-correct output delivery,
live browser and production-equivalent service acceptance remain outstanding.

Artifact observability: the inspected changes restore ordinary visibility of
retained data, manifests, catalogs and results through established tools. They
add no hidden lineage record. This review did not generate scientific artifacts,
perform an archive/restore byte-equality round trip or publish a private table.
The highest supported claim is source-level reconciliation review plus the
explicit finding dispositions above, not output or deployment acceptance.

## Residual risk and sign-off

No private-source leakage risk is accepted. Public retained-result sharing is
the operator's intended behavior, not an exception to private-resource rules.
S04/S08 need independent technical disposition; code removal alone cannot close
them. Group-only authority, single-maintainer audit administration, and deferred
PowerUser sanctions retain their accepted scope.

Cancellation preflight and stopping do not share one atomic job-tree snapshot.
The correctness review records the dispatch-window limitation; no supported
ordinary dispatcher adding a differently governed restricted task was identified
in this bounded review. This remains an explicit concurrency coverage limit,
not a reproduced new bypass or authorization to redesign cancellation.

Security reviewer: `/root/contract_security`, 2026-10-02 UTC. Package owner must
link this artifact and record final evidence/disposition before M3 closeout.
