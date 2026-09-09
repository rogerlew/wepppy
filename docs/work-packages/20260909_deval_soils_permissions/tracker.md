# DEVAL soils permissions tracker

## Progress

- [x] Identify failure, deployed identities, file mode, and introducing commits.
- [x] Grant group read to the affected file and requeue the failed job.
- [x] Recover report: original job finished at 2026-09-09 21:35:31 UTC;
  generated HTML is 17,595,542 bytes.
- [x] Implement explicit readable parquet publication; 25 focused tests pass.
- [x] Live candidate regenerated soils as UID 1002/GID 130; DataFrame equality
  passed and output mode is 0644. Fresh render job
  `5f1e6673-9fe6-41d6-92b2-aaa6518a6bd5` finished at
  2026-09-09 21:39:24 UTC using the deployed renderer identity.
- [x] `wctl run-pytest tests --maxfail=1`: 8,113 passed, 72 skipped;
  completed in 829.91 seconds. Documentation and exception checks pass.
- [ ] Deploy permanent writer correction through the production workflow.

## Decision log

- Restore the existing working report contract with a small writer correction.
  Keep atomic publication; do not depend on repeated manual permission repairs.
- Validate the candidate in an isolated production worker process before
  rollout. Existing worker processes import NoDb at startup, and their source
  comes from the image: editing the host checkout alone is not deployment.

## Review and outcomes

The report and regenerated-input render both pass. Permanent rollout remains
separate from the isolated candidate canary. Operator owns deployment timing:
the production started registry still contains unrelated jobs, so no worker
restart or stack deployment has been executed.

The public route check reached the CAP gate (HTTP 200), not the HTML report;
this is not claimed as authenticated browser acceptance. RQ artifact validation
and the renderer log establish successful report generation.

Operational tooling friction: `wctl rq-info --detailed` on wepp1 invokes an RQ
CLI that rejects `--detailed`; inspect started registries directly for the
deployment gate until the wrapper is corrected.
