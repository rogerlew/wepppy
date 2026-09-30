# Forest validation

Starting revision: `bbace6023575d29ca00a26f1ad2a7776e957fc8a`.
Candidate: the Git commit containing this evidence, authorized for source
publication after forest validation. No deployment or cluster acceptance claimed.
Production source diff fingerprint is recorded in the security review.
Environment: forest, canonical development Compose `weppcloud`, Python 3.12.14.

## Results

| Command/check | Outcome |
| --- | --- |
| Initial affected climate/batch/RQ suites | 84 passed |
| `wctl run-pytest tests/nodb/test_batch_daymet_multiple_contention.py --maxfail=1 --tb=short` | 35 passed in 21.85 seconds |
| Final combined affected suites | 117 passed in 26.66 seconds |
| `wctl run-pytest tests/nodb tests/rq --maxfail=1 --tb=short` | Interrupted intentionally: 1569 passed, 23 skipped; no failure, not a pass gate |
| `wctl run-pytest tests --maxfail=1 --tb=short` | 10015 passed, 99 skipped, 3558 warnings in 2433.36 seconds; exit 0 |
| `wctl run-stubtest wepppy.nodb.core.climate` | Passed, one module |
| `wctl check-test-stubs` | Passed |
| `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` | Passed, net zero new broad catches |
| Documentation lint and spelling previews | Passed, including final package/developer/canonical updates |
| Independent correctness and security source reviews | Passed, no unresolved local findings |

The NoDb/RQ standalone run overlapped the broad run; it was interrupted to avoid
redundant heavy work and Redis fixture contention. The broad run includes those
paths. Final compatibility and pipeline-failure additions were covered by the
35-case final regression run; these additions followed broad-suite collection.

## Generated artifact evidence

See `2026-09-30_forest_artifact_manifest.json` for exact relative paths, SHA-256,
byte sizes and semantic readback. The fixture supplies remote acquisition only:
real CLIGEN, GDAL sampling, twelve-band PRISM tiles, actual revision numerical
code, ClimateFile parsing and WeppPrepService copy run unchanged.

Daymet and legacy baseline CLI/PRN/source parquet compare semantically equal.
The source parquet has 365 daily rows and preserves mm/day, Celsius and l/day
column units. The PRISM-revised `_1.cli`, legacy `_1.cli`, and actual consumed
`wepp/runs/p1.cli` match byte-for-byte and have 365 parsed rows. `old.cli` in the
manifest is an intentional preexisting sidecar retained by a direct builder;
full-build replacement is separately covered by the state matrix.

The regression module also performs fresh normal controller readback, real
serializer interleavings, relevant-change rejection, current/legacy base
resynchronization, maintenance-lock duplicate exclusion before/after projection
reset, live Climate-token preservation, rollback and unknown-commit recovery.
Working/failed attempt browser downloads and real archive/restore preserve
original bytes; browse authorization fixtures are stubbed and cannot establish
production identity parity. The 12-case mode/spatial/state matrix exercises the
full router. The PRISM-failure full Multiple case preserves committed Daymet,
blocks incomplete WEPP preparation, and omits completion/export/event hooks.

## Limits and scope

No scientific defaults, formulas, queue edges, dependency, lease duration,
worker topology, or stale-write rejection changed. Existing six-hour maintenance
leases remain bounded and unrenewed. Local injected writers establish mutation
boundary failures but cannot attribute the Kubernetes incident writer.

No cluster access, live target mutation, registry publication, deployment,
affected-run repair or incident closure occurred. Cluster acceptance must satisfy
`2026-09-30_cluster_integration_gate.md` and the active ExecPlan.

Code-quality observability was attempted. Radon is absent and its changed-file
comparison does not include this uncommitted working tree; no valid per-file
complexity delta was obtained. Its incidental global reports were restored to
initial content. This observe-only tool limitation is not a correctness gate.
