# S01 live batch dispatcher and worker acceptance

Final status: **PASS** after the retained initial source-metadata preflight
failure and independently reviewed explicit revision2. See
`runtime_omni_sbs_correctness_acceptance.md`, actual job-tree records and the
final source proof in `runtime_omni_sbs_rq_result.json`.

Prepared extension: `runtime_omni_sbs_rq_acceptance.py`. It requires the successful
two-generation direct manifest on the exclusively owned corrected unique copy.
The parent authorized execution after the development restart. This uses the
canonical tracked admission helper and actual existing `batch` queue; it does not
claim HTTP batch enqueue support. The batch `/run-omni` route intentionally only
saves scenarios. No production auth, queue wiring, worker configuration or task
result is replaced. The RQ operator skill and canonical response/controller
contracts informed polling, failure retention and owned-run checks.

```sh
wctl run-python docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_omni_sbs_rq_acceptance.py --native-manifest /wc1/batch/qa-omni-native-20260917-a61f3e/omni-native-manifest.json
```

The exact owned run is
`batch;;qa-omni-native-20260917-a61f3e;;qa-omni-native-20260917-a61f3e-grizzly`.
Canonical `get_wd` and `RedisPrep` identity must agree before admission. The script
requires the prior canonical fork-marker reset and refuses namespace overrides or
an existing queued-attempt directory. It does not clear locks, queues or jobs.

The first submission restores retained low-severity bytes to the same selected
upload path after the direct high-severity generation, including the original
mtime. The tracked dispatcher must produce an actual four-job terminal tree:
dispatcher, scenario worker, compilation and finalization. The queued receipt
must identify the supplied bytes, the worker must execute, generated management
and soil files must change, and five actual watershed/interchange Parquets must
match the direct run of those same input bytes exactly in values and dtypes.
The finalizer must stamp completion. The next submission without another upload
must produce a three-job tree with no scenario worker, report `skipped`, and
preserve numerical artifact hashes and physical versions.

The canonical job-status and job-info functions provide retained polling JSONL,
terminal job-info and actual registered child/dependency records, including worker
identities, times, functions, results and exceptions. A failed/stopped/canceled or
missing tree fails; the two-hour polling deadline does not cancel or retry work.
All working artifacts and failure manifests remain in the disposable root's
`rq-acceptance` directory. Named source versions are checked before admission and
the entire named source is independently rehashed after successful execution.

Cost is one additional full 46-year native generation, its normal compilation and
finalization, a consumed-source dispatcher round, retained child artifacts and a
full 6.37 GB source verification read. Existing restarted workers use their own
configured CPU limits (`WEPPPY_NCPU=6`), not the direct harness's process-local
limit of four. Existing worker result retention is one week. Other acceptance
work may overlap; elapsed times are functional observations, not performance
budget evidence. Live API/browser presentation remains a separate root-owned gate.

## Retained preflight interruption and explicit retry

The initial attempt stopped before any queue admission or upload restoration:
the scheduled access-log compiler physically rewrote byte-identical operational
source files. See `runtime_omni_ttl_attribution.md`, its exact old/current identity
and hash JSON, and the independent security disposition. The original baseline
and failed `rq-acceptance` directory remain immutable. The explicitly reviewed
retry uses:

```sh
wctl run-python docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_omni_sbs_rq_acceptance.py --native-manifest /wc1/batch/qa-omni-native-20260917-a61f3e/omni-native-manifest.json --attempt-name rq-acceptance-revision2 --accept-reviewed-operational-metadata
```

Only `TTL`, `disturbed.log`, `ron.log` and `watershed.log` may differ physically,
and only with their exact original bytes and modes. The harness records those
differences explicitly; it does not claim whole-tree metadata immutability.
All other source files retain strict original versions; complete regular-file
membership and before/after observation guards remain mandatory, and final
verification still hashes every source file. No named source file is changed,
and no scheduler task is stopped or modified.
