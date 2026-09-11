# Native SBS upload and result rendering

Make SBS native failures visible and restore a usable upload/summary workflow.
Security impact: high, because an untrusted HTML error becomes formatted Details
content. Dedicated independent correctness/security reviews are required.
Scope: SBS native helper/fallback removal, equivalent source/configured NoData export,
Disturbed/BAER upload and summary error presentation, focused tests and real
Wallow browser upload. No full suite, scientific retuning, new dependencies,
queue changes, proxy-timeout increases or fleet operations.

Canonical contracts: docs/schemas/sbs-raster-contract.md,
docs/ui-docs/contracts/sbs-control-contract.md and ADR-0065.
Execution: prompts/completed/sbs_native_upload_execplan.md.
Status: completed and independently reviewed. Validation and final reviews
are retained in artifacts/. Runtime changes remain uncommitted; no push.
