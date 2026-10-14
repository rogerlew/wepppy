# EDDE-WEPP-01 independent contract security review

## Findings and verdict

No blocking contract finding. **PASS for the preimplementation checkpoint only.** There are no unresolved high, medium, or low findings. Runtime implementation, environment acceptance, and the dedicated final security gate remain pending; this review does not authorize deployment or replace correctness review.

The proposed controls preserve valid absent, empty, populated, and legacy climate state. Missing optional EDDE state does not invalidate an existing method. EDDE submission requires an explicit valid projection and period; unsupported or hostile selections fail before mutation/enqueue. Locale presentation does not substitute for server authority or native-cell eligibility.

## Metadata and scope

- Reviewer: independent `security_reviewer`, `/root/edde_integration_contract_security`.
- Date: 2026-10-14 UTC.
- Starting implementation revision: `6acfb3d23ae91f834fae92c0e691cb9ec76a5b54`.
- Reviewed: new `docs/schemas/edde-v2-weppcloud-contract.md`; amendments to the experimental client, project-owned configuration, and RQ agent API contracts; package checkpoint and active ExecPlan.
- Supporting implementation inspection: `wepppy/climates/edde/client.py`, `wepppy/nodb/_derived_build.py`, `wepppy/nodb/core/climate_observed_build.py`, and `wepppy/microservices/rq_engine/climate_routes.py`.
- Related review: independent contract correctness review, being completed separately for this checkpoint.
- No runtime files were edited by this reviewer. The review artifact is the sole authored file.

## Authority and security triage

Security impact is **high** and a dedicated final review is required. The existing authenticated climate endpoint gains a source acquisition and model execution path. The operator requested integration after accepting raw EDDE future values and the established station-derived CLIGEN hybrid. The contract stays within that scope: no historical application mode, source bias/elevation correction, new queue/service/dependency, changed auth policy, graph migration, or deployment.

The additive capability reader floor precedes live writers and covers ordinary and existing single-input variants. Existing graph identities/choices remain unchanged until explicit refresh. The exact-current compatibility allowance explicitly cannot bypass EDDE source or locale validation. This protects existing valid projects while preventing a submitted mode number or stale graph from granting an unsupported source choice.

## Surface assessment

| Surface | Contract assessment | Required implementation evidence |
| --- | --- | --- |
| Auth, session, CSRF, read-only access | Reuses existing build-climate authentication, run access, enqueue scope, conflicts, and replay; browser/archive authorization is unchanged. | Actual authorized submission and rejected unauthorized/read-only requests; no acquisition or durable mutation on denial. |
| Input, paths, and rendering | Projection is a finite combined choice; years and spatial modes are bounded. Project attempts are locally generated. Existing client validates point/key tokens and hashes complete keys for cache names. | Reject malformed field types, traversal/URL-shaped projections, unsupported combinations, and nonfinite coordinates. Preserve template escaping and run-root/symlink safeguards. |
| Egress and secrets | Experimental client contract fixes the public HTTPS bucket, disables ambient credentials/proxies, rejects redirects, and requires explicit timeouts. No user endpoint or credential input is added. | Verify integration uses that client unchanged; response errors and manifests must not expose service credentials or unrelated project content. |
| Resource use and queue | One private yearly cache with the existing 4-billion-byte query budget; finite period and existing RQ timeout; no automatic retries or shared cache writes. | Demonstrate consecutive-year cleanup, failure/cancellation behavior, requested source footprint, and actual queue timeout. Keep prior evidence when a retry starts a new attempt. |
| Source integrity | Listing identity, exact size, ETag/If-Match, and SHA-256 remain required. Native projected grid and land mask govern eligibility before daily acquisition. | Tampered/wrong-size cache rejection, partial acquisition, absent records, invalid cells, and retained source identities; no fallback model/cell/date. |
| NoDb and publication | Snapshot collection outside the lock; fresh durable comparison under finalization lock; allowlisted derived fields; previous publication retained until success. | Direct real-filesystem tests for supersession, changed geometry/settings, interrupted publication, symlink rejection, and preservation of unrelated fresh state. Do not substitute mocked publication for these tests. |
| Artifact integrity and observability | Visible unique attempt directories retain points, source identities, extraction/generation evidence, diagnostics, and failures. Disposable class is explicitly source NetCDF cache bytes. | Retain useful per-object attempt/identity metadata before discarding temporary cache bytes, including failed queries; actual browser/download and canonical archive/restore must preserve successful and failed records. |
| Science/provenance | Raw EDDE fields, station-generated auxiliary fields, optional PRISM revision, and user precipitation scaling stay separately attributed. Station header location cannot stand in for the EDDE cell. | Persisted selection, actual source/CLI hashes, prepared WEPP inputs, fresh WEPP outputs, and rendered provenance must agree for actual US and Canadian geometry. |
| Supply chain and tooling | No new dependency, binary, service, privilege, or deployment topology is proposed. | Final review checks the actual change set and build commands for scope drift. |

## Implementation gate notes

The source client's `.attempt.json` records are initially written inside its cache. Removing a yearly temporary directory must not discard the only useful failure identity/status record. Preserve that diagnostic evidence under the visible project attempt before cleanup; raw source NetCDF bytes remain reconstructible cache under the application contract.

A killed or timed-out worker may be unable to mark an attempt failed. A retained working/incomplete attempt must remain inspectable and must never be presented as completed readiness. Existing cancellation and terminal-job semantics are not weakened by this integration.

The reviewed route uses `RQ_TIMEOUT`, default `216000` seconds, rather than `project_rq.TIMEOUT` (`43200`). A 75-year MPI request has a conservative source-query ceiling of 300 billion bytes across sequential yearly queries; this is not a 4-billion-byte whole-job limit. These are bounded existing-mechanism choices, not a promise that all longest periods finish. Environment evidence must report actual source bytes, elapsed time, configured timeout, and failure behavior. No new threshold or authorization flow is requested by this review.

## Validation and residual risk

This is a read-only contract and precedent inspection, not runtime conformance evidence. Existing standalone client tests cover credential isolation, unsafe keys, budget enforcement, cache integrity, and partial failures; they do not prove the newly proposed route/worker/publication boundary. The final review must follow implementation correctness/QA review and require no unresolved medium/high findings.

Residual risks are upstream source availability, authenticated high-cost builds within the supported finite period, and process interruption during multi-file publication. Existing timeout/conflict mechanisms and the proposed retained-attempt/finalization behavior address these without changing accepted workflows. No exceptional risk acceptance is requested or recorded. The final gate must review actual handling and evidence before package closeout.

## Sign-off

Independent security reviewer approves EDDE-WEPP-01 for the standalone contract checkpoint. Package owner disposition and the ancestor revision are recorded in the checkpoint/tracker. Implementation and deployment approval are expressly outside this sign-off.
