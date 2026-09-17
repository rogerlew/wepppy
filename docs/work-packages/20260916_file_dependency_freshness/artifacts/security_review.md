# File dependency freshness: consolidated security review

**Security PASS through `de3a1eba0`, including the reviewed bounded development
runtime.** The required dated closeout is
[20260917_security_review.md](20260917_security_review.md). No known unresolved
production security finding remains in the reviewed changes. Root documentation,
QA/check reconciliation and package closeout remain separate. Earlier pending
statements below describe their review cutoffs and are superseded by the dated
runtime disposition, not rewritten into historical passes.

## Metadata and triage

- Package: `docs/work-packages/20260916_file_dependency_freshness/`.
- Independent reviewer: `freshness_security`, 2026-09-17.
- Scope: the bounded implementation waves from baseline `adb4f9b00` through
  `de3a1eba0`, including their reviewed follow-up fixes. The accompanying
  [source bindings](security_review_source_bindings.json) enumerate all 48
  changed Python implementation/stub files; all current bytes match that commit.
- Method: prior direct filesystem/native/permission probes and independent
  checkpoint/implementation reviews, consolidated by read-only inspection while
  the final broad suite runs. No new probes, production/test edits, deployment,
  credential reads or named-project mutations were performed for this review.
- Security impact: **high**; dedicated review required for file/path authority,
  uploads/downloads, native discovery, retained artifacts, replay and archive
  restoration. This classification does not imply an authentication redesign.
- Correctness and QA remain separate gates. In particular, use the linked wave
  reviews below, [remaining-family QA](remaining_inventory_disposition_qa.md),
  [C02/C07 assessment](features_omni_remaining_closure_qa.md), and the final
  correctness/QA follow-ups when supplied. This review does not sign for them.

## Findings and verified closure

Original failed designs, probes and logs remain evidence. A later passing
revision closes its stated finding without relabeling the original failure.
The IDs below are local to their linked reviews; the links retain actual
commands, source locations, outputs and scope limits.

| Finding / surface | Severity and failure path | Required correction and retained evidence | Disposition |
| --- | --- | --- | --- |
| SEC-I01, SEC-I02: post-fire digests | Medium: growth caused unbounded reads; ordinary rapid equal-stat rewrites reused stale SHA. | Captured-size bounds, one-second monotonic observation, fresh admission and bounded observation generations. Actual growth and real-clock collision controls in [first-wave review](first_wave_security_review.md). | Resolved within the stated filesystem/read-observation assumptions. |
| Report RP-SI01–03, RP-I02 | Medium: partial absence concealed denial, history required a new write, malformed proof downgraded, or rejected history prevented a valid rebuild. | Validate complete proof and present prerequisites; read-only historical context; reacquire authoritative current context before a rebuild. [Report review](reports_implementation_security_review.md). | Resolved. |
| Report RP-I01 | High correctness/integrity finding: a copied project could query its original root and return100 instead of900. | Clone and normalize only the three selected report catalog entries; current allowed absolute paths take precedence; query and proof use the same context. Real relocation after-probes in [report review](reports_implementation_security_review.md). | Independently verified resolved. |
| Report RP-SI04/05 | Medium: atomic replacement bypassed C09's existing target write denial; version repair changed sidecar access/mode. | Nontruncating write authorization for the existing C09 target and repairable sidecar, preserving each writer's original semantics and sidecar's own mode. C08 retains its prior native replacement behavior. [Authorization follow-up](reports_write_authorization_security_review.md). | Resolved; earlier report PASS was explicitly reopened. |
| R-I01: raster inventory | Medium: GDAL could reopen a replaced auxiliary and add network access during freshness discovery. | Pre-open finite eligibility, restricted inspection siblings/drivers, explicit companion graph and unverified native fallback. Actual loopback and replacement controls in [raster review](raster_implementation_security_review.md). | Resolved for the bounded supported inventory; native operation options remain unchanged. |
| R-I02/03: raster admission | Low/Medium: a recorded parent becoming unavailable escaped the expected error; changed/restored sources admitted an intermediate native result. | Validate collected observations on failure; same-acquisition physical/configuration guards span the native operation, both C03 inputs and C04 admission/hits. [Raster review](raster_implementation_security_review.md). | Resolved. |
| G-I01/02: Geneva publication | Medium: generic write authorization rejected valid native replacement; late target alias/auxiliary changes escaped final validation. | Preserve JSON versus native writer authority; repeat selected-target and clean-layout checks after validation immediately before replacement. [Geneva review](geneva_implementation_security_review.md). | Resolved. |
| G-I03/04: Geneva compatibility/errors | Low: absent main files concealed orphan auxiliaries; post-commit diagnostic failure misreported success as failure. | Finite companion inspection selects the original native compatibility path; minimal diagnostic handling respects the commit point. Actual controls in [Geneva review](geneva_implementation_security_review.md). | Resolved. |
| P-I01: profile event paths | Medium: path replacement between validation and copying could write outside the selected event directory. | Held no-follow directory descriptors for creation, fixed members and receipt/status publication, plus final visible-path validation. Actual `os.open` replacement seam in [S02 review](profile_sbs_implementation_security_review.md). | Resolved. |
| P-I02/03: profile source selection | Medium: denied selected input fell back to different bytes; the initial correction then rejected a valid higher-priority source because an unused source was denied. | Strict errors until a source is selected, preserving priority and subsequent optional discovery. Real permission and valid-state controls in [S02 review](profile_sbs_implementation_security_review.md). | Resolved. |
| A-S01: archive attempt privacy | Medium: restore changed private0700 attempt ancestry to0755, exposing retained candidate files. | Record ordinary directory modes; validate before cleanup; establish recorded group/other restrictions before payload writes; restore final modes deepest-first. Nine actual controls in [archive review](archive_directory_implementation_security_review.md). | Resolved for new archives with usable directory metadata; legacy limits explicit. |
| O-I01/02: Omni SBS | Medium: late child mutation escaped admission; replacing `shutil.copyfile` lost same-inode protection and truncated the upload before rejection. | Complete-set final child guard; open destination without truncation, compare actual descriptor identities, then truncate only a distinct file. Eleven actual controls in [S01 review](omni_sbs_implementation_security_review.md). | Resolved. |
| O-C01/02: Omni durable admission | Correctness findings, including High runtime failure: an invalidated legacy association could be resurrected; detached refresh dropped the logger. | Match the captured association under lock and restore runtime logging after hydration while preserving unrelated durable state. [Independent correctness review](omni_sbs_implementation_correctness_review.md); security's actual one-lock control also passes. | Correctness verified resolved; no nested-setter or broader lock policy introduced. |

No unresolved High, Medium or Low **changed-code security finding** remains
in this scope. The unchanged CLI credential-output hazard described below is
not approved by that statement; runtime execution must contain it. The separate
preexisting scientific/UX limitations are not silently counted as fixed.

## Other reviewed implementation boundaries

| Wave | Reviewed guarantee and limit | Evidence |
| --- | --- | --- |
| NoDb hydration | Text and version come from one opened descriptor; observable drift retries through ESTALE. Atomic earlier generations retain their own version. No later pathname stat tags old text; NoDb metadata/Redis caching is not globally replaced. | [NoDb security](nodb_implementation_security_review.md). |
| C01 main paths | Uncached regular-file SHA strengthens transaction checks. Directory-backed inputs retain their prior identity with explicit absent digest, preserving valid Zarr. Indirect native closure remains unresolved. | [Derived-main security](derived_main_implementation_security.md), [indirect disposition](derived_indirect_closure_security_disposition.md). |
| Shared digests and C10 | Ordinary symlinks and access checks remain supported; bounded admission/cache eviction and consumer before/after expectations prevent the demonstrated stale hashes. C10 removes only the parsed-header metadata cache. | [Shared digest security](shared_digest_implementation_security.md), [header security](bundle_header_implementation_security_review.md). |
| C02 Features export | Content-bound selected files, immutable artifact provenance, separate candidates, verdict before successful packaging/publication, and accepted-producer proof for companions. Both prior bindings remain on verification rejection; cross-file I/O atomicity is not claimed. | [Features security](features_content_implementation_security.md), [correctness](features_implementation_correctness_review.md). |
| C11 D-Tale | Content plus resolved target bind reuse; lazy rows/counts verify generation before/after native work. Optional absence removes old overlays; partial registration is cleaned up. Existing grid receives its supported visible error envelope; internal loads retain409. | [D-Tale security](dtale_content_implementation_security.md). |
| PF-R02 CLI Parquet | Producer parses retained verified source bytes and publishes rows plus embedded proof together. Readiness requires that association; legacy files stay readable for existing readers. New attempt root uses held directory authority; source/output aliases and existing write access remain compatible. | [Lineage security](cli_lineage_implementation_security_review.md), [same-call parent reuse](cli_lineage_parent_reuse_security_review.md). |
| Geneva optimized guards | Every call acquires its own graph; joint physical/configuration checks surround member hashes and companion rescans. No cross-request authority reuse or stat-only substitute. Existing auxiliary-bearing outputs use their original uncached native overwrite and its explicitly weaker failure guarantee. | [Geneva security](geneva_implementation_security_review.md), [correctness](geneva_implementation_correctness_review.md). |
| S02 event dispatch | Original appended marker prevents failed captures from looking legacy. Exact immutable receipts bind per-event seeds; verified bytes, rather than a reopened path, are passed to Requests. | [S02 security](profile_sbs_implementation_security_review.md), [correctness](profile_sbs_implementation_correctness_review.md). |

## Surface checks and valid-state noninterference

The threat model includes ordinary concurrent writers, local path replacement,
permission denial, malformed/legacy provenance, partial native failures and
untrusted archive metadata within the existing run/actor authority. Tests use
actual service UID/GID and disposable local resources where stated. They do not
certify every production mount, ACL, ownership topology, arbitrary hostile writer
or native format.

| Security template surface | Scoped review result |
| --- | --- |
| Valid states and errors | Real empty/missing/legacy/current controls accompany changed-boundary probes. Permission and parse failures are not optional absence; unsupported raster inventory selects the existing native operation uncached. No blanket ban on previously valid ordinary symlinks, directories or formats was introduced. |
| Auth/session/JWT/CSRF | Existing route scopes, run/config selection and token/session policies remain. S01 reuses the existing signature argument and queue topology. No new token minting, cookie-to-bearer bridge, CSRF exemption or actor permission is approved. Restarted authenticated acceptance is pending. |
| Secrets | No credential dependency was added. This review read no secret files. The unchanged canonical profile command prints resolved cookies; the pending acceptance must keep raw output private and redact before retaining any record. This is not certification of that command's logging. |
| Input/output and paths | Domain-specific openers retain their existing authority: ordinary digest symlinks differ deliberately from post-fire no-follow reads. New private attempt/event writes use restricted creation and held descriptors where required. Final target selection and proof generation are rechecked. Existing external target capabilities are not silently replaced with containment bans. |
| Native/network authority | Raster proof discovery refuses unproven layouts before opening them for inventory and uses restricted sibling inspection. Original native execution retains its options and supported inputs. Loopback probes establish no added discovery requests in the tested cases, not universal native egress safety. |
| Queue/subprocess | No new queue edge, subprocess protocol or privilege is part of these waves. Actual direct/RQ dispatcher controls were reviewed; full worker/model execution remains a runtime gate. Retained graph refresh reports146 unchanged edges. |
| Integrity/locking | Scientific equality is separated from coherent-read and publication guards. Strict locked finalizers, NoDb lock ownership, optional absence and legacy states remain explicit. Partial candidates and failure evidence are retained without replacing accepted outputs. No multi-file transaction or atomic conditional-unlink guarantee is invented. |
| Logging/recovery | Expected drift is explicit; unrelated I/O/native errors retain their established behavior. Post-commit status failures cannot retroactively undo published success. Failure evidence survives rejected builds and archive restoration. |
| Tooling/CI/supply chain | No new dependency, service, watcher, external tool credential, deployment topology or CI privilege is introduced by these implementation commits. Security probes use disposable targets and do not authorize deployment. |

Metadata guards detect observable drift; they do not freeze in-place files.
The accepted timestamp-quantum policy and coherent earlier point-in-time read
limits remain material. Cache-hit reads still check authority. A digest or
successful stat tuple is not permission to stream different bytes, invent old
provenance, or claim an arbitrary multi-file snapshot.

## Durable contracts and retained limitations

Normative behavior is recorded outside this package in the file-dependency
contract and cache-admission ADR; NoDb persistence contract; report freshness
and output-scope contracts; climate-lineage contract; raster-dependency
contract; Features export specification; Geneva specification; Omni SBS
contract; Profile Test Engine specification; and artifact-observability archive
directory section. Their working hashes are in the source-binding artifact.
RAP, post-fire and GL user documentation records the principal unresolved
currentness limits. This satisfies durability of the decisions, not runtime
verification of their implementation.

Documentation precision remains for the owner's final pass: some canonical
headings still say `implementation pending` or `checkpoint pending` after their
implementations were committed. Refresh those labels and the living status
tables; retain the underlying historical probe failures. These are stale status
labels, not missing contracts or a new production defect.

The ExecPlan Decision Log explicitly adopts the package's allowed **justified
unresolved inventory** category. This narrowly qualifies earlier blanket
closure wording; it is not an exception for unresolved changed-code security
findings and does not itself waive runtime acceptance. No `Accepted-risk`
security finding or inferred human acknowledgment is used in this review.

| Remaining boundary | Exact disposition and follow-up authority |
| --- | --- |
| PF-R01 soil logical identity | Seven real logically equal SQLite cases remain conservatively stale. Strict snapshots and no-source-connect policy remain. A fix needs a ratified read-only polling/snapshot policy and measured owned-reader behavior, not an old digest assigned to an unseen generation. [Security disposition](soil_logical_currentness_security_disposition.md). |
| C01 indirect raster inputs | Main-file SHA does not prove nested VRT leaves or directory members. The complete small RAP run proves its40-file/234-native-call result and lock budget, not universal closure. Preserve formats/finalizers; future native read-set scope and cost require their own checkpoint. [Security disposition](derived_indirect_closure_security_disposition.md). |
| B-F01 browser generations | Confirmed active GL mixed-generation values remain unfixed; new-tab/reload guidance is recovery, not a snapshot guarantee. Related browser caches have individually stated unconfirmed boundaries. An explicit open-view refresh contract must precede a new generation workflow. [Disposition](browser_generation_unresolved_disposition.md). |
| C02 complete closure | Selected main-file correction is verified. A maintained mixed GeoJSON/Parquet/NoDb/Unitizer profile still needs its prepared runtime acceptance; arbitrary indirect/native and cross-input closure is not established by the one-layer probes. [QA assessment](features_omni_remaining_closure_qa.md). |
| C07 pruning | The held-receipt native stale mechanism is real; ordinary maintained producer/completion sequencing remains unverified. Keep completion authority. Future correction needs the actual producer/consumer result trace, source selection and whole-consumer cost before a new contract. [QA assessment](features_omni_remaining_closure_qa.md). |
| Wider maintained families | Roads upstream closure, AgFields cross-stage closure, cached whole-Geneva preparation, Omni contrast/unavailable-source reuse, other upload-event fidelity and finite browser/tool candidates keep the individual dispositions in [remaining-family QA](remaining_inventory_disposition_qa.md). No blanket safe conclusion follows from a negative search. |
| S01 native companions | The receipt binds copied main bytes and guards that child through execution. Inherited child world/mask/PAM files and indirect native dependencies remain outside that proof, as specified in the Omni contract and scoped review. No complete native dataset receipt is claimed. |

These are preexisting correctness/UX or evidence limits preserved by the bounded
work, not new false-current mechanisms accepted in changed code. Some include
confirmed scientific defects; their unchanged status must remain in final
claims. Their follow-up owner is the package orchestrator until a named bounded
work item takes over. They cannot be reported among completed fixes.

## Runtime and observability requirements at the initial review cutoff

The current quiet full suite and any subsequent edits need their final retained
outcome. Earlier broad and wave-local passes do not certify that unfinished run.
Reviewed performance evidence includes46 raster,16 amended Geneva,27 original
profile and45 original Omni gates. Original failed measurements remain retained;
ratified amendments did not convert those failures into passes.

Before package closeout, review the actual rebuilt/restarted development stack
under its real identity, groups, mounts, umask, configuration and orchestration.
Required remaining evidence includes served controller/D-Tale behavior,
maintained mixed-profile export, report/CLI state and download behavior, actual
direct/RQ/model propagation including S01, and retained accepted/failed artifacts
through authorized browsing and canonical archive/restore. The prepared
[archive requirements](runtime_archive_acceptance_requirements.md) and script
have not run for this final gate. Helper browse/ZIP tests do not establish live
browser authorization or all service boundaries.

For S02, [HTTP auth disposition](profile_http_auth_security_disposition.md)
confirms the unchanged cookie-only canonical runner cannot supply the RQ
route's required Authorization bearer by the inspected path. **Actual canonical
runtime outcome remains pending.** Use the existing authenticated
`PlaybackSession(session=...)` API only as separately identified additional
HTTP verification, with unchanged JWT/run-access checks. It must prove each
event's received bytes and failed-marked-seed behavior; it cannot turn a failed
canonical `wctl run-test-profile` into a pass. Retain per-request statuses and
target effects: shell exit0 or the streaming response200 can conceal401s.
Capture any raw cookie-bearing command output privately and redact before
artifact publication; no credential has been inspected by this reviewer.

Artifact observability is consequently **partially verified, final gate open**:
ordinary visible module attempt directories, native failed-work retention,
embedded/companion provenance and actual archive bytes/modes have direct
implementation evidence. Fresh after-restart browsing/download/archival proof
and external profile-store lifecycle remain separately named acceptance rows.
Project ZIP coverage must not be claimed for profile seeds stored outside the
project tree. No hidden-only record or new exclusion is approved.

## Sign-off

- Security reviewer: `freshness_security`, 2026-09-17: **PASS for the scoped
  implementation, verified findings closure and reviewed development runtime
  through `de3a1eba0`**; see the dated closeout for final limits.
- Security gate: **PASS for that scope**. Overall package completion and
  remaining owner documentation/check gates are not declared complete here.
- Package owner: no final closeout acknowledgment is inferred. No risk-acceptance
  signature is requested for the unchanged justified-unresolved inventory.
- Correctness, QA, runtime operations and user workflow acceptance remain
  independent; this sign-off does not replace their results.

## After-restart follow-up: archive operation

The [runtime archive review](runtime_archive_security_review.md) records the
first actual run after verified service recreation: native Geneva outputs,
accepted/failed attempt retention, canonical archive/restore and ordinary helper
list/download checks pass under UID1000/GID993, groups993, umask0022. All10 files
and7 directories retain exact bytes/modes, including0700 attempt ancestry.
Live HTTP authorization and optional external profile receipts remain separate.
The final Python log now independently confirms8924 passed/99 skipped. The
earlier pending statements describe the review point before those results;
other runtime rows and overall security closeout remain pending.

The later live archive browse and both failed-record downloads returned200 with
matching source hashes; see the archive review's follow-up. Actual S02 draft and
promotion preserve both distinct event payloads and private modes, and supported
authenticated `PlaybackSession` HTTP dispatch has exact seed/wire/server parity.
The [S02 runtime review](runtime_profile_security_review.md) records the separate
canonical CLI failure: two401 uploads despite exit0/completion text. It remains
a failed compatibility row requiring explicit final disposition, not a pass.

The later Omni RQ preflight correctly stopped on source metadata drift before
admission. [Independent operational-drift disposition](runtime_source_operational_drift_security_disposition.md)
permits only an explicit acceptance-harness exception for four exact operational
files with original bytes/length/mode, while preserving strict scientific/other
versions, membership, full final hashing and the immutable original baseline.
It does not alter production policy or permit a whole-tree stat-immutability
claim. The source and failed preflight remain untouched.

Final readback confirms the queued Omni result's full manifest SHA and both
successful job trees. Its final full source hash audit meets that precise
exception. Live API/RQ archive preservation and explicit M3 recovery, the actual
shipped Features/public D-Tale workflows and interleaved read-only state evidence
are reviewed in the dated security closeout. Existing CLI/CSV failures and
native/soil/browser/completion limitations remain disclosed there.
