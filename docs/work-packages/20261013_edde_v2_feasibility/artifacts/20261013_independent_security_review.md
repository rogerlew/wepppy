# Independent security review — EDDE v2 feasibility

## Findings

| ID | Severity | Surface and exploit/failure path | Evidence and required remediation | Status |
| --- | --- | --- | --- | --- |
| ISEC-01 | Medium | Ambient credentials: the initial default Requests session attached matching `.netrc` credentials to the supposedly anonymous public S3 request. A machine or default entry could therefore disclose credentials to that external host. The Daymet study helper used the same default behavior. | Reproduced using a temporary synthetic `NETRC` and request preparation, without sending credentials or inspecting real secrets. Explicitly disable ambient authentication. Current `client.py:116` and `artifacts/reference.py:20` set `trust_env=False`; the contract declares the resulting direct-HTTPS proxy/CA policy. `test_public_requests_ignore_ambient_credentials` and independent live S3/Daymet checks pass. | Resolved |
| ISEC-02 | Medium | Provenance integrity: a new PRISM CLI target could have an existing companion `.prism.json`, which the original writer would overwrite. A companion/source alias could also replace the source after hashing it. | Reject occupied CLI and companion paths and either source alias. Current `cligen.py:135` enforces this; `test_prism_preserves_existing_provenance` and the independent correctness preservation probe pass. Also tracked as ICOR-03. | Resolved |

No unresolved high, medium, or low implementation finding remains within the reviewed scope. These findings required code changes; they were not accepted as residual risks.

## Metadata and review order

- **Reviewer**: independent security reviewer agent, `/root/edde_security_review`; no production-code edits.
- **Date**: 2026-10-13 UTC.
- **Context**: planning commit `03435abc5` plus the working-tree feasibility implementation. Exact reviewed source/test hashes and checks are retained in [independent check evidence](20261013_independent_security_checks.json).
- **Scope**: `wepppy/climates/edde/`, its two test modules, public acquisition/study scripts, retained archives, and the [experimental contract](../../../schemas/edde-v2-experimental-client-contract.md).
- **Preceding gates**: [independent correctness review](20261013_independent_correctness_review.md), pass with all three medium findings resolved; [implementer QA review](20261013_qa_review.md), explicitly not independent. Both were read before this final security verdict.

## Security triage and assumptions

**Impact: high; dedicated review required.** Public network egress, downloaded native files, filesystem writes, and executable invocation trigger the repository's security gate. This classification does not make the research interface a public service.

Callers are trusted local researchers choosing their own writable cache/output roots and canonical station inputs. Cache roots have one writer and are not shared with hostile principals. Source endpoints are fixed public HTTPS services; downloaded bytes remain untrusted input to existing native parsers. No application route, project authorization, NoDb state, RQ worker, deployment, or new dependency is introduced. This verdict does not cover arbitrary endpoints, shared writable caches, hostile filesystem owners, or multi-tenant execution.

The correctness review's absent/empty/populated/legacy/hostile state matrix was checked. Fresh and verified populated caches, new outputs, and valid native land cells work. Corrupt/truncated cache objects, outside/ocean cells, malformed climate inputs, and occupied outputs fail explicitly under the documented contract. Existing application workflows receive no new controls.

## Surface checks

| Surface | Review result |
| --- | --- |
| Authentication, session, JWT, CSRF | No application changes. Anonymous egress now explicitly suppresses ambient credentials. No secrets or credentials are required by the new interface. |
| Network and remote names | Fixed S3 HTTPS root, safe archive identifiers, encoded listing parameters, no redirects, explicit timeouts, listed-size/transfer budgets, and `If-Match` plus response ETag checks. Daymet helper also requires direct HTTPS and HTTP 200 without redirects. |
| Cache and local paths | Remote keys become SHA-256 cache names, not filesystem path components. Fresh local SHA-256 and size/metadata equality gate cache reuse. Partial downloads retain attempt identity and are promoted only after exact byte-count validation. Local roots remain a trusted-caller boundary. |
| Outputs and recovery | Query/CLIGEN output directories must be new; incomplete manifests precede acquisition/generation. PRISM preserves existing CLI/companion evidence. No completed status is emitted after validation failure. New attempt locations are the documented recovery path. |
| Execution | Fixed existing CLIGEN binary, argument vectors rather than shell interpolation, explicit 120-second timeout and zero retries, and no quality-guard bypass. Study WEPP execution uses a fixed repository binary with a timeout. Downloaded content never selects an executable. |
| Data integrity | Source geometry/calendar/coverage/values and generated CLI semantics are checked. The correctness review independently confirmed valid retained PRISM files still pass strengthened rejection rules. Atomic cache-object promotion does not claim concurrent-writer support. |
| Evidence archives | All three SHA-256 digests and member counts match the final index. All 1,528 members are regular files with relative paths and no traversal components. Container fixture extraction verifies its archive hash and uses the data extraction filter. |
| Logs, secrets, and supply chain | Logs/manifests retain public source identity, source/output hashes, and failure evidence. Inspection found no new secret source or secret logging. A limited archive scan found no AWS access-key-ID or private-key-header signatures; this is not an exhaustive secret scan. Existing dependencies/binaries are reused; no CI/CD permissions or publication paths changed. |
| Queue, NoDb, agent tooling, deployment | No changed interfaces or privileges in these surfaces. This review performed bounded read-only network probes and wrote only review evidence. No further agents were delegated. |

## Validation evidence

- Independent final focused run: `wctl run-pytest tests/climates/test_edde_client.py tests/climates/test_edde_cligen.py` — **25 passed**, two existing dependency deprecation warnings; [retained log](validation/security-focused.txt). Real NetCDF, local cache corruption/truncation, and actual CLIGEN/PRISM outputs supplement mocked HTTP transport.
- Credential boundary: before-fix synthetic `.netrc` request preparation reproduced an Authorization header with zero network traffic. The corrected client regression prepares the same request without Authorization. No real credential file was read.
- Live container S3 probe: direct HTTPS listing returned three static objects, including one land mask, with `trust_env=False`; zero weather bytes downloaded.
- Live Daymet probe: the corrected study helper acquired a 389,542-byte reference CSV and companion manifest into a temporary directory. The reviewer asserted no Authorization header, `trust_env=False`, and redirects disabled immediately before the real send, with only synthetic `NETRC` contents in scope. Temporary probe outputs were removed.
- Independent archive checks: 276 point-data, 352 generated-climate, and 900 WEPP-evidence members; matching indexed hashes and safe regular-file membership. The linked correctness review additionally verified source CSVs and consumed/generated artifact hashes and semantics.

The broad regression suite has a reproduced unrelated SBS metadata assertion failure and an incomplete continuation. This security verdict does not turn those results into a passing broad gate or authorize package closure past that limitation.

## Verdict and residual scope

**Security gate: pass for the standalone research delivery.** Unresolved findings: high 0, medium 0, low 0. Recommendation: retain the experimental interface and the explicit hold on general WEPPcloud production integration. No risk acceptance is needed or inferred for the resolved findings.

Residual trust assumptions remain material: HTTPS authenticates the public provider, while ETags/local hashes establish object identity and local integrity rather than independent scientific authenticity. Existing NetCDF/PROJ/CLIGEN parsers are not newly sandboxed. Download limits and read/connect timeouts do not implement global storage retention, multi-worker admission, or a wall-clock service deadline. These are documented research boundaries, not approved production behavior. The [integration package](../../20261013_edde_v2_weppcloud_integration/package.md) must reassess concurrency, trusted paths, project authorization, resource limits, and production execution parity before adopting this client.

Scientific bias, station-derived auxiliary weather, CLIGEN rejections, PRISM inversions, and Canadian watershed acceptance remain separate production blockers. Security approval does not close them.

## Artifact observability and sign-off

Comparable artifacts follow the existing climate/CLIGEN/PRISM workflows; the durable contract's Artifact layout and operational recovery section and `evidence-index.json` define the study inventory. Source tables, intermediates, failed attempts, generated climates, execution inputs, hashes, and representative outputs are visible in standalone files/archives. The independent writer/consumer and archive checks support that limited claim.

Project browser/download/archive tests are not applicable to this additive standalone study; no project tree or exclusion policy changed. Those tests remain required for integration. No observability waiver or deployment approval is granted.

**Signed**: independent security reviewer agent, 2026-10-13 UTC. Package closeout authority remains with the parent/operator, subject to all other recorded gates.
