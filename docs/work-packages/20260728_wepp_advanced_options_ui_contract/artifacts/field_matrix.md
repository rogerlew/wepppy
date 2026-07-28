# DOM-14B WEPP Advanced Options Field and Action Matrix

| Rendered identity/action | Downstream behavior | Evidence |
| --- | --- | --- |
| Advanced numeric/boolean fields | Parsed as supported native WEPP payload fields | Partial renders + parser contract |
| PMET values/routine toggle | Preserves numeric values and posts the PMET routine state | Actual render + Jest + RQ-engine |
| Frost, Interchange, Soil option controls | Preserve existing option-specific render contracts | Actual render + parser contract |
