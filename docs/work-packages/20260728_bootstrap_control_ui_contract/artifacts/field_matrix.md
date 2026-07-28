# DOM-15 Bootstrap Control Field Matrix

| Rendered identity/action | Downstream behavior | Evidence |
| --- | --- | --- |
| Enable/mint/checkout/disable actions | Authorized bootstrap lifecycle mutations | Actual render + Jest + route/RQ-engine |
| Clone/commit fields | Hydrate repository and checkout state | Actual render + Jest |
| No-prep run actions | Queue bootstrap execution only when enabled | Actual render + RQ-engine |
