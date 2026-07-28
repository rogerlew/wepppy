# DOM-06 Outlet Field and Action Matrix

| Rendered identity/action | Controller behavior | Downstream boundary | Evidence |
| --- | --- | --- | --- |
| `set_outlet_mode` cursor radio | Default selection is cursor mode | Browser mode state | Actual render + Outlet Jest |
| `set_outlet_mode` entry radio | Reveals manual longitude/latitude input | Browser mode state | Actual render + Outlet Jest |
| `input_set_outlet_entry` | Parses `lon, lat` into numeric coordinates | `POST /set-outlet` | Actual render + manual-entry Jest |
| Cursor toggle/map click | Sends numeric coordinates | `POST /set-outlet` | Existing Outlet Jest |
| `hint_set_outlet_cursor` and status/stacktrace panels | Expose job/status lifecycle | RQ job/status stream | Actual render + existing Outlet Jest |
| RQ request | Validates/enqueues then mutates Watershed | `set_outlet_rq` and reload query | Existing route/RQ tests |

Excluded: authorization, CSRF, queue wiring, and outlet algorithms are not
changed. Any production change to those surfaces requires a new risk review.
