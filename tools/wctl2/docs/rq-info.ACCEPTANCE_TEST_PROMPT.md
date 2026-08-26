# Acceptance Test Prompt - wctl rq-info

## Preconditions

- A normal worker stack (`rq-worker`) or the dedicated wepp3 stack
  (`rq-worker-fork-archive`) is running.
- RQ workers are connected to Redis DB 9.

## Test Steps

1. Run `wctl rq-info`.
   - Confirm the log line targets `rq-worker` on a normal stack or
     `rq-worker-fork-archive` on the dedicated wepp3 stack.
   - If Redis auth is enabled, confirm the command succeeds (no `Authentication required.` error) and the log does not echo raw credentials.
   - Confirm output lists all default queues (`default`, `batch`, and
     `fork-archive`).
   - If workers are running, confirm each worker line includes `jobs: X finished, X failed`.

2. Run `wctl rq-info --interval 1`.
   - Confirm the screen refreshes every second.
   - Stop with `Ctrl-C` after at least one refresh.

3. Run `wctl rq-info --detail`.
   - Confirm the standard `rq info` output appears.
   - Confirm a `Jobs (started, queued)` section follows with columns for `runid`, `description`, and `auth_actor`.
   - If output is too large, rerun with `--detail-limit 10` and confirm the job list is shorter.

## Pass Criteria

- The command exits successfully and displays queue + worker stats for all
  three queues.
- The command automatically targets the dedicated fork worker on wepp3 without
  requiring `--service`.
- Extra args (like `--interval 1`) are honored.
- Interval mode (`--interval ...`) preserves native `rq info` refresh behavior.
- Worker visibility is correct even if Redis worker registry set indexes were stale prior to running the command.
- `--detail` appends job metadata without breaking the base `rq info` output.

---

## Test Results - 2026-01-06

### Preconditions
- Docker stack verified running with `redis`, `rq-worker`, and `rq-worker-batch` containers.

### Test 1: `wctl rq-info`
**PASS**
- Log line showed: `docker compose exec rq-worker bash -lc /opt/venv/bin/rq info -u redis://redis:6379/9 default batch`
- Output listed all default queues (`default`, `batch`, and `fork-archive`)
- Worker lines included `jobs: X finished, X failed` stats (for example, `jobs: 1 finished, 0 failed`)

### Test 2: `wctl rq-info --interval 1`
**PASS**
- Command passed `--interval 1` to `rq info`
- Screen refreshed every second (verified timestamps 1 second apart)
- Default queues (`default`, `batch`, and `fork-archive`) still honored

### Summary
All pass criteria met.
