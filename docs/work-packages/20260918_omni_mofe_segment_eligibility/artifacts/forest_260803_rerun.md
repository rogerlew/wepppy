# Forest rerun with WEPP 260803

2026-09-18: user explicitly authorized stopping the two remaining thinning jobs
and rerunning all six saved scenarios with `wepp_260803` on local Forest.
No production project or repository configuration default changes.

Cancellation through `/api/canceljob/{job_id}` returned HTTP 200 for both
thinning leaves and their deferred compilation/finalization jobs. Readback:

- `0fe3d138-37e8-47e2-a544-765675ea8b0a`: stopped.
- `acd2a3a1-6ccb-4b93-878b-9ec26eef7dcc`: stopped.
- `12d94ea9-1003-44f7-a315-82c6df428975`: canceled.
- `6ee03f8e-4dc3-4736-84dc-4fb0d86e2cfe`: canceled.

Compatibility/regression plan: change only the saved binary through the existing
NoDb setter, preserve the six scenario definitions and all scientific settings,
clear the scenario dependency cache, and verify each regenerated child inherits
the selected binary. Baseline outputs remain historical and are not refreshed
by this scenarios-only submission; they must not be described as 260803 outputs.

Before mutation, preserved `wepp.nodb` and `omni.nodb` as sibling files with
suffix `.before_260803_20260918`. Scoped cache invalidation preceded hydration.
At 19:59:56 UTC the setter changed the binary from `wepp_dcc52a6` to
`wepp_260803`; durable JSON readback matched. The dependency tree was already
empty and explicitly persisted empty at 20:00:00 UTC.

Prior child artifacts were copied successfully (6.3 GB, exit 0), without following symlinks, to
`/wc1/runs/ve/ventilated-gag/_pups/omni/scenarios_dcc52a6_before_260803_20260918`.
The replacement submission followed successful completion of this copy.
Both 260803 executable variants exist locally. API pipeline reports preconditions
met and rerun allowed; its failed status describes the previous attempt.

Dispatch at 2026-09-18 20:03:37 UTC returned HTTP 202, job
`ef226e0f-a5f7-4daf-bee6-9db5f420c7aa`. Initial status HTTP 200, queued.
Six saved definitions submitted unchanged. Correlation ID:
`omni-mofe-260803-rerun-20260918-forest`.

Worker binary SHA256: watershed
`4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5`;
hillslope `86ef065c8d8c6c1e644db40c022c7c850701c0c174d3c622dfa28f1d6da122e7`.
Await completion/error notification; submission does not establish acceptance.
