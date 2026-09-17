# Development runtime acceptance

Execution date: 2026-09-17 UTC. Runtime acceptance is complete within the explicit
consumer dispositions; this record distinguishes passing boundaries from
justified unresolved findings and preexisting failures. Production was not deployed. Named investigation projects were read-only.

## Delivery and identities

`wctl build weppcloud` produced image
`sha256:00a3e43a88a5c9079a7e58a8423432d69f22b7b09c0a9288078b67abbca1d3f8`.
`wctl build-static-assets` initially failed because host Python lacked Jinja2;
repeating the same command with the repository virtualenv on PATH passed. Both
logs remain. The canonical dev Compose recreation covered all16 shared-image
services, with Redis/Postgres and the proxy retained. Read-only preflight found
all three queues empty before recreation.

[Restart verification](runtime_restart_verification.json) records new container
IDs, image identity and preserved users/groups/mounts for every service. The
first observation retained `download` health starting; the final observation
passes. Before/after service probes retain UID1000/GID993/groups993, umask0022,
Python3.12.14, GDAL3.10.3 and rasterio1.3.10. `/wc1` is NFS on this host; no
cross-host cache-coherence guarantee is inferred.

The final quiet Python suite passed8,924 tests/99 skips in1192.22s. npm passed
112 suites/899 tests and lint. Stub completeness, five stub modules, RQ graph
and changed broad-exception gates pass. The earlier full-suite timing failure
under concurrent image-build/copy load and its isolated pass remain retained.

## Main workflow

Disposable project: `/wc1/runs/qa/qa-freshness-runtime-7e24c8d1`, an independent
3,916-file copy. Inherited asynchronous job markers were cleared using the
canonical destination-only fork helper before submission.

1. Actual climate API/RQ build2019–2021 completed, including native PRISM
   adjustment, CLI parquet/lineage and frequency exports.
2. Actual M3 CLI assessment completed and became current. This bounded three-year
   fixture correctly reports unavailable longer return intervals as a partial
   result; it is not evidence of complete ten-year rainfall estimates.
3. The normal WEPP API pipeline completed all18 actual RQ jobs, including
   hillslope/watershed execution and interchange.
4. All218 CLI paths retained identical SHA-256 hashes while all218 ctimes and
   link counts changed. The same accepted M3 result remained current in state and
   actual browser reload. See [hard-link acceptance](runtime_m3_hardlink_acceptance.json).
5. The supported climate API change to2019–2022 completed; all218 CLI hashes
   changed and M3 became stale in both API and browser. Rerunning M3 created a
   new accepted result and restored current state/browser presentation.

Every browser phase compares rendered expected bundle identity against the
served80-line bundle header; all completed phases match
`2026-09-17T08:03:11Z` with zero page errors. State, request/poll/jobinfo records
and screenshots are retained under `runtime_*`.

## Other changed boundaries

- [Features/D-Tale acceptance](runtime_features_dtale_qa_acceptance.md): actual
  shipped mixed-profile CSV/GPKG exports, cache/semantic controls, public HTTP,
  visible browser stale guidance, same-ID generation reload and optional map
  refresh/removal pass. Named inputs and prior immutable outputs remain unchanged.
- [Geneva/archive review](runtime_archive_security_review.md): actual native
  geometry/alignment, deliberately failed retained candidate, canonical archive
  helpers, exact private directory/file modes and live authenticated downloads
  pass. Its explicit fixture transport is distinct from the main live RQ archive.
- [SBS profile review](runtime_profile_security_review.md): actual HTTP upload,
  capture, promotion and supported authenticated PlaybackSession pass. Both
  distinct event seed hashes equal transmitted bytes and server-stored bytes;
  independent draft/promoted mode and noninterference checks pass.
- `runtime_nfs_digest.json`:1,006 real metadata/content operations pass, including
  hardlinks, touch, chmod and1,000 equal-size/restored-mtime writes. No whole-stat
  collisions were observed on this NFS probe; earlier overlay/ext collision
  evidence remains separate.
- `runtime_nodb_processes.json`: three ordinary atomic setter updates propagate
  to a persistent reader in another process with matching payload/name and
  recorded disk mtime/size. Concurrent acquisition races remain covered by
  independent implementation tests, not this sequential runtime probe.

## Existing runtime failures retained

- Canonical `wctl run-test-profile` sends cookies without the bearer header
  required by the recorded rq-engine upload route. Both requests returned401,
  yet the CLI exited0 and reported success. This is a confirmed existing auth/
  result-reporting defect, not a passing canonical replay. The supported
  authenticated-session result above validates S02 bytes without changing auth.
- Water-balance CSV returned500 because the offered route reaches an unimplemented
  `ReportBase.__iter__`. [Independent baseline attribution](runtime_watbal_csv_qa_disposition.md)
  confirms the adapter defect predates this work. C08 HTML and actual
  provenance-bearing cached-Parquet download pass; C09 HTML/CSV and all five M3
  result downloads return200. Complete statuses remain in
  `runtime_reports_after_wepp_complete.json`; its overall check intentionally fails.

## Archive and Omni acceptance

Live API/RQ archive and restore both finished. All545 selected files and84
directories retain exact bytes/modes; the ZIP mode check also passes. Restored
M3 is stale solely because of the existing physical soil inventory (PF-R01).
The independent soil attribution verifies all7 manifest-bound source hashes and
SQLite main/WAL/SHM against ZIP members. An ordinary API/RQ rerun restores
current API, run-page, actual report-page/query and download results. Recovery
creates a new accepted result; the original archive and stale observation remain.

Both direct Omni46-year native generations and consumed-upload skips pass,
with changed actual management/soil/watershed output on changed upload. Live
RQ execution finishes four jobs and reproduces the direct numerical outputs;
consumed-upload admission finishes three jobs without another scenario worker
or numerical change. See [final Omni acceptance](runtime_omni_sbs_correctness_acceptance.md).
The native project has217 hillslopes and one watershed; this does not certify
a full multi-OFE model run or arbitrary indirect native readers.

## Source operational metadata observation

The direct native audit rehashed all3,916 named source files successfully. A
later live-RQ preflight stopped before mutation on physical drift in TTL and
three logs. All four retained original bytes/lengths/modes; other3,912 versions
and membership remain exact. Scheduler job/code/timing provide strong evidence
for normal access-log compilation and NoDb logger touches, not syscall-level
attribution. The independently reviewed, opt-in RQ-only exception preserves
original manifests and the first failure and requires a final complete hash
audit. That final audit passes for all3,916 files/6,375,730,842 bytes; the
four operational physical differences remain explicitly recorded. No source file was repaired or rebaselined. Whole-tree physical
immutability is explicitly false. See
[runtime source disposition](runtime_source_operational_drift_security_disposition.md).

## Interleaved state observation

[Actual two-project observation](runtime_interleaved_state.json) records30
alternating requests per project: warm means739.48/862.19ms, first calls
2.225/2.648s. The production digest cache retains395 of512 entries, with12,840
additional hits and zero new misses or direct uncached digest payloads. This
passes the bounded-cache/warm-read obligation, not a whole-state latency
deadline or a claim of zero filesystem reads. Eviction is covered by separate
component probes. The recovered primary project is current; the copied Omni
parent's inherited M3 is stale, as recorded without repair.

Final dispositions and independent reviews are linked from
[implementation disposition](implementation_disposition.md). Known PF-R01,
indirect-reader, browser-generation and completion-receipt limits remain
explicit; production deployment is outside this execution.
