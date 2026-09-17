# Operational source metadata change during runtime acceptance

The initial queued acceptance stopped before upload restoration or queue
admission. Its immutable failure is `runtime_omni_sbs_rq_initial.log` and
`/wc1/batch/qa-omni-native-20260917-a61f3e/rq-acceptance/manifest.json`.
The original copy manifest has not been edited or rebaselined; no named source
file has been restored, touched or repaired by this investigation.

Direct native acceptance finished at08:21:04 UTC after its complete original
source verification. The subsequent read-only preflight started at08:21:48 and
reported changed `TTL` metadata. `runtime_omni_ttl_observations.json` retains old
and new physical identities, exact original/current hashes and TTL payload.
Membership is unchanged. Only four of3,916 source file versions differ; all four
still have the exact original SHA-256. The remaining3,912 versions are equal.

| Path | Actual physical change | Current modification time UTC |
| --- | --- | --- |
| `TTL` | Atomic replacement, identical427-byte JSON |08:21:34.475347 |
| `ron.log` | Same inode, touched, identical bytes |08:21:30.001319 |
| `disturbed.log` | Same inode, touched, identical bytes |08:21:30.009319 |
| `watershed.log` | Same inode, touched, identical bytes |08:21:30.016320 |

The scheduler trace records `access_log_compile` admission at08:21:17.
`runtime_omni_ttl_batch_logs.txt` records actual job
`3f8a415d-e8dd-4469-b785-44fe335be797`,
`wepppy.rq.project_rq.compile_dot_logs_rq`, running08:21:27–08:21:35.
This brackets every observed physical change. The unchanged TTL payload retains
`last_touched_by=access_log` and its earlier00:36:57 access/update values.
Attribution is strongly supported by this timing and the concrete writer code;
no process-level syscall tracing was collected.

Concrete existing writer semantics explain the observations:

- `compile_dot_logs._load_run_metadata` hydrates Ron and Watershed and reads
  `ron.has_sbs`, which discovers the Disturbed owner. NoDb `_init_logging`
  opens each controller log and calls `Path(log_path).touch(exist_ok=True)`.
- The compiler calls `touch_ttl` for recorded accesses, including historical
  accesses. `run_ttl.touch_ttl` invokes `_write_payload` even when the access is
  not newer; `_write_payload` atomically replaces the TTL file.
- `docker/scheduled-tasks.yml` schedules this canonical task on the batch queue
  after the restarted scheduler's initial delay. No new source HTTP access is
  needed to cause these identical-byte rewrites.

The acceptance scripts use source `stat`, inventory and binary reads only. The
copier never hydrates a source controller. Native owners and GDAL open only the
independent rebased copy. The queued attempt's only resolver call before failure
is canonical `get_wd` for the exact unique batch run, whose result is checked
against the copy before the source preflight.

The independent security disposition approved the bounded retry: an explicit RQ-only
allowlist for these four operational files may tolerate physical-version changes
only while exact original bytes and permission mode remain equal. Scientific
files and all other paths retain strict original versions; membership and final
full-source hashes remain checked. The result must list physical exceptions and
must not claim all metadata remained unchanged. Original failure and baseline
remain immutable; any retry uses a new explicit attempt directory. This proposal
does not authorize stopping the scheduler, touching named inputs or hiding an
actual source content change.
