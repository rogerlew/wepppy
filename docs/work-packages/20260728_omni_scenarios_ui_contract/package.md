# DOM-25A Omni Scenarios UI Contract

**Status**: Closed 2026-07-28 UTC  
**Package ID**: DOM-25A

Actual rendering covers the dynamic scenario host, add/delete/run actions, job
hint, and confirmed-delete modal. Existing controller, route, NoDb, rq-engine,
worker, artifact, reload, upload-validation, and authorization tests cover
scenario modes and lifecycle. No production repair was required.

## SURF-04B Fork Reset Amendment

The bounded enhancement at `../20260806_fork_skip_omni_reset/` may establish a
fresh destination Omni controller and empty scenario collection only when its
new fork option is selected. It does not change scenario payloads, execution,
uploads, reports, authorization, or this package's verified state.
