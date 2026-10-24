# Environment probes

Scope: isolated validation only. Production `wepp1` is a read-only source; no production jobs, writes, restarts or deployment. Evidence collected by `/root/environment_validation` on 2026-10-23 UTC.

## Host and storage baseline

| Environment | Identity / mount | Evidence limit |
| --- | --- | --- |
| forest host | workspace `/workdir/wepppy`; `/wc1` NFS4 from `10.0.0.2:/`; 893 GiB free at inventory | Development NFS, different server from production. |
| forest weppcloud + rq-worker-batch | uid 1000, gid 993; web umask 0022 | Same local service identities for cross-container test. |
| wepp1 rq-engine | uid 1002, gid 130; production source `/geodata/wc1/runs/gl/glaciated-waterfront` | Identity differs; no claim of complete production parity. |

Production source size is 54 GiB: 45 GiB archives, 8.5 GiB climate, 320 MiB `manifest.db`, remaining scientific/project artifacts comparatively small. No source symlinks were found at depth two. The isolated copy excludes archives and manifest database sidecars; scientific files are copied, never hardlinked or aliased to production. Exclusion means this copy does not validate original archive members.

## Real NFS guard exclusion

Probe used the actual `catalog_lifecycle_guard` and an explicit managed root under `/wc1/query-catalog-validation/20261023/lock-probe`. Both processes used identical root/namespace/coordination configuration through `wctl docker compose exec -T`.

- `weppcloud` holder: uid 1000/gid 993; acquired after 0.0073 s; held for 4 s.
- `rq-worker-batch` contender: uid 1000/gid 993; acquired after 3.2231 s.
- Both processes exited 0; contender assertion required more than 2.5 s waiting.
- Scratch driver: `/tmp/qcat_nfs_probe_driver.py`; raw record `/tmp/qcat-nfs-probe-result.json`.

This demonstrates separate-container, same-host shared-NFS exclusion. It does not prove cross-host production NFS locking, production UID/GID parity, restore/delete integration or complete browser/model behavior; those gates remain separate.

## Isolated Mill Creek copy

Read-only rsync source: `wepp1:/geodata/wc1/runs/gl/glaciated-waterfront/`.
Initial target: `/wc1/query-catalog-validation/20261023/runs/gl/glaciated-waterfront/`.
Transfer uses compression, normal independent destination files, no owner/group inheritance, `--safe-links`, and exclusions `archives/`, `manifest.db`, `manifest.db-shm`, `manifest.db-wal`.

Copy completed successfully (rsync exit 0): 9,270,055,877 logical bytes, 4,559 regular files, 51 directories; 4.5 GiB allocated on compressed ZFS. A complete destination walk found no symlinks. The independent copy was renamed to `/wc1/runs/qc/qcat-mill-creek-20261023`; 14 NoDb files were rebased using existing `_rebase_fork_nodb_text`, preserving model parameters. The clone retains before/after NoDb hashes in `qcat-validation-copy.json`. Source files were untouched.

## Cross-host lock defect and candidate correction

`forest1` exposes the same `/wc1` storage as local ZFS (`zfs_pool0`), whereas forest accesses it over NFS4. The shared scratch ready marker was visible on forest1. Both contender/holder container identities were uid1000/gid993.

- **Failing actual-guard probe:** forest web core `catalog_lifecycle_guard` held the inode for 5 s using `flock`; forest1 worker using local `flock` acquired in **0.0013 s** while the holder remained active. This proves the initial implementation does not exclude NFS-client and storage-server-local users of the same inode.
- **POSIX candidate probe:** repeat with forest1 contender using `lockf`; it waited **4.4831 s**, proving POSIX record locking interoperates with the NFS lock representation in this topology.
- Raw retained scratch records: `/tmp/qcat-crosshost-probe-result.json`, `/tmp/qcat-crosshost-lockf-probe-result.json`; drivers `/tmp/qcat_crosshost_probe.py`, `/tmp/qcat_crosshost_lockf_probe.py`.
- Parent/publication agent notified. Required implementation correction: interoperable POSIX record locks plus per-process thread serialization; actual updated-core and thread probes are recorded below.

The candidate probe does not yet count as final implementation validation. It explains why a same-host/container-only green test was insufficient.

## Updated implementation validation

The corrected core uses POSIX `lockf` plus a per-process keyed reentrant thread lock. The same source (SHA256 `5551eb1d4956f5bd306d6ee86a7e1a6480029e7e08b5638e031b7b5e13bc80bd` at probe time) ran on both sides. To avoid changing forest1 application files, the contender loaded this exact source from stdin into an in-memory module.

- Forest NFS-client web holder held the actual guard for 5 s; forest1 server-local worker contender waited **4.375527 s**. Both exited successfully with uid1000/gid993.
- Two threads in one process: nested same-thread guard succeeded; a second thread waited **2.002313 s** for the first holder's 2 s critical section.
- Drivers: `/tmp/qcat_crosshost_actual_core.py`, `/tmp/qcat_thread_probe.py`; cross-host result: `/tmp/qcat-crosshost-actual-core-result.json`.

These checks validate the corrected primitive across the actual forest NFS/server-local topology and within a threaded process. Full production identity, workflow, and lifecycle parity remain separate rollout gates.

## Authenticated Mill Creek submission and catalog execution

Actual FastAPI TestClient request exercised JWT verification, scoped run authorization, real payload mutation and Redis enqueue. The process locally redirected queue constructors to unique real queues `qcat-mill-creek-model-20261023` and `qcat-mill-creek-catalog-20261023`; no live queue consumer configuration changed. Async settings and managed-root configuration applied only to the probe process.

- Unauthenticated request: **401**.
- Run-scoped signed service-token request with existing `initial_sat` and `wepp_261010`: **200 in 0.636588 s**, including actual `soils.dump_soils_parquet` execution.
- Exactly one model job and one catalog maintenance job queued; one durable catalog receipt existed at return.
- Actual isolated RQ catalog worker published **92 entries**, including `soils/soils.parquet`, and acknowledged all pending receipts.
- Actual `job_info` tree returned model job `9e59da85-e50a-4d5c-bfa3-5033fb89d466` in queued state before execution.
- Fresh source/clone soil Parquet comparison: **1,908 rows**, equal schemas; after sorting by `topaz_id`, every column is equal except the intentionally rebased `soils_dir` path.
- Drivers: `/tmp/qcat_mill_creek_prepare.py`, `/tmp/qcat_mill_creek_submit.py`; raw submission log `/tmp/qcat-mill-creek-submit.log`; clone result `qcat-validation-submission.json`.

The real unchanged 184-year WEPP261010 pipeline is running with `WEPPPY_NCPU=2`, a unique SimpleWorker consuming only these two queues, and optional Discord completion notification disabled in the harness. Its 18 real model jobs were inspected through `job_info`; test job metadata retention was extended to one day. Final model and report acceptance remains pending. This is service-token API acceptance, not browser-session acceptance or complete production identity parity.

## Submission variants and malformed catalog finding

Three independent small project copies retain actual NoDb, soil, watershed and DEM inputs. Existing fork helpers rebase paths and clear inherited async job markers; scientific values are unchanged. Real scoped-token submissions each queued one model job and one catalog request:

| Catalog before submission | HTTP | Request elapsed | Maintenance result |
| --- | --- | --- | --- |
| Missing | 200 | 1.101639 s | 58 entries, no pending receipts |
| Malformed JSON | 200 | 0.904447 s | Failed JSON decoding; receipt retained |
| Populated | 200 | 0.839299 s | 92 entries, no pending receipts |

The malformed maintenance failure occurs while loading catalog JSON before the refresh failure-state boundary; parent and publication owner notified for disposition. This confirms producer responsiveness but does not establish automatic malformed-catalog recovery. Early fixture attempts correctly returned 409 when watershed artifacts or inherited model-job markers were incomplete; corrected copies use actual fork metadata reset and required artifacts. No failed fixture result is counted as application failure.

## Native GIL responsiveness on actual NFS

Five direct native scans of the stable copied climate directory took 0.040–0.042 s each. A concurrent Python heartbeat advanced 37–39 times per scan; maximum inter-heartbeat gap was **0.001157 s**. The same test across the whole model tree took 0.261–0.313 s per scan with 241–288 heartbeats; that second tree had concurrent unsupported soil-input writes and therefore proves responsiveness only, not snapshot consistency. Both probes ran under uid1000/gid993 on forest's NFS4 mount.

## Actual producer death before durable receipt

A separate copied soil project on the same NFS mount ran the real `Soils.dump_soils_parquet` implementation in a child process. A harness hook killed that child with **SIGKILL** exactly at the call to `request_catalog_refresh`, after artifact atomic replacement and file/directory fsync but before any receipt creation.

- Child return code **-9**; the replacement Parquet contained **1,908 rows**, changed modification time, and **zero pending receipts**.
- Real inventory reconciliation visited three scope directories and admitted one maintenance job.
- The isolated real Redis/RQ worker published the repaired catalog; required-path consumer validation succeeded and pending receipts returned to zero.
- Driver `/tmp/qcat_kill_boundary.py`; independent fixture `/wc1/query-catalog-validation/20261023/kill-boundary`; raw log `/tmp/qcat-kill-boundary.log`.

Structured measurements for these probes are retained in [environment_probe_results.json](environment_probe_results.json).

## Model harness correction

The first stdin-launched worker caused Python spawn to reject `<stdin>`; existing soil preparation recovered using a fork executor. This was a harness defect, not a catalog failure. With parent authorization, the owned worker and its three helper processes were stopped as one verified process group; their disappearance was checked before requeuing the same soil job. The corrected worker runs an actual file with a `__main__` guard and `WEPPPY_NCPU=8`, retaining all 184 scientific years and model values. The original warning log remains `/tmp/qcat-mill-creek-worker.log`; corrected log is `/tmp/qcat-mill-creek-worker-file.log`.

## Malformed catalog disposition and independent rerun

Publication owner corrected malformed derived-catalog handling: log corrupt-catalog diagnostics, rebuild from authoritative sources, verify before replacement, and preserve original corrupt bytes if repair fails. A fresh process independently re-ran the actual failed malformed scope using real Redis/RQ on NFS. Maintenance job `query_catalog_refresh_511dfb29-bf76-4c95-99e1-2bd67934f7ee` rebuilt **59 entries**, acknowledged receipt `e6c663b3-64f2-4abf-a775-57b2b38f0257`, and returned **current with zero pending**. The original malformed request had already returned 200 in 0.904447 s. This closes automatic repair evidence for that failure without claiming a new browser login or production identity match.

## Private test ownership and authorization

Flask's legacy authorization treats filesystem-only runs without DB owners as public. The local environment was verified before mutation: Docker Compose `wepppy-postgres` service, PostgreSQL 16, and application DB endpoint `postgres:5432/wepppy`. The six probe-created run IDs were associated with the existing dedicated local `dev-agent` account via canonical `user_datastore.create_run`; no users, passwords or roles changed. No `PUBLIC` markers exist. Anonymous report requests now return **404**, the canonical run handler's deliberate masking of forbidden 403 responses. These owner records must remain while retained canonical test directories exist; remove only these dedicated test Run rows when those directories are retired.

A genuine password/CSRF login attempt correctly encountered the existing Cap.js challenge requirement. No CAPTCHA, password or auth configuration was altered; login challenge completion is outside this probe's claims. Subsequent report probes use an explicitly seeded real Flask session for the existing dedicated account and retain normal ownership, role and route authorization.

The authenticated run-summary route returned **200 in 0.353443 s** during model execution and rendered the real observed count **751 hillslopes ran**. This verifies authorization plus live report artifact readback; it is not the final 1,908-hillslope completion assertion. `/tmp/qcat_session_report.py` uses the actual Flask app, real Redis-backed session, dedicated account lookup and route authorizers; only session establishment is injected by the test client. The CAPTCHA login flow is expressly not exercised.

## Guard rerun after implementation corrections

After core corrections, source SHA256 `1f19401a875246e621fdeea398cf4f42d6fb288eef591ad5d611c19b6fd3dcd5` was independently exercised again across forest NFS and forest1 server-local storage. Actual-core contender waited **3.701250 s** behind the five-second holder; both exited 0. The same-process second thread waited **2.001937 s** with nested same-thread guard success. This supersedes the earlier core revision for guard acceptance, while preserving the original failing `flock` evidence.

## Scientific executable parity

Read-only SHA256 comparison against wepp1's `docker-rq-engine-1` confirms the local scientific binaries are byte-identical: `wepp_261010_hill` is `d8ea3a07a29ef1e754c5362bd7931cc3a93486d75faa32df5c5f2e821c22d698`; watershed/base `wepp_261010` is `1dd1ca75cf53f9a0606cf5a598312d4e680e161df631156360d4a20dbcb6f17e`. This closes scientific binary-version uncertainty; it does not remove the separately documented production identity, storage or Python/native deployment parity gaps.

## Full scientific execution progress and worker source boundary

All **1,908 hillslopes completed successfully** with the unchanged 184-year inputs and verified WEPP261010 binary; the hillslope RQ stage took **1,012.850306 s**. The worker honored a warm shutdown only after that stage, leaving model child processes uninterrupted. Completed preparation/hillslope tasks used the source snapshot imported at 20:45 UTC; later catalog permission/repair corrections were not loaded in that process. A fresh worker resumed the existing unique queue at 21:08 UTC for watershed preparation, interchange, watershed execution and finalization. Source file hashes and the loaded Rust extension hash are retained in structured evidence. The actual extension hash is `7908a4fa667b149f4eee5a827dfb65c39c0c080369459b659c68cec26f411811`; the separately captured Python wrapper hash is not the extension identity.

Full watershed/postprocessing/report completion remains pending at this checkpoint; the partial job tree is retained at the clone's `qcat-validation-hillslopes-complete.json`.

## Final-source producer and catalog permission rerun

Fresh-process actual authenticated requests repeated all three owned small variants after implementation corrections: missing **200 / 1.100435 s**, malformed **200 / 0.891383 s**, populated **200 / 0.821492 s**. Real maintenance completed all three with **zero pending receipts**. Repaired malformed catalog retained **0600**; populated catalog retained **0640**; new catalog mode **0644** matched umask. All never-executed variant model jobs were canceled after queued-state verification, retaining the full submission result evidence.

Soil artifact replacement normalized 0640 to 0644; comparison with `git show HEAD:wepppy/nodb/core/soils.py` confirmed this is unchanged preexisting soil-writer policy. It is not a catalog-task regression and no soil permission policy was changed.

A second worker, `qcat-mill-creek-watershed-20261023`, was authorized after resource measurement to consume **one job only** from the same isolated model queue. The existing DAG already permits watershed execution alongside hillslope interchange. Source hashes matched the fresh primary exactly. The secondary exits after its dependency-ready watershed job; remaining catalog work and finalization remain with the primary worker. No global consumer configuration or dependency edges changed.

Native PASS conversion atomically published `H.pass.parquet`; independent Parquet footer readback found **128,229,048 rows**, **1,908 row groups**, and **2,930,862,555 bytes**. Event-by-event, element and hillslope-loss products subsequently published. This is intermediate artifact evidence only; soil/water conversions and watershed completion remain active and final report assertions have not yet run.

## Completed hillslope products; watershed still active

At 21:47 UTC, fresh-source hillslope interchange and `totalwatsed3` completed successfully. All six atomic H.* products passed independent Parquet footer readback: PASS, soil and water each contain **128,229,048 rows / 1,908 row groups**; event-by-event contains 8,552,063 rows; element 16,426,060; loss 9,540. The primary worker exited cleanly with **zero pending catalog receipts**. Remaining postprocessing and finalizer jobs correctly remain deferred behind the active watershed branch.

Watershed pass assembly read all 15.794 GB of hillslope input and wrote 22.321 GB before actual routing began around 21:46 UTC. Routing reached year 3 around 21:48; this initial rate suggests hours for all 184 unchanged years. This is an observed scientific workload duration, not evidence of catalog blocking. Full workflow acceptance remains open until watershed, finalization and the prepared authenticated report/download assertions complete.

The bounded `/tmp/qcat_completion_supervisor.py` polls only watershed job `65a2df6e-acca-4223-8c1a-f053733e68a7` every 30 seconds. On success it invokes the existing unique-queue primary worker, then the final Parquet/query/live-download and authenticated Flask report validators. Unexpected job status or any validator failure stops explicitly. Logs are `/tmp/qcat-completion-supervisor.log`, `/tmp/qcat-mill-creek-finalization-worker.log`, `/tmp/qcat-final-artifacts.log`, and `/tmp/qcat-final-session-reports.log`. This supervisor does not consume shared queues or change service configuration.

Read-only inspection at 21:51 UTC confirmed the active watershed RQ timeout is **43,200 seconds (12 hours)**, started 2026-10-23 21:14:19 UTC, with computed deadline **2026-10-24 09:14:19 UTC**. The measured 2–3 hour remaining estimate fits that existing budget. No timeout or queue policy was extended or altered. The watershed worker and completion supervisor remain running.

## Completed hillslope consumer checks and scientific report failure

The actual catalog-backed `H.loss.parquet` query returned **9,540 rows and 1,908 distinct hillslopes**. Authenticated run-summary returned **200 / 0.159691 s**, reporting all **1,908** hillslopes; anonymous access remained **404**. The live run-scoped browse download returned **200** and exactly matched all **3,837,828 bytes** of the local H.loss artifact. Catalog receipts remained **zero pending**. These are hillslope-only checks while watershed execution continues; channel and outlet assertions were not attempted.

The actual `HillslopeWatbalReport` consumer **failed** with `ValueError: duplicate hillslope daily OFE observation`. Inspection of the first H.wat row group found repeated `(wepp_id, ofe_id, year, julian)` observations beginning at simulation year 104. Crucially, raw binary output `H1.wat.dat` itself contains two distinct observations for OFE 1 / day 365 / simulation year 104, with different precipitation and storage values. Exact source rows are retained in structured evidence. This is a real scientific-output/report acceptance failure; it must not be represented as successful report validation or silently deduplicated. Catalog publication did not invent these raw duplicate dates. Baseline causal attribution beyond that observation is not established.

The deferred `_run_hillslope_watbal_rq` stage calls this same report constructor, so downstream pipeline completion is expected to encounter the same failure. The full worker/supervisor remain running without bypasses, source changes, timeout extensions or validation weakening. Driver `/tmp/qcat_hillslope_partial.py` retains the failed report probe; `/tmp/qcat_hillslope_independent.py` runs the independent successful query/run-summary/download subset.

A read-only wepp1 baseline check found the original source `wepp/output` directory empty and no `H1.wat.dat`. Its only archive is a 45 GB `.zip.tmp` file; it was not extracted or scanned. Therefore original raw-output comparison is unavailable and the report failure is not labeled a proven preexisting defect.

## Terminal outcome — full scientific acceptance failed

The unchanged watershed job failed at **2026-10-23 22:59:54 UTC**, after **6,335.000811 seconds**, during simulation year **100**. The raw model error ends:

```text
SIMULATION YEAR =         100
PASS components error: SOURCES3 date mismatch
Note: The following floating-point exceptions are signalling: IEEE_UNDERFLOW_FLAG IEEE_DENORMAL
STOP 1
```

The actual job tree reports watershed failure, nine successful preceding child stages, and seven downstream stages still deferred, including finalization. Catalog receipts remained **zero pending**. The full model/report acceptance criterion therefore **failed**; channel/outlet/final reports were not validated. Completed hillslope artifact, catalog query, authenticated run-summary and exact live-download evidence above remains valid within its stated partial scope.

The primary and one-job watershed workers exited normally (process exit 0; RQ still correctly records watershed job failure). The completion supervisor observed failed status and exited **1**, before starting any finalization worker or final validators. Process inspection found no owned workers/supervisor left running; RQ worker discovery found no owned registered workers, and both isolated queue lengths were zero. No scientific fix, rerun, dependency bypass or timeout alteration was attempted. Retained private fixtures and their dedicated owner associations remain available for diagnosis.

Structured evidence includes the complete terminal job tree, exact error excerpt, worker/supervisor exit results, and SHA256 hashes of model error, sample raw H.wat, totalwatsed3, terminal job-tree file and harness logs. `pw0.err` SHA256 is `2a8e29641c1db74e1378624c997ff0f8607445686671c67ed1eae29753d814dc`.

### Attribution boundary

The paired native build includes preserved calendar/HBP edits. Read-only inspection shows the calendar edit exposes the existing Gregorian leap-year predicate to sibling modules; HBP edits change HBP calendar handling. This actual `pw0.run` instead points the WEPP watershed executable directly at raw `H*.pass.dat` inputs and `pass_pw0.txt`, with no HBP or derived Parquet input. Earlier owned-process file-descriptor observations also showed the binary itself reading those 1,908 raw PASS files and writing the master PASS. Python `run_watershed` launches that binary with the run prompt directly.

This establishes the observed input path; it does **not** establish original-source baseline behavior or prove a causal relationship between the watershed SOURCES3 failure and the independently observed duplicate raw H.wat dates. Both are retained as distinct scientific acceptance failures. Production identity/mount/orchestration parity and CAPTCHA login completion also remain unproved. The earlier running/pending statements in this ledger are chronological checkpoints superseded by this terminal outcome.
