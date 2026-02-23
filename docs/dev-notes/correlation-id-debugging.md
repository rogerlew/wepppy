# Correlation ID Debugging Guide

Use this guide to trace one request across WEPPcloud ingress, rq-engine enqueue, RQ worker execution, and query-engine responses.

## Contract At A Glance

- Canonical internal key: `correlation_id`
- HTTP header contract: `X-Correlation-ID`
- If inbound header is missing or invalid, services generate a new ID.
- Core services always emit `X-Correlation-ID` on responses.
- Query-engine MCP compatibility contract keeps `meta.trace_id` and maps it to the same value as `meta.correlation_id`.

## Fast Workflow

1. Send a request with an explicit correlation ID.
2. Confirm the response echoes `X-Correlation-ID`.
3. Search logs and job metadata for that same value.

## Step-By-Step Debugging

### 1. Send a request with a known ID

Use a unique value so log searches are unambiguous.

```bash
CID="cid-debug-$(date +%s)"
curl -si \
  -H "X-Correlation-ID: ${CID}" \
  http://localhost:8080/rq-engine/health | sed -n '1,20p'
```

```bash
CID="cid-debug-$(date +%s)"
curl -si \
  -H "X-Correlation-ID: ${CID}" \
  http://localhost:8080/query-engine/health | sed -n '1,20p'
```

### 2. Verify response header behavior

- Expected: response includes `X-Correlation-ID`.
- Expected: valid inbound IDs are echoed.
- Expected: invalid inbound IDs are replaced with a generated ID.

### 3. Locate the ID in service logs

```bash
wctl logs -f weppcloud | rg "cid-debug-"
```

```bash
wctl logs -f rq-engine | rg "cid-debug-"
```

```bash
wctl logs -f rq-worker | rg "cid-debug-"
```

`correlation_id` and `trace_id` fields are injected into log records by `wepppy/observability/correlation.py`.

### 4. Confirm enqueue -> worker propagation

When a route enqueues a job, correlation metadata is stored on the job.

```bash
wctl exec weppcloud python - <<'PY'
from redis import Redis
from rq.job import Job
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

job_id = "<job_id>"
conn = Redis(**redis_connection_kwargs(RedisDB.RQ))
job = Job.fetch(job_id, connection=conn)
print("correlation_id:", job.meta.get("correlation_id"))
print("meta keys:", sorted(job.meta.keys()))
PY
```

Worker-side run-scoped logs are written to `rq.log` under the run working directory (canonical root: `/wc1/runs/`).

### 5. Confirm query-engine trace compatibility

For MCP JSON responses, expect:

- `meta.trace_id` present
- `meta.correlation_id` present
- `meta.trace_id == meta.correlation_id`

## Common Failure Patterns

### Missing `X-Correlation-ID` on response

- Check ingress middleware order for the service.
- For query-engine, verify CORS preflight still passes through correlation middleware.

### Logs show `correlation_id` as `-`

- Context was not bound for that execution path.
- Confirm request/job middleware hooks are installed in the running service.

### Worker logs missing request correlation

- Check enqueue metadata on the job (`job.meta["correlation_id"]`).
- Ensure enqueue happened through patched queue paths (`install_rq_auth_actor_hook()`).

### Inbound header not preserved

- Only IDs passing validation are accepted.
- Invalid values are replaced by generated IDs by design.

## Source Map

- Shared utility and log enrichment: `wepppy/observability/correlation.py`
- Flask ingress/egress hooks: `wepppy/weppcloud/app.py`
- rq-engine middleware: `wepppy/microservices/rq_engine/__init__.py`
- Query-engine middleware: `wepppy/query_engine/app/server.py`
- MCP middleware and `trace_id` mapping: `wepppy/query_engine/app/mcp/router.py`
- Enqueue metadata propagation: `wepppy/rq/auth_actor.py`
- Worker metadata restore: `wepppy/rq/rq_worker.py`

