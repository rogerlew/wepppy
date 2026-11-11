# Focused validation receipt

Contract checkpoint: `d6796407f29b4dd7b05031ed89efa416b13a5665`.
Implementation revision: pending candidate commit; these receipts test its working tree.

- Core/API/NoDb/startup compatibility: 156 passed.
- Expanded observability/profile/migration/AgFields/PATH-CE/UserSum compatibility:
  221 passed (`20261111_compatibility_output.txt`).
- Final-output adapters: 47 passed (`20261111_artifact_canaries_output.txt`),
  including actual Roads NoDb JSON, AgFields integration failure JSON, Omni
  contrast JSON, cache status JSON, delayed OpenET warnings, EU publication,
  playback stdout/results, migration logs/JSONL, and direct response bypasses.
- Final focused run: 47 passed (`20261111_focused_output.txt`), including
  Geneva batch JSON, RUSLE optional reports, BatchRunner metadata, successful
  RQ result payloads containing errors, and playback ADMIN/Wojak process sources.
- SSURGO preparation, PATH-CE sweep CSV and real NoDb failure status passed
  in the 46-test successful prefix of the model run. The final Geneva test's
  missing constructor `code` keyword was corrected and passed in the final run.
- Actual disposable Redis failure readback retains failed state, traceback/meta/
  result sanitation, and original callback/handler exception types. Successful
  partial-error jobs retain finished state and sanitized result dictionaries.
- Process probes cover uncaught/thread hooks, failing stderr, worker-pool
  ForkProcess, PFDF failure JSON, NoDb/SSURGO spawn pools and exit semantics.
- Container PASS: `20261111_container_receipt.json` and captured output.
  Reproduce: `python tests/docker/run_safe_traceback_probe.py`; existing image,
  UID 1000/GID 993, mode 0444 read-only production paths, network none, no
  shared-service mutation, current-file replacement observed by one process.
- Benchmark: 24 synthetic sources, 8194 characters, 100 renders: median
  3.623 ms, max 3.957 ms. 10,000 normal logs: 257.66 ms, zero source reads.
- Broad-exception enforcement PASS; existing allowlist line anchors refreshed
  after import insertion. No broad exception behavior was introduced outside
  documented sanitizer/formatter output boundaries. Code quality is observe-only.

All pytest invocations use `wctl run-pytest`. Disposable Redis opt-in argument:
`--f5-redis-socket /workdir/wepppy/.pytest_cache/f5-disposable-redis/redis.sock`.
The exact full pytest command intentionally omits that opt-in; direct Redis
acceptance is established above with a sentinel-verified isolated server.

Failed development probes were repaired: fixture import/profile ordering,
worker `for_pool` adapter signature, spawn initializer expectations, bounded
regex behavior, and new test harness constructor/state expectations. No failure
was relabeled as a pass. Historical output and generic command transcripts are
not scrubbed. Production deployment has not occurred. Full M5 gates pending.

Final review regressions: config-update conflict response passes with unavailable
required secret source (17 tests); browse 4xx dict/list/text responses preserve
status and headers (3 tests); batch-create HTML errors (3 route tests); Mapping
including UserDict exception log arguments and owned-source process probes
(5 tests). These close the final compatibility/import/producer findings.

QA's final schema finding is closed: browse HTTP dict/list bodies retain JSON
content type, status and headers when a required source fails. All six normal/
fail-closed shape cases pass (`20261111_browse_failclosed_output.txt`).
`wctl check-test-stubs` passes. Playback subprocess evidence proves profile
metadata/formatting; service early-install placement is source-reviewed.
