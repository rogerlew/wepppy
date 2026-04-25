# redis_nodb_cache_stress

Stress harness scaffold for `redis_nodb_cache_client` behavior in `wepppy/nodb/base.py`.

This harness targets Redis **DB 13** (NoDb cache), uses a configurable mixed workload (`get`, `set`, `mutate`, `mutate_seq`, `delete`, `scan`), and writes JSON evidence reports suitable for `wepp1`/`wepp2` comparison.

## What This Includes

- `run_harness.py`: concurrent workload runner + JSON report writer.
- `fixtures/*.json`: built-in payload fixtures shaped like real `.nodb` content (`watershed`, `climate`, `soils`).
- Optional payload corpus support: append real `.nodb` files at runtime via `--payload-corpus-dir`.

## Safety Model

- Defaults use synthetic run ids (`stresscache-*`) and generated cache keys under `/wc1/runs/...`.
- Workload is scoped to Redis DB 13 by design (`--redis-db`, default `13`).
- No filesystem writes to run directories are performed.
- Harness does **not** call `clear_nodb_file_cache()` on live run ids.

## Quick Dry Run

```bash
python tools/perf/redis_nodb_cache_stress/run_harness.py \
  --target-profile local \
  --use-wepppy-resolver \
  --dry-run
```

## Local Run

```bash
python tools/perf/redis_nodb_cache_stress/run_harness.py \
  --target-profile local \
  --use-wepppy-resolver \
  --threads 32 \
  --duration-seconds 120 \
  --runid-count 150
```

## Run Inside Stack (`rq-worker`)

When running from a worker container, use the worker venv interpreter explicitly:

```bash
wctl docker compose exec rq-worker sh -lc \
'/opt/venv/bin/python /workdir/wepppy/tools/perf/redis_nodb_cache_stress/run_harness.py \
  --target-profile local \
  --use-wepppy-resolver \
  --threads 8 \
  --duration-seconds 12 \
  --runid-count 80 \
  --operation-weights "get=30,set=20,mutate=20,mutate_seq=20,delete=5,scan=5" \
  --mutate-seq-burst-length 7 \
  --mutate-hot-key-fraction 0.15 \
  --max-failure-rate 0.05'
```

Notes:
- `python` in container exec may resolve to `/usr/local/bin/python` (without the worker deps).
- `rq-worker` runtime uses `/opt/venv/bin/python`, which includes `redis` and matches worker behavior.

## Production Run (`wepp1`)

Run on host `wepp1` from `/workdir/wepppy`:

```bash
hostname
python tools/perf/redis_nodb_cache_stress/run_harness.py \
  --target-profile wepp1 \
  --use-wepppy-resolver \
  --threads 64 \
  --duration-seconds 300 \
  --operation-weights "get=35,set=25,mutate=20,mutate_seq=10,delete=5,scan=5" \
  --runid-count 300
```

Run `wepp1` and `wepp2` sequentially, not at the same time, unless you are intentionally testing simultaneous host pressure.

## Production Run (`wepp2`)

Run on host `wepp2` from `/workdir/wepppy`:

```bash
hostname
python tools/perf/redis_nodb_cache_stress/run_harness.py \
  --target-profile wepp2 \
  --use-wepppy-resolver \
  --threads 64 \
  --duration-seconds 300 \
  --operation-weights "get=35,set=25,mutate=20,mutate_seq=10,delete=5,scan=5" \
  --runid-count 300
```

If resolver-based URL resolution is not appropriate for your host, use one explicit source instead:

```bash
python tools/perf/redis_nodb_cache_stress/run_harness.py \
  --target-profile wepp2 \
  --redis-url "redis://:<password>@redis-host:6379/9"
```

The harness rewrites the URL path to DB `13`.

## Using Real Project Payloads

Append a real `.nodb` corpus without committing payload data:

```bash
python tools/perf/redis_nodb_cache_stress/run_harness.py \
  --target-profile wepp1 \
  --use-wepppy-resolver \
  --payload-corpus-dir /tmp/nodb-corpus \
  --payload-corpus-limit 50
```

Expected corpus shape:

- any directory containing `.nodb` files recursively
- relative file paths are preserved in generated cache keys

## Key Options

- `--operation-weights "get=35,set=25,mutate=20,mutate_seq=10,delete=5,scan=5"`
- `--mutate-seq-burst-length 5` (number of sequential writes against one key per `mutate_seq` op)
- `--mutate-hot-key-fraction 0.10` (fraction of keyspace used as mutation hot set)
- `--max-connections 50` (match NoDb cache pool default)
- `--socket-timeout 5`
- `--socket-connect-timeout 5`
- `--health-check-interval 30`
- `--max-failure-rate 0.02` (process exits non-zero if exceeded)
- `--skip-prime` (skip synthetic key pre-seeding)

## Reports

Each run writes:

- `tools/perf/redis_nodb_cache_stress/results/redis_nodb_cache_stress_<timestamp>.json`

Report includes:

- target profile (`local` / `wepp1` / `wepp2`)
- redacted Redis URL and pool config
- fixture inventory + payload sizes
- throughput, failure rate, latency (`p50`, `p95`, `p99`)
- per-operation metrics
- failure type counts
- first-failure and first-recovery timing offsets
- mutation workload context (hot-key set size, sequential burst length)

## Forest (dev) Statistics

Measured on host `forest` (dev stack), run timestamp `2026-04-25T16:24:05Z`:

- Command surface: `rq-worker` container via `/opt/venv/bin/python`
- Report: `tools/perf/redis_nodb_cache_stress/results/redis_nodb_cache_stress_20260425T162405Z.json`
- Threads: `8`
- Duration: `12s`
- Run ids: `80`
- Operation weights: `get=30,set=20,mutate=20,mutate_seq=20,delete=5,scan=5`
- Mutation hot-key set size: `36` keys (`15%` of generated keyspace)
- Sequential mutation burst length: `7`

Outcome:
- `ops_total=14415`
- `ops_failure=0` (`failure_rate=0.0`)
- `throughput_ops_per_sec=1200.202`
- Latency: `p50=2.668ms`, `p95=27.954ms`, `p99=42.194ms`
- Highest p95 operation: `mutate_seq` (`41.874ms`)

## Wepp1/Wepp2 No-Restart Statistics

Measured on `2026-04-25` using live `rq-worker` containers with no compose restart.

Execution mode:
- Harness directory copied into running containers at `/tmp/redis_nodb_cache_stress` via `wctl docker compose cp`.
- Harness executed with `/opt/venv/bin/python` inside each `rq-worker` container.
- Workload profile: `threads=8`, `duration=12s`, `runid_count=80`, `get=30,set=20,mutate=20,mutate_seq=20,delete=5,scan=5`, `mutate_hot_key_fraction=0.15`, `mutate_seq_burst_length=7`.

`wepp1` result (run timestamp `2026-04-25T16:30:29Z`):
- Report: `/tmp/redis_nodb_cache_stress/results/redis_nodb_cache_stress_20260425T163029Z.json`
- Redis target: `redis://<redacted>@redis:6379/13`
- `ops_total=19923`
- `ops_failure=0` (`failure_rate=0.0`)
- `throughput_ops_per_sec=1659.698`
- Latency: `p50=2.252ms`, `p95=17.499ms`, `p99=22.69ms`
- Highest p95 operation: `mutate_seq` (`22.618ms`)

`wepp2` result (run timestamp `2026-04-25T16:31:17Z`):
- Report: `/tmp/redis_nodb_cache_stress/results/redis_nodb_cache_stress_20260425T163117Z.json`
- Redis target: `redis://<redacted>@192.168.100.237:6379/13`
- `ops_total=21982`
- `ops_failure=0` (`failure_rate=0.0`)
- `throughput_ops_per_sec=1831.066`
- Latency: `p50=2.084ms`, `p95=15.95ms`, `p99=20.208ms`
- Highest p95 operation: `mutate_seq` (`20.208ms`)

Cross-host Redis confirmation for `wepp2` run:
- `wepp2` `RQ_REDIS_URL` host resolved to `192.168.100.237` (db `/9`), which is `wepp1`.
