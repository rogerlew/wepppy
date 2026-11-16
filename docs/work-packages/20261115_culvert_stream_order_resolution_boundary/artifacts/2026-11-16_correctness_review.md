# Correctness and User-Experience Review - Culvert Stream-Order Resolution Boundary

> Required independent review for the production-behavior repair. Complete this
> artifact after local validation and the forest RQ replay.

## Metadata

- **Package**:
  `docs/work-packages/20261115_culvert_stream_order_resolution_boundary/`
- **Reviewer**: TBD; must not be the sole implementer.
- **Date**: TBD.
- **Scope reviewed**: mapping helper, culvert batch orchestration, forest RQ
  replay, generated and consumed terrain artifacts.
- **Commit/branch context**: TBD exact revision and dirty-state declaration.
- **Canonical contract(s)**:
  `docs/culvert-at-risk-integration/weppcloud-integration.spec.md` and the new
  parameterization ADR.
- **Related QA/security artifacts**: security artifact N/A; QA and forest
  evidence paths TBD.

## User Outcome

- **User goal**: retain approximately regular WEPPcloud hillslope/channel scale
  when a culvert payload uses a nominal 1 m DEM.
- **Success presented to the user as**: a completed, browsable Point_ID 1040 run
  whose stream, channel, subcatchment, and outlet artifacts are valid and whose
  scale is within the accepted approximately 10 m comparison range.
- **Failures that may reach the user**: payload validation failure, missing
  stream coverage/fallback, terrain-preparation error, worker timeout, WEPP
  failure, or a completed run with scientifically unacceptable network scale.
- **Partial-state behavior**: retain the new forest batch, job diagnostics, and
  available artifact evidence; do not publish an acceptance claim for stages not
  directly verified.

## Failure-Class Coverage

The broken shared assumption is that a nominal 1 m raster is represented as a
floating value less than or exactly equal to `1.0`. Assess every consumer of
`_map_order_reduction_passes`, both resolution boundaries, non-default
accumulation thresholds, payload overrides, and per-run fallback. Record the
consumer/variant matrix and disposition here before closure.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Missing/nonpositive cell size | no for mapping | return `None`; caller retains configured behavior | TBD focused test |
| Nominal 1 m through approved boundary | yes | three passes | TBD focused tests and Santee log |
| Above nominal boundary through 4 m | yes | two passes | TBD 1.51/2.0/4.0 tests |
| Above 4 m | yes | one pass | TBD boundary test |
| Missing/nonpositive accumulation threshold | supported legacy | use 100 | TBD focused test |
| Explicit pass override | yes | override mapped result | TBD orchestration test |
| Pruned stream absent in one watershed | supported fallback | explicit full-stream fallback, not silent acceptance | TBD replay/readback |
| Malformed resolution/threshold metadata | no | bounded explicit/default behavior per current contract | TBD tests |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Candidate network remains outside scale gate | expected acceptance failure | package remains open; no promotion | Count parity is the reported outcome, not job success |
| Main drainage/outlet removed | exceptional candidate failure | explicit failed replay and rollback | More aggressive pruning cannot sacrifice valid topology |
| NRCS SDA unavailable or returns incomplete SSURGO tables | expected environmental blocker | no replay submission; retain probe failure and retry later | External soil-service failure cannot test stream-order mapping |
| External service fails after terrain build | exceptional partial failure | failed job with retained stage evidence | Partial artifacts do not imply completed modeling |
| Unrelated active forest job blocks restart | expected operational wait | defer restart | Restart authority is not cancellation authority |

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Direct evidence | Result |
| --- | --- | --- | --- |
| User/request intent | only Point_ID 1040; source 1 m DEM/streams; threshold 100; no override | filtered payload manifest and semantic comparison | pending |
| Reloaded persisted state | extracted batch preserves intended metadata and model parameters | normal reader/API and filesystem readback | pending |
| Generated intermediate | three-pass `netful.tif` and matching `chnjnt.tif` retain valid main network | raster parse, hashes, stream/junction statistics | pending |
| Prepared/executable input | Point_ID 1040 consumes candidate topology without silent fallback | resolved run paths/symlinks and identity comparison | pending |
| Execution output | exact candidate RQ tree produces fresh subcatchment/channel artifacts | revision, containers, jobs, parsed artifacts | pending |
| User-facing result | batch summary and browse/download expose the fresh run accurately | authenticated readback | pending |

- **Direct unmocked failing boundary**: pending forest Whitebox pruning and
  normal culvert execution.
- **Actual-project/environment evidence**: pending host `forest`, Santee
  Point_ID 1040, exact candidate revision.
- **Highest completion claim supported**: diagnosed.
- **Deployment/recovery still outstanding**: forest1 and production deployment,
  plus production batch repair, remain outside this package.

## Review Checks

- [ ] Canonical intent and accepted ADR are named; implementation/tests are not
      treated as authority by themselves.
- [ ] Missing, boundary, intermediate, override, fallback, and malformed states
      are tested or explicitly dispositioned.
- [ ] The observed raw Santee resolution is retained rather than rounded in
      evidence.
- [ ] At least one direct, unmocked forest replay exercises real raster pruning,
      queue execution, and artifact consumption.
- [ ] Generated and consumed raster semantics are parsed, not inferred from
      files, timestamps, logs, or job status.
- [ ] Payload filtering preserves Point_ID 1040 semantics and raster bytes.
- [ ] Candidate scale is compared with both the two-pass failure and
      approximately 10 m baseline.
- [ ] Spatial drainage/outlet validity is checked independently of counts.
- [ ] Forest restart preserved unrelated work, queues, and durable state.
- [ ] Pre- and post-restart uncached SSURGO builds for an actual Santee MUKEY
      passed from the batch-worker identity immediately before submission.
- [ ] SSURGO admission evidence includes parsed SDA-backed tables and a valid
      generated soil; WMesque health and cached artifacts were not substituted.
- [ ] Status language distinguishes implementation, local validation, forest
      validation, deployment, and production repair.
- [ ] No unresolved medium/high finding remains.

## Findings Register

| ID | Severity | Finding | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| TBD | TBD | Review pending | TBD | TBD | Open |

## Verdict

**Pending.** The package cannot close until an independent reviewer records a
verdict and all medium/high findings are resolved. Forest validation is not
forest1 or production deployment, and it does not repair the existing production
batch.
