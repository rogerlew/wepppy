# DOM-14C SWAT/Cover Transform Field Matrix

| Rendered identity/action | Downstream behavior | Evidence |
| --- | --- | --- |
| `reveg_scenario` | Persists selected cover-transform scenario | Actual render + RQ-engine |
| Cover-transform upload action | Authenticated upload stages selected user transform | Actual render + Jest |
| SWAT run action | Queues SWAT after WEPP hillslope outputs exist | Jest + RQ-engine |
