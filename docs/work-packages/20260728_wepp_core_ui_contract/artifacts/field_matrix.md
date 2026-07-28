# DOM-14A WEPP Core Field and Action Matrix

| Rendered identity/action | Downstream behavior | Evidence |
| --- | --- | --- |
| `wepp_bin` | Serialized to the run route and validated before queueing | Actual render + Jest + RQ-engine |
| Run action | Queues WEPP and hydrates result/lifecycle state | Actual render + Jest + RQ-engine |
| Watershed toggle/prep/run actions | Persists routine state and queues only when prerequisites hold | Actual render + Flask + RQ-engine |
| Hint/status/stacktrace targets | Surface lifecycle and failure state to the browser | Actual render + Jest |
