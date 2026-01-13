# RQ Job Dashboard
> Pure UI dashboard for inspecting RQ job trees and canceling jobs.
> **See also:** [`AGENTS.md`](../../../../../AGENTS.md) for UI and documentation conventions, [`docs/ui-docs/ui-style-guide.md`](../../../../../docs/ui-docs/ui-style-guide.md) for Pure layout patterns.

## Overview
The job dashboard renders a live view of RQ job trees with status chips, progress summaries, and stack traces. It polls rq-engine for job info.

## Routes
| Route | Method | Purpose |
| --- | --- | --- |
| `/weppcloud/rq/job-dashboard/<job_id>` | GET | Render the dashboard UI (`dashboard_pure.htm`). |
| `/rq-engine/api/jobinfo/<job_id>` | GET | Primary polling endpoint for job status. |
| `/rq-engine/api/canceljob/<job_id>` | POST | Cancel a job (JWT scope `rq:status`, session token required for run-scoped jobs). |

## Templates
| File | Notes |
| --- | --- |
| `templates/dashboard_pure.htm` | Extends `base_pure.htm`, uses Console Deck Layout + Summary Pane, and renders job groups with `<details class="wc-collapse">`. |

## Behavior Notes
- Polling re-renders the tree and preserves open state by tracking `<details open>` nodes.
- Group status derives from terminal job statuses (finished, failed, canceled, stopped); mixed states stay `running`.
- Cancel status strings are normalized to `canceled` in status mapping.

## Security
- The dashboard route is gated by `requires_cap` for anonymous users.
- Job info endpoints are public; cancel is JWT-protected. See `docs/dev-notes/endpoint_security_notes.md`.
