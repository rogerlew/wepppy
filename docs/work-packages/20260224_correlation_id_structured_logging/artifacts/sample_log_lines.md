# Sample Log Lines

Synthetic but representative examples showing continuity of one correlation ID across ingress, enqueue, worker execution, and query-engine response payload compatibility.

## Shared ID

- `correlation_id`: `cid-flow-20260223-001`
- Header: `X-Correlation-ID: cid-flow-20260223-001`

## weppcloud ingress

```json
{"ts":"2026-02-23T19:11:05.104Z","service":"weppcloud","event":"http.request","method":"POST","path":"/rq-engine/api/runs/demo/config/wepp","correlation_id":"cid-flow-20260223-001"}
```

## rq_engine enqueue boundary

```json
{"ts":"2026-02-23T19:11:05.312Z","service":"rq-engine","event":"rq.enqueue","queue":"default","job_id":"rq:job:7b5f","runid":"demo","correlation_id":"cid-flow-20260223-001","meta_keys":["auth_actor","correlation_id"]}
```

## rq_worker execution

```json
{"ts":"2026-02-23T19:11:05.500Z","service":"rq-worker","event":"job.start","job_id":"rq:job:7b5f","runid":"demo","correlation_id":"cid-flow-20260223-001"}
{"ts":"2026-02-23T19:11:07.821Z","service":"rq-worker","event":"job.success","job_id":"rq:job:7b5f","runid":"demo","correlation_id":"cid-flow-20260223-001"}
```

## query_engine MCP response compatibility

```json
{"ts":"2026-02-23T19:11:08.103Z","service":"query-engine","event":"mcp.response","status":200,"headers":{"X-Correlation-ID":"cid-flow-20260223-001"},"meta":{"trace_id":"cid-flow-20260223-001","correlation_id":"cid-flow-20260223-001"}}
```
