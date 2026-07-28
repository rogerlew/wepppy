# DOM-08B Landuse Catalog and Map Editor Field and Action Matrix

| Rendered identity/action | Browser behavior | Downstream boundary | Evidence |
| --- | --- | --- | --- |
| Catalog `data-*-url` attributes | Mint session token and select list/upload/delete/description endpoint | RQ-engine run authorization and catalog files | Actual render + inline Jest + route tests |
| `management_upload`, `replace` | Submit `.man`/`.zip` FormData with explicit replacement choice | Archive/file validation and atomic install | Actual render + RQ-engine upload tests |
| Dynamic description/save/delete actions | Submit filename and description JSON | Metadata persistence and catalog refresh | Inline Jest + route tests |
| Map snapshot/save/clear URLs | Load snapshot and post native row JSON | Custom mapping override and Landuse state | Actual render + inline Jest + route tests |
| Snapshot `lookup_sha256` | Send `X-If-Match-Sha256` before save | Optimistic concurrency | Actual render + inline Jest + conflict tests |
| Save/reload/clear controls | Save rows, refresh snapshot, or clear override | Atomic mapping file and persisted override path | Actual render + route tests |

Landuse build and reload are DOM-08A. Report-inline mapping modification is
DOM-09. No queue edge changes are in scope.
