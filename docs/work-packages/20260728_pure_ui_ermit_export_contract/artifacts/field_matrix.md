# SURF-16 ERMiT Export Contract Matrix

| Boundary | Risk-bearing contract | Verified evidence |
| --- | --- | --- |
| Discoverability | non-RHEM results link; RHEM exclusion | render + route |
| Launcher | run/config display and run-scoped submit/token/return URLs | direct render |
| Initial state | queued chip, active note/spinner, hidden actions/error | direct render |
| Token | same-origin POST; non-empty bearer token; canonical errors | Jest + session tests |
| Submit | one bearer `POST`; `job_id`, `status_url`, `download_url` | Jest + rq-engine |
| Poll | canonical active/failure/finished states and bounded timer | Jest + job contract |
| Download | bearer fetch, filename, blob URL, automatic and manual action | Jest + rq-engine |
| Retry | fresh recoverable attempt after any workflow failure | Jest |
| Worker | run/config/workdir inputs and relative artifact metadata | worker + route |
| Security | CAP/auth/run access/scope/pup containment/job association | routes + review |

ERMiT export formulas, CSV schema, and queue topology are excluded.
