# DOM-25B Omni Contrasts UI Contract

**Status**: Closed 2026-07-28 UTC  
**Package ID**: DOM-25B

Actual rendering covers contrast modes/scenarios/pairs, GeoJSON path, run,
dry-run, delete confirmation, and limits. Existing controller, route, NoDb,
rq-engine, worker, artifact, reload, authorization, and map-overlay tests cover
the complete lifecycle. No repair was required.

## SURF-04B Fork Reset Amendment

The bounded enhancement at `../20260806_fork_skip_omni_reset/` may establish a
fresh destination Omni controller and empty contrast collection, including no
preserved `_uploads`, only when its new fork option is selected. It does not
change contrast payloads, execution, uploads, deletion, reports, overlays,
authorization, or this package's verified state.
