# Milestone three interim security review

## Metadata

- Package: `docs/work-packages/20261001_feature_access_governance/`.
- Reviewer: `/root/contract_security`; independent read-only source review,
  retained 2026-10-02. Only this review artifact was written by the reviewer.
- Base: `c19fefcc69eaa8487abe3c8aaddf9a5f10ffff3f`; uncommitted M3 working tree.
  Line references below identify the reviewed snapshot and may move as fixes land.
- Scope: principal adapters and issuers; shared Flask/RQ workflow admission;
  browse, download, GDAL, D-Tale, query/MCP, export, and job-result boundaries.
- Authority: [FA-01](../../../schemas/feature-access-governance-contract.md),
  [RQ response contract](../../../schemas/rq-response-contract.md),
  [active plan](../prompts/active/feature_access_governance_execplan.md), and
  [tracker](../tracker.md). This is an interim gate, not a completed correctness,
  QA, browser, deployment, or integration acceptance review.

## Security Triage Decision

Security impact: **high**; dedicated review required. M3 turns recorded
membership into live admission across several processes and protects retained
scientific data on existing public delivery paths. A hidden UI control alone
does not enforce the boundary.

Trusted infrastructure includes credential verification, the account database,
operator-owned integration registration and server-controlled session bindings.
Attackers can supply URLs, grouped/legacy aliases, query expressions and stale
credentials, and can revisit cached dataset URLs after membership removal.
Signed provenance establishes origin, never mutable permission. Existing scope,
resource, expiry, revocation, session-marker and project checks remain additive.

Controls must preserve ordinary anonymous creation/editing/model work, ordinary
query/cache behavior, public non-embargoed reads, absent optional feature state,
legacy Dev/Root entitlement where specified, open lifecycle polling, and the
registered Culvert service contract. PowerUser sanctions remain deferred.

## Findings

**Applied / pending acceptance** means the reviewer read the mitigation in the
working tree, but has not confirmed its final executable acceptance evidence.
It is not a closed security finding or a release waiver.

| ID | Severity | Surface | Initial defect / exploit | Current disposition |
| --- | --- | --- | --- | --- |
| M3-S01 | Medium | Public inspection | RQ admission resolved account identity before deciding that public non-embargoed inspection needs no account lookup, introducing an unnecessary account-store failure dependency. | Applied / pending acceptance: public inspection bypasses identity resolution. |
| M3-S02 | Low | Configuration errors | Missing/malformed integration registration escaped the intended feature-unavailable boundary, allowing generic caller authentication errors/tracebacks. | Applied / pending acceptance: typed configuration error translated at the RQ boundary. |
| M3-S03 | High | Query workflow roots | Ordinary datasets under private Batch/Culvert roots were queryable without their workflow entitlement; checking contrast dataset names alone missed grouped IDs and absolute/symlink aliases. | Applied / pending acceptance: resolved workflow-root admission at entry and dataset sources. |
| M3-S04 | High | Query execution | SQL expressions can read protected files absent from the declared dataset list; dataset admission does not constrain DuckDB's effective file access. | **Open**; compatible execution boundary and dependency evaluation unresolved. |
| M3-S05 | High | Grouped D-Tale/GDAL launch | Public Batch or workflow-only callers could launch protected contrast tables/rasters through helpers that checked the workflow but not the requested data. | Applied / pending acceptance: source checks added before handoff/output. Downstream cache access is separate S08. |
| M3-S06 | Medium | aria2c catalogs | Public manifests enumerated protected filenames and URLs even when HTML/query catalogs hid them. | Applied / pending acceptance: per-file checks, including bundles. |
| M3-S07 | Medium | Job polling availability | Recursive projection called `.get` on `None` children emitted for missing/expired RQ jobs, breaking otherwise ordinary polling. | Applied / pending acceptance: non-dictionary descendants are preserved safely. |
| M3-S08 | High | Retained D-Tale data | Once an entitled caller loads a restricted dataset, anonymous/removed callers can directly retrieve cached data through public D-Tale routes. | **Open**; live conditional admission must follow dataset delivery. |
| M3-S09 | High | Legacy child aliases | Parent-only authorization missed `?pup=omni/contrasts/<id>` for generic Flask reports/actions and RQ exports using a resolved child working directory. | Applied / pending acceptance: resolved active-source checks in shared Flask and export adapters. |
| M3-S10 | Medium | Raw query catalogs | Raw `_query_engine/catalog.json` exposed protected entries/schema hidden by the query API; the file was not classified as mixed protected metadata. | Applied / pending acceptance: classify raw catalogs, resolved sources and catalog ZIP members. |

### Source evidence and required closure

**S01–S02.** `wepppy/microservices/rq_engine/feature_access.py:28–53` now returns
an anonymous principal for absent claims and skips account resolution for
public inspection. `wepppy/weppcloud/utils/feature_access_identity.py:20–29`
and `:68–81` wrap account configuration and registration failures in
`FeatureIdentityConfigurationError`; the RQ adapter catches it with SQL errors
and returns explicit unavailability. Confirm ordinary public reads during an
account outage and fail-closed protected requests with missing/bad registration.

**S03.** `wepppy/query_engine/app/helpers.py:26–59` accepts grouped and absolute
run paths. Initially `app/feature_access.py` checked only protected dataset
sources. Its current `require_root` resolves configured Batch/Culvert roots,
uses the existing grouped transport/resource checks for non-MCP requests, and
adds live feature admission after MCP's existing resource/scope checks. Web and
MCP entry points invoke it immediately after resolution; `require_datasets`
and `visible_entries` check logical and catalog physical sources too. Source
tests in `tests/microservices/test_feature_access_data.py` cover private roots,
symlink aliases, ordinary roots and the public Batch exception. Confirm these
through real request entry points and authenticated allowed/removed principals.

**S04.** `wepppy/query_engine/payload.py:114–163` accepts arbitrary computed SQL;
`core.py:343–358` inserts columns/computed/aggregate expressions into the query;
`executor.py:35–49` executes them with external access available. An ordinary
declared dataset plus a scalar subquery calling `read_parquet` on
`omni/contrasts.out.parquet` passes declared-dataset checks and reads protected
data. The web endpoint constructs this payload directly. Constrain effective
execution sources to authorized physical files while preserving valid ordinary
expressions, spatial reads and bounded execution. Do not rely on SQL keyword
blacklists. The parent reports an installed DuckDB 1.1.1 experiment: no
`allowed_paths` setting, and global external-access disable also prevents reads
through prebound ordinary Parquet views. This experiment is parent-reported,
not independently reproduced here. Upgrade evaluation is awaiting the operator;
no upgrade or alternate execution design is approved by this review. Acceptance
must execute synthetic protected-file attempts, ordinary/spatial queries,
aliases/globs and attempts to re-enable or expand access through submitted SQL.

**S05.** Initial `wepppy/microservices/browse/dtale.py:147–157` performed only
group admission before the loader handoff; the three GDAL handlers likewise
executed the selected source after transport admission. Current D-Tale
`:179–184` checks the logical/resolved file before load; `_gdalinfo.py:151–155`,
`:199–203` and `:251–255` check logical and final target paths before execution.
Confirm public ordinary files and entitled protected files still work, while
anonymous/workflow-only callers cannot load protected data through either
grouped route, including aliases and virtual-path handling.

**S06.** `wepppy/microservices/browse/_download.py:306–339` originally called
`_collect_file_specs` without feature context. Its current `:758–787` checks
every candidate with `require_data_access(..., inspect_bundle=True)` and omits
denied entries. Confirm ordinary entries remain and protected paths, aliases
and mixed ZIPs disappear from anonymous/unentitled manifests.

**S07.** `wepppy/rq/job_info.py:199–218` intentionally appends `None` for missing
children. `wepppy/microservices/rq_engine/feature_results.py:89–95` now returns
false for a non-dictionary descendant. Confirm single/batch polling with missing
children, ordinary results and nested protected children; retain lifecycle and
queue fields while removing protected auxiliary fields. Review source also
shows orchestration reads applying the same projection before derived responses.

**S08.** The affected tracked file is
`wepppy/webservices/dtale/dtale.py`, absolute path
`/home/workdir/wepppy/wepppy/webservices/dtale/dtale.py` in this checkout.
`:186–189` derives a predictable dataset ID from run/config/path; `:1072–1099`
serves grid data without principal/feature admission. The internal token check
at `:1142–1146` protects loading only. `docker/caddy/Caddyfile.wepp1:193–206`
directly exposes `/dtale*` and `/weppcloud/dtale*`;
`docker/docker-compose.prod.yml:238–265` runs the tracked service entry point.
An entitled launch therefore leaves a protected table available to anonymous
or removed callers at `/dtale/data/<id>`; eager data, metadata, export and map
surfaces must be assessed with it. Preserve source/workflow classification and
enforce live conditional admission on downstream representations. Launch-only
checks, opaque IDs or stale grants are insufficient. Preserve ordinary public
D-Tale behavior; any different restriction on legitimate protected workflows
requires an explicit policy decision. Real service/browser acceptance is needed,
including a previously loaded table after membership removal. No service
deployment is authorized or performed by this review.

**S09.** `wepppy/weppcloud/routes/_run_context.py:83–90` selects a legacy pup
directory while retaining the parent's run ID. The original shared guard used
only run ID syntax, allowing public-parent generic reports/actions to reach a
contrast child. Current `utils/helpers.py:784–797` classifies the active/pup
source and gates it. `wepppy/microservices/rq_engine/export_routes.py:91–122`
now classifies every return from `_resolve_export_wd`, and its callers pass
claims and preserve authorization errors. Confirm legacy and composite aliases
through actual Flask reports/actions plus ERMiT sync/submit/download and related
exports, including entitled success and ordinary scenario compatibility. This
finding concerns existing aliases, not the separately pending fork policy.

**S10.** `wepppy/query_engine/catalog.py:50–61,119–133` loads raw catalog JSON
containing dataset paths, physical pointers and schemas. Browse's hidden-path
guard rejects dot prefixes, not `_query_engine`. The current
`wepppy/weppcloud/utils/feature_access_data.py:38–47,75–79,115–119` classifies
mixed raw catalogs and catalog members inside ZIPs. Confirm raw browse/download,
alias and ZIP cases, including catalogs with physical pointers to renamed
protected exports. Ordinary catalogs must retain their established behavior.

## Verdict

- Gate status: **fail — NOT PASSED**.
- Open implementation findings: High **2** (S04, S08).
- Applied but acceptance-unconfirmed findings: High **3**, Medium **4**, Low **1**.
- Release recommendation: **hold M3 acceptance and dependent self-promotion**.
  No Medium/High finding has been waived or accepted as residual risk.

The existing fork-destination lineage question is an additional policy blocker.
The operator must settle how copied restricted workflow/contrast data remains
classified at its destination. This review does not choose a blanket fork
prohibition, invent a new artifact schema, or count the known unanswered question
again as a newly discovered code finding. The SQL dependency decision and
downstream D-Tale design must also be settled before final acceptance.

## Surface Checks

1. **Valid states/UX:** preservation targets are stated above; full route/browser
   acceptance is outstanding. Source readback cannot establish noninterference.
2. **Auth/session/CSRF:** trusted adapters resolve canonical human IDs, legacy
   SID bindings, admin-run-token delegation and registered integrations. Live
   roles/membership replace informational token groups for feature admission.
   Ordinary scope bundles and the separate Culvert browse credential remain;
   protected transport composition still requires final acceptance.
3. **Secrets:** no credentials were read, printed, rotated or introduced by this
   review. Integration registration contains non-secret identity metadata.
4. **Input/output and filesystem:** source classification covers protected
   paths, mixed NoDb, manifests, direct/bundle delivery and aliases. S04, S08 and
   the fork decision prevent a complete data-boundary pass.
5. **Queues/subprocesses:** admission is before restricted submission, with
   recursive result projection and explicit cancellation checks. Preserve
   admitted-job completion and ordinary open polling. Full queue/lifecycle
   regression evidence is pending.
6. **MCP/tooling:** existing query audience, scope and run guards remain in place;
   current feature checks are additional. SQL execution remains an open bypass.
7. **Network/integrations:** no production action occurred. Culvert's expired
   deployed credential must remain rejected; eventual authorized renewal and
   live compatibility testing are separate rollout prerequisites.
8. **Supply chain:** DuckDB upgrade evaluation is not yet approved/completed.
   Preserve dependency precedent/evaluation and spatial-extension compatibility.
9. **Integrity/concurrency:** membership remains a live database decision; this
   slice adds no migration or group mutation. M1/M2 transaction reviews are
   historical evidence, not proof of every M3 adapter and cached delivery path.
10. **Logs/recovery:** unavailable feature decisions fail closed. Correlated
    final response/error behavior and rollout/rollback evidence remain part of
    the final checkpoint, not established by this interim review.

## Validation Evidence

The reviewer inspected current source, diffs, focused test source, canonical
contracts and the actual D-Tale Compose/Caddy relationship. No runtime exploit
was attempted against user data; no application tests, browser workflow or
deployment were executed by this reviewer. Parent-owned acceptance work is in
progress. Test existence alone is not recorded as a passing result.

`wctl doc-lint --path` for this artifact passed: one file, zero errors/warnings.
The `uk2us` preview identified one spelling normalization, applied here.
Final review must link actual focused and broad test logs and service/browser
acceptance evidence, then disposition each pending finding explicitly.

## Residual Risk and Sign-off

- Accepted residual risks: **none for the findings above**.
- Security reviewer: `/root/contract_security`, interim **NOT PASSED**.
- Package owner: root orchestrator to track fixes, operator decisions and final
  independent review. No risk-acceptance acknowledgment or release approval is
  supplied by this artifact.

## Artifact Observability Gate

Existing run tools remain the observation paths for ordinary artifacts. FA-01
explicitly authorizes feature entitlement for embargoed objects and an explicit
denial for indivisible protected bundles; it does not authorize silently partial
archives or hidden-only replacements. Final acceptance must prove actual
browser/download behavior, generated artifact correctness and archive/restore
classification under representative identities. These gates remain pending.
