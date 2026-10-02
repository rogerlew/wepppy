# FA-02 runtime correctness and user-experience review

## Metadata and scope

- Reviewer: `/root/contract_correctness`, independent review, 2026-10-02 UTC.
- Base: accepted FA-02 ancestor `102c81066`; reviewed the uncommitted runtime reconciliation and its tests.
- Authority: [feature-access contract](../../../schemas/feature-access-governance-contract.md), especially Authorization composition, UI and backend obligations, and Protected-data classification and mixed delivery; [FA-02 checkpoint](2026-10-02_fa02_sharing_checkpoint.md).
- Scope: shared evaluator/adapters, Flask retained views, browse/download/GDAL/D-Tale launch, query dataset admission, export/fork/archive admission, polling and cancellation, and changed tests.
- Related review: [historical M3 security review](2026-10-02_m3_security_review.md). M3-S04 and M3-S08 remain separate open private-resource findings; this review does not close them.
- Write scope: this artifact only. No implementation, account, credential or deployment changes by this reviewer.

## Findings

Line references identify the reviewed working snapshot and may move during disposition.

| ID | Severity | Evidence and consequence | Required correction | Status |
| --- | --- | --- | --- | --- |
| FA02-RC01 | High | Initial `wepppy/microservices/rq_engine/feature_results.py:4` classified only contrast/PATH execution; `job_routes.py:515` checked only the root before recursive cancellation. OpenET, AgFields and restricted descendants could therefore miss feature admission. The omitted families predated FA-02. | Exact task-name classification now covers the six governed families, and `cancellation_nodes` checks every retained descendant before calling `cancel_jobs`. Direct/nested negative route cases pass; ordinary contrast-child ancestry remains allowed. Concurrency limitation below is separate from this fixed snapshot-coverage defect. | Closed on source readback and focused regression |
| FA02-RC02 | Medium | Initial `wepppy/weppcloud/routes/nodb_api/omni_bp.py:267` called `Omni.getInstance` for absent optional state, yielding an internal error; report tests retained obsolete role-only denials. | `tryGetInstance` now returns an explicit 404 `results_unavailable` response for absent state. Positive reads across roles, CAP/resource denials and the absent-state route case pass. | Closed on source readback and focused regression |
| FA02-RC03 | Medium | Initial `wepppy/weppcloud/templates/user/feature_access.html:14` and `templates/user/_internal_access.html:12` required separate contrast access merely to read PATH inputs. | Both views now distinguish retained input reads from actual contrast execution. | Closed on source readback |

## User outcome and valid states

Authorized users may share retained results under ordinary project/resource rules. Recipients gain no restricted action permission. The inspected removal of contrast-only classifiers, inherited ancestry checks and result projection implements that distinction without changing scientific formulas or artifact schemas.

| State | Valid? | Expected behavior | Evidence and limit |
| --- | --- | --- | --- |
| Public feature absent or never used | Yes | Show unavailable results without feature initialization or analysis | PATH status/results use optional state; Omni report now returns explicit `results_unavailable` for missing optional state |
| Empty or populated public contrast/PATH results | Yes | Read retained data without originating feature membership | Evaluator, report/status/results, browse/export and query source readback; existing empty Omni report stub; endpoint/content acceptance remains incomplete |
| PATH member without contrast membership | Yes | Execute PATH using retained contrast inputs; deny actual contrast execution | Updated real-PostgreSQL evaluator tests inspect this separation; no fresh execution evidence independently run here |
| Anonymous/nonmember/removed member | Yes | Shared reads remain available; restricted actions denied | Public inspect bypasses account lookup; feature action guards remain; direct/nested cancellation denial passes with feature admission stubbed |
| Public readonly or unsupported current backend | Yes | Retained reads remain available; relevant actions retain restrictions | Evaluator returns existing-read admission before action capability checks |
| Ordinary operation on legacy contrast-child alias | Yes | Preserve baseline operation and resource checks | Updated helper tests cover GET/POST composite and `pup` aliases; no live fork/restore roundtrip claimed |
| Private Batch/Culvert resource | Yes, with existing permission | Keep live grouped-read membership, resource/token rules and public Batch exception | Query root and catalog-source tests remain; known SQL-expression/D-Tale cache escapes remain separately open |
| Missing child in a polling tree | Yes | Preserve the ordinary response shape | Exact single/batch route assertions retain feature results, diagnostics and `None` children |
| Hostile paths, expired/revoked token, wrong resource or sensitive file | No | Keep established explicit denial and containment | Removed checks classified only feature origin; existing security boundaries remain in source; this is not a comprehensive security acceptance claim |

## Compatibility and error policy

- Public retained inspection acquires no new account-store dependency. Required group operations retain explicit configuration/unavailable failures and acknowledgment rules.
- PATH no longer treats a read dependency as contrast execution. Other direct restricted actions retain their feature guards.
- Browse, dedicated download, exports and fork/archive remove feature-derived sharing barriers; private resource, token, sensitive-file and containment checks remain independent requirements.
- Open polling retains its configured admission and unprojected lifecycle/queue/result shape. Cancellation now admits actual restricted tasks throughout the retained tree before stopping work.
- Expected absence of optional state must not become an internal exception. Existing report CAP checks and ordinary endpoint authentication are preserved.
- No universal D-Tale login, DuckDB upgrade, new identity, token scope/TTL change or global anonymous-writer restriction is implied.

## Validation and evidence limits

Independent command:

```text
wctl run-pytest tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=3 -q
```

Result before disposition: **3 failed**, 8.43 seconds. The three cases expected User, PowerUser and Admin report reads to return 403; the amended implementation correctly returned 200. Those superseded expectations were corrected without restoring feature read gating.

Independent post-fix command:

```text
wctl run-pytest tests/microservices/test_feature_access_data.py tests/microservices/test_rq_engine_jobinfo.py tests/weppcloud/routes/test_omni_bp_routes.py -q
```

Result: **84 passed**, 1.65 seconds, with seven dependency deprecation warnings. This includes exact shared polling responses, direct/nested restricted cancellation denial before any stop, shared report roles, retained resource/CAP guards and optional absent report state.

The author additionally reported **275 passed** across delivery/export/fork/browse/D-Tale launch/jobinfo/Omni report tests, and an earlier evaluator/query/PATH run reached **219 passed, 2 skipped** before a subsequently corrected export test-stub failure. Those broader results are author evidence, not independently rerun totals. `/tmp/fa02-full-pytest.log` was still running at readback; no full-suite pass is asserted here.

Source inspection covered the removed helper imports/calls, evaluator decision order, real task function names, recursive cancellation implementation, optional NoDb reader behavior, and existing endpoint guards. Updated helper tests exercise shareable catalog sources, export aliases/traversal, ordinary contrast-child operations and public inspection without account lookup. Helper tests alone do not establish transport or generated-content acceptance.

| Evidence stage | Result |
| --- | --- |
| User intent and canonical behavior | Reviewed against accepted FA-02 ancestor |
| Persisted state and generated intermediate/executable inputs | No producer or schema changes in this bounded delta; no fresh scientific run independently generated |
| Direct failing boundary | Stale route expectations reproduced and fixed; post-fix route/helper regression passes. Cancellation tests stub identity/feature admission and stopping; absent-state test stubs the optional reader. These do not substitute for real Redis/NoDb/browser acceptance |
| Generated artifacts consumed by browser/download/query | Existing retention/delivery paths inspected; byte equality, live browser, ZIP/fork/restore and production-equivalent service evidence not completed by this review |
| Artifact observability | Removing feature-only filters restores ordinary access to retained data/catalogs/results; introduces no hidden lineage artifact |
| Highest supported claim | Bounded runtime correctness fixes reviewed with focused regression; not M3 acceptance |
| Deployment/recovery | M3 remains incomplete and undeployed; known private-resource findings and final acceptance remain outstanding |

## Cancellation concurrency limitation

`job_routes.canceljob` reads and authorizes a recursive snapshot before `cancel_jobs` fetches the root again. The preflight does not share a transaction or dispatch lock with that later fetch. Existing `cancel_job._cancel_job_recursive` honors `child_dispatch_lock_key` during stopping, but the route's earlier snapshot is outside that lock. Consequently this review does not prove that every descendant created during that interval was individually preflighted.

Source tracing found OpenET/PATH submissions directly admitted as their classified tasks, and contrast/AgFields/Batch/Culvert dispatch roots are also classified. No supported ordinary dispatcher that adds a differently governed task after preflight was established in this bounded investigation. The observed snapshot/dispatch gap is therefore an explicit residual concurrency risk, not a reproduced authorization escape or an authorization to redesign cancellation. Final M3 acceptance should retain this limit; a concrete mixed-feature dispatch path or deterministic race reproduction would require disposition before claiming that path safe.

## Verdict

- Bounded correctness gate: **pass for the reviewed FA-02 reconciliation and RC01–RC03 fixes**.
- Unresolved concrete findings in this review: High **0**, Medium **0**, Low **0**. The cancellation concurrency limitation and acceptance coverage gaps remain explicit above.
- Release recommendation: **hold M3 completion**. Separate open private-resource findings, full-suite validation and full M3 artifact/browser/service gates still apply; this bounded pass is not deployment or M3 approval.
- Reviewer: `/root/contract_correctness`, 2026-10-02 UTC.
