# Security review — file dependency freshness

**PASS for the reviewed production changes and bounded development-runtime
acceptance through `de3a1eba0`.** No known unresolved changed-code security
finding remains. This sign-off does not declare the package done, approve a
production deployment, or claim the disclosed existing defects fixed. Root owns
final documentation, QA/check reconciliation and package closeout.

## Metadata, scope and triage

- Independent reviewer: `freshness_security`, 2026-09-17.
- Package: `docs/work-packages/20260916_file_dependency_freshness/`.
- Production revision: `de3a1eba03ba2a0a09beef84e7f3a768d34690fe`.
- Security impact: **high**; dedicated review required for file/path handling,
  native discovery, replay, publication and archive permissions.
- [Final bindings](20260917_security_review_bindings.json) confirm all 48 changed
  Python implementation/stub files still match the reviewed commit and bind 28
  actual evidence files. No production/test edits were made for this closeout.
- The full threat model, valid-state controls, surface checks and per-wave
  commands/source/probe links remain in the
  [implementation ledger](security_review.md). This dated artifact supplies its
  final runtime disposition and supersedes earlier pending security status;
  original failed evidence remains failed.
- Independent counterparts: [correctness consolidation](final_implementation_correctness_review.md),
  [QA consolidation](final_qa_review.md), and their later runtime records below.
  This review does not sign for their remaining owner/checklist work.

## Findings and closure

The ledger verifies closure of SEC-I01/02 (digest growth/collisions), report
RP-SI01–05 and RP-I01/02 (provenance, copied-run selection, access), R-I01–03
(raster discovery authority/read intervals), G-I01–04 (Geneva publication and
valid-state compatibility), P-I01–03 (profile confinement/source priority), A-S01
(archive privacy), O-I01/02 (copy/admission), and the independent O-C01/02
correctness findings (association resurrection/runtime logger). NoDb hydration,
shared digests, controller headers, Features, D-Tale and CLI lineage have their
own linked scoped passes. Earlier failures and the initial automated review/tool
failure remain recorded.

**Unresolved changed-code security findings: High 0, Medium 0, Low 0.** No
`Accepted-risk` security-control exception or inferred owner acknowledgment is
used to close these findings. Optional absence is distinguished from denial;
ordinary supported symlinks/formats and consumer-specific write authority remain
valid. No auth/CSRF exemption, new queue edge, privilege, native service or hidden
artifact exclusion was introduced to obtain a pass.

## Reviewed runtime evidence

| Boundary | Accepted evidence and precise limit |
| --- | --- |
| Restart and identity | All 16 shared-image development services recreated on image `00a3e43a88a5c9079a7e58a8423432d69f22b7b09c0a9288078b67abbca1d3f8`, preserving configured users/groups/mounts. Ordinary execution records UID 1000/GID 993/groups 993, umask 0022. No production deployment. |
| M3 and real source changes | Complete 18-job WEPP pipeline changed ctime/link count on 218 CLI paths with zero changed hashes; the same accepted M3 remained current in API/browser. A normal climate rebuild changed all 218 hashes and made it stale; normal API/RQ rerun restored current state. The short rainfall window is explicitly partial science. [Runtime record](runtime_acceptance.md). |
| Features/D-Tale | Shipped CSV/GPKG profiles exercise real GeoJSON/Parquet/NoDb/units and preserve 16 historical artifacts. Public D-Tale HTTP/browser checks show stale guidance, same-ID relaunch and optional overlay refresh/removal. [Independent runtime QA](runtime_features_dtale_qa_acceptance.md). |
| Geneva/private attempts | Native geometry/alignment, two accepted attempts and one failed candidate survive canonical helper archive/restore with exact bytes/modes across 10 files/7 directories. Live listing and failed-file downloads return 200 with matching SHA. [Security review](runtime_archive_security_review.md). |
| Live API/RQ archive | Archive/restore jobs finish; 545 selected artifacts/84 directory modes and selected ZIP modes match. Restored M3 is stale only from the preexisting physical soil inventory; original soil hashes/SQLite bytes match. Normal M3 rerun restores current API/browser/report/query/downloads. Preservation plus explicit recovery passes; automatic restored currentness does not. [Independent attribution](runtime_archive_restore_soil_qa_review.md). |
| S02 HTTP | Actual capture/promotion and supported authenticated `PlaybackSession` dispatch deliver both distinct event payloads with exact seed/multipart/server SHA. Independent draft/promoted reads preserve bytes, original markers and private modes. Canonical CLI failure is separate below. [Security runtime review](runtime_profile_security_review.md). |
| S01 native/direct/RQ | Two 217-hillslope, 46-year direct generations change real management/soil parameters and watershed output; consumed-upload skips preserve results. A live four-job native tree and three-job skip tree pass, with five direct/RQ Parquets equal in values/dtypes. [Independent acceptance](runtime_omni_sbs_correctness_acceptance.md). This uses tracked developer batch admission, not an HTTP batch enqueue claim. |
| Source preservation | Final queued audit rehashes all 3,916 original files/6,375,730,842 bytes. Four exact operational paths retain original bytes/length/mode despite physical drift; all other 3,912 versions and membership remain unchanged. Original copy and failed preflight remain immutable. [Disposition](runtime_source_operational_drift_security_disposition.md). Whole-tree physical immutability is false. |
| Cache/read runtime | NFS digest probe has zero mismatches across 1,006 operations; three completed atomic NoDb updates reach another process. Interleaved state records a 395-entry working set and zero new digest misses/uncached payloads across 30 calls per project, preserving expected current/stale distinctions. One host/process/workload does not establish cross-host or arbitrary-capacity guarantees. |

Independent broad-log readback records **8,924 passed / 99 skipped**; npm records
**899 tests / 112 suites**. Lint, stub, graph and exception gates are retained by
root. Quiet component budgets and ratified amendments remain separate from
concurrent runtime timings. Earlier timing and harness failures remain retained.
Performance/checklist ratification stays with QA.

## Disclosed unresolved and failed boundaries

The explicit package inventory allowance and ExecPlan decisions retain these
limits; none is counted among completed fixes:

- **PF-R01:** logical soil equality still becomes stale after harmless physical
  changes, including actual archive restore. Strict snapshots/read-only polling
  stay intact; recovery is explicit normal M3 rerun.
- **C01:** main-file checks do not prove nested VRT, directory/chunk or
  archive-child inputs. The small complete RAP pass does not close that limit.
- **B-F01:** an open GL view can mix generations; reload/new-tab guidance is
  recovery, not a coherent snapshot guarantee.
- **C07:** held-receipt native stale reuse is confirmed; a maintained ordinary
  producer failing completion invalidation remains unproven. S01 is separate.
- Wider Roads, AgFields, whole-Geneva preparation, Omni contrast/unavailable
  sources, S01 inherited companions and other native/upload families retain
  their [finite-inventory dispositions](remaining_inventory_disposition_qa.md).
  C02's shipped-profile experiment is complete; arbitrary native closure is not.
- **Canonical profile CLI:** two actual uploads returned 401 for missing
  Authorization while the CLI exited 0/reported success. The authenticated API
  test passes only its own boundary. This existing transport/result defect stays
  failed. Its cookie logger remains unsafe for unredacted use; controlled logs
  were redacted. This review does not approve general credential-output behavior.
- **C08 CSV:** the offered water-balance CSV returns 500 from the preexisting
  unimplemented base iterator. Unchanged baseline route/base classes establish
  attribution; HTML/cached-Parquet delivery pass. CSV remains failed.
  [Independent disposition](runtime_watbal_csv_qa_disposition.md).

Durable limitations live in the RAP README, post-fire operator notes, GL
currentness section, report README's current CSV limitation and
[Profile specification: RQ bearer authentication and outcome verification](../../../../wepppy/profile_recorder/PROFILE_TEST_ENGINE_SPEC.md#rq-bearer-authentication-and-outcome-verification).
Normative byte/provenance, authority, legacy, error, publication and archive
decisions remain in the canonical contracts linked by the implementation ledger.
No scientific guard or authorization was weakened to hide a failed workflow.

## Artifact observability and sign-off

Direct unmocked boundary controls plus restarted native/HTTP/RQ/archive evidence
support the stated authority, valid-state and failure-retention claims. Profile
seeds remain in the external data repository; project ZIP membership or new
browser exposure is not implied. Timestamp-quantum limits, historical reads,
native auxiliary compatibility, existing restore failure semantics and
point-in-time observation limits remain explicit.

- **Security reviewer:** `freshness_security`, 2026-09-17 — **PASS** for the frozen
  implementation and reviewed development-runtime scope.
- **Release recommendation:** no security objection within that scope once root
  completes remaining documentation/check gates. No production deployment is
  authorized or claimed by this review.
- **Package owner:** final sign-off remains with root. No overall package
  completion or owner/risk-acceptance signature is inferred.
- **Follow-up owner:** root retains the disclosed unresolved/failed rows until
  bounded owner/contract tasks take them forward. Their later fixes must preserve
  authority and working behavior, not silently weaken guards or relabel failures.
