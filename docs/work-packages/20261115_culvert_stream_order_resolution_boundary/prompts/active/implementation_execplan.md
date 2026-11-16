# Calibrate the nominal 1 m culvert stream-order boundary with a forest replay

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must remain current.
Maintain it according to `docs/prompt_templates/codex_exec_plans.md`. Update this
plan and `docs/work-packages/20261115_culvert_stream_order_resolution_boundary/tracker.md`
at every stopping point.

Current execution is [per-run selection](per_run_selection_execplan.md). The
three-pass candidate below failed the twofold cardinality criterion and was
superseded by ADR-0144 after the resolution/outlet study. Retain this plan as the
record of that experiment; do not apply its old mapping as the current contract.

## Purpose / Big Picture

Culvert batch users should receive approximately the same WEPP hillslope scale
from a nominal 1 m DEM as from the regular approximately 10 m workflow. Today,
Santee reports its resolution as `1.0000000000089009 m`; the strict `<= 1.0`
comparison assigns two stream-order pruning passes instead of the intended three,
and Point_ID 1040 expands to 14,339 subcatchments and 5,765 channels.

After this work, the mapping will have an explicit nominal 1 m class with a
candidate upper boundary of 1.5 m. A human can see it working in a fresh forest
RQ job: logs select three passes for the retained Santee input, the generated
stream raster is the one consumed by Point_ID 1040, and parsed channel and
subcatchment counts approach the retained approximately 10 m baseline. A green
unit test or completed job alone is not acceptance.

## Progress

- [x] (2026-11-16 00:46 UTC) Diagnose the strict-boundary failure and identify
  retained 1 m and approximately 10 m Santee evidence.
- [x] (2026-11-16 00:46 UTC) Scaffold the package, tracker, correctness artifact,
  and this ExecPlan; record forest restart authority.
- [x] Draft the parameterization ADR and implement the bounded candidate with
  focused regression tests.
- [x] Run local focused tests and documentation/governance checks.
- [x] Prepare a semantically verified, one-point Santee Point_ID 1040 payload.
- [x] Pass the uncached NRCS SDA/SSURGO availability gate from the actual forest
  batch-worker identity before and after candidate restart.
- [x] Inventory and safely restart/reload the necessary forest stack services.
- [x] Submit and monitor the replay through the rq-engine API as real RQ work.
- [x] Parse generated and consumed artifacts and compare the fresh result with
  retained baselines.
- [x] Complete correctness review, ratify or reject the boundary in the ADR, and
  close or hand off the package without exceeding supported claims.

## Surprises & Discoveries

- The uncached SDA probe succeeded on 2026-11-16 at 01:07 UTC; the reported outage is not currently reproduced. MUKEY 131939 occurs in 655,110 source raster pixels.
- Existing map logging rounded cell size to two decimal places, preventing the required raw-resolution evidence.

- Observation: the existing 2 m unit test is not calibration evidence.
  Evidence: the cutoff was added in commit `bfdc19e6b` on 2026-01-11; the test
  was added during helper extraction in commit `964de73fe` on 2026-02-19.
- Observation: the integration plan said to test two then three passes on 1 m
  batches, but the next mapping commit marked the phase complete without
  retaining measured boundary results.
  Evidence: `docs/culvert-at-risk-integration/weppcloud-integration.plan.md`
  Phase 5c.
- Observation: retained production payloads do not provide an intermediate
  1.5-2.5 m calibration site.
  Evidence: production culvert batch metadata inventory on 2026-11-15.

## Decision Log

- Decision: change only the existing map log cellsize formatter from `%.2f` to `%r`.
  Rationale: retain unrounded source resolution for the required acceptance gate; no queue or route changes.
  Date/Author: 2026-11-16 / Codex, correctness review.

- Decision: test an explicit 1.5 m upper boundary for the nominal 1 m class
  rather than use `floor()` or only an epsilon.
  Rationale: `floor()` reclassifies genuine 1.9 m and 4.9 m data, while epsilon
  repairs only metadata noise and preserves the unsupported 1.01 m cliff. The
  1.5 m candidate is bounded and must earn acceptance through actual-project
  evidence.
  Date/Author: 2026-11-16 / Operator and Codex.
- Decision: require a fresh RQ submission on forest, not a direct Python call.
  Rationale: the escaped failure crosses payload, raster, long-running process,
  queue, worker, and artifact-consumer boundaries.
  Date/Author: 2026-11-16 / Operator.
- Decision: authorize restart of forest only.
  Rationale: long-running rq-engine and batch-worker processes must load the
  candidate, while forest1 and production promotion remain separate decisions.
  Date/Author: 2026-11-16 / Operator.
- Decision: treat SSURGO availability as a hard precondition for the replay.
  Rationale: culvert preparation builds WEPP soils through the NRCS Soil Data
  Access Tabular API. A service outage would fail or distort the end-to-end job
  independently of stream-order mapping, so it cannot be admitted as candidate
  evidence.
  Date/Author: 2026-11-16 / Operator and Codex.

## Outcomes & Retrospective

The initial three-pass replay produced3,344 hillslopes and1,339 channels,
exceeding twice the retained726/298 baseline. The service-token admission issue
was resolved using a registered culvert service identity without a human account.
The superseded replay was canceled through the supported endpoint; artifacts
remain retained. The subsequent calibration and outlet study led the operator to
choose per-run descending candidates. ADR-0144 and the per-run ExecPlan now govern
implementation, following reviewed contract ancestor `61645e8a1` and source commit
`4266e740a`. See that plan for current forest acceptance and regression results.

## Context and Orientation

`wepppy/rq/culvert_rq_helpers.py` contains
`_map_order_reduction_passes(cellsize_m, flow_accum_threshold)`. It computes an
effective cell size as the raster cell size multiplied by the square root of the
flow-accumulation threshold divided by 100. The current bins are three passes for
an effective size at or below exactly 1 m, two at or below 4 m, and one above 4
m. A pruning pass removes the current first-order headwater streams; repeated
passes simplify the network before WEPP subcatchments are built.

`wepppy/rq/culvert_rq.py` reads payload metadata, obtains the mapped pass count,
builds batch-level `topo/netful.tif` and `topo/chnjnt.tif`, and enqueues one RQ
child per culvert on the `batch` queue. A run may fall back to the unpruned
`streams.tif` when the pruned raster has no stream coverage; this fallback must
be checked because it could make the mapping appear ineffective.

`wepppy/microservices/rq_engine/culvert_routes.py` owns the authenticated
`POST /rq-engine/api/culverts-wepp-batch/` upload. Use this supported boundary so
the replay exercises validation, extraction, persistence, parent orchestration,
child execution, finalization, and job polling.

The retained production source is batch
`f7c24f19-5cf4-4da0-8ef6-3975a8a6a890` on wepp1. Its DEM is 7,764 by 7,344 at
`1.0000000000089009 m`, its model parameter has `flow_accum_threshold=100`, and
Point_ID 1040 covers about 21.69 square kilometers. The failed-scale output has
14,339 subcatchments and 5,765 channels after two passes. Retained batch
`0b4ea911-9c78-42d3-92bc-4df6b7c3239c` uses a 9.325770936 m DEM and provides an
approximately 10 m comparison of about 726 subcatchments and 298 channels.

The execution host is exactly `forest`, the development Compose environment.
The operator authorizes restarting its stack for this package. That authority
does not extend to forest1 or production and does not permit queue flushing,
volume removal, `compose down`, or terminating unrelated active work.

## Plan of Work

First, draft a parameterization ADR under `docs/adrs/` following
`docs/standards/parameterization-adr-standard.md`. State that 1.5 m is a
candidate nominal-class boundary pending forest acceptance. Record the old and
new classifications, the absent intermediate-resolution production evidence,
the twofold scale criterion, decision participants, and rollback to the strict
mapping if the replay fails. The ADR must be finalized before merge, not merely
linked as TBD.

Second, make the smallest code change in
`wepppy/rq/culvert_rq_helpers.py`. Name the 1.5 m boundary so it is not an
unexplained literal. Preserve the effective-cell-size formula and the 4 m
boundary. Extend `tests/rq/test_culvert_rq_helpers.py` with the observed Santee
value and explicit cases at 1.3, 1.5, 1.51, 2.0, immediately around 4.0, and at
least one non-default accumulation threshold. Do not use `floor()` and do not
change queue or route code.

Third, update the canonical culvert integration specification and developer
guidance so they describe ranges, not only representative resolutions. Explain
that the mapped pass count is a heuristic and that payload-level
`order_reduction_passes` remains an explicit override. Run focused tests and
documentation checks before operating forest.

Fourth, create a disposable replay payload on forest from read-only copies of
the retained production batch inputs. Preserve the full DEM and stream rasters,
filter both GeoJSON feature collections to only Point_ID 1040, set the declared
culvert count consistently, and preserve model parameters except for any
production-specific base-run identifier that the existing forest payload
contract requires replacing. Do not include an `order_reduction_passes`
override. Build a relative-path SHA-256 manifest and semantically parse the ZIP
before submission. Prove DEM and streams are byte-identical to the source and
both feature collections contain exactly the same Point_ID 1040 feature as the
source.

Fifth, establish the forest operational baseline. Confirm `hostname` is
`forest`, the installed `wctl` preset resolves `docker/docker-compose.dev.yml`,
and Compose labels identify the expected project. Record the git revision,
working-tree state, relevant image/container IDs, rq-engine health, batch-worker
registration, active jobs, and queue counts. If unrelated batch work is active,
wait for it to finish; restart authority is not cancellation authority.

Before restarting anything, verify that the external NRCS Soil Data Access (SDA)
Tabular API is usable from the existing `rq-worker-batch` container. Do not use
only WMesque `/health`: WMesque supplies the gridded MUKEY raster, while
`SurgoSoilCollection` subsequently queries SDA for component, horizon,
restriction, fragment, and texture tables. Select one valid MUKEY present in the
retained Santee Point_ID 1040 soil raster, create a brand-new temporary SQLite
cache, instantiate `SurgoSoilCollection` for that MUKEY, build its WEPP soil with
one worker, and parse the generated soil semantics. The empty cache is required
to prove a network retrieval occurred. Retain the timestamp, MUKEY, table row
counts or collection synchronization count, endpoint identity, and parse result,
but not the full response.

If this probe fails, stop before restart and submission. Record the bounded error
and leave environment validation blocked; do not substitute cached data, a
different soil source, STATSGO fallback, or a mocked response. Local source/tests
and payload preparation may continue while SDA is unavailable.

Load the candidate into long-running processes with the smallest sufficient
restart:

    wctl docker compose restart rq-engine rq-worker-batch

If readback proves other forest services retain incompatible code or the
targeted restart cannot establish a coherent candidate, the operator has
authorized a broader `wctl docker compose restart` after the same active-job
gate. Never use `down`, flush Redis, delete volumes, or prune images/data. After
restart, prove the services are healthy, the worker is freshly registered on the
`batch` queue, and an in-container helper call classifies the observed Santee
resolution as three passes. Then repeat the same disposable, uncached Santee
MUKEY SSURGO build from the restarted `rq-worker-batch` container. Require both
the pre-restart and post-restart probes to pass; the second must finish
immediately before submission so a stale availability observation cannot admit
the long replay.

Sixth, submit the verified payload through the existing script and credential
file workflow. Do not print or store the token in package artifacts. From
`/home/workdir/wepppy`, the command shape is:

    python docs/culvert-at-risk-integration/dev-package/scripts/submit_payload.py \
      --payload <disposable-santee-1040-payload.zip> \
      --host forest.tail305ec9.ts.net \
      --token-file <gitignored-forest-token-file> \
      --poll-seconds 30 \
      --timeout-seconds 57600

The submit response must provide a new batch UUID and parent job ID. Inspect the
actual job tree with the rq-engine job endpoints or `wepppy/rq/job_info.py` and
record every child/finalizer ID, queue, status, timestamps, and failure detail.
The replay must be RQ-submitted; a foreground helper invocation is diagnostic
only and cannot satisfy acceptance.

Finally, read back artifacts. Retain the raw mapped-pass log including the
unrounded resolution. Parse the batch `netful.tif` and `chnjnt.tif`, identify the
exact per-run topology paths consumed by Point_ID 1040, determine whether the
per-run fallback activated, and parse the fresh subcatchment/channel products.
Compare counts and spatial validity with both the 1 m/two-pass failure and the
approximately 10 m baseline. Complete the correctness review. If the candidate
is outside twofold of either approximately 10 m count, loses the drainage/outlet
semantics, or silently falls back to the unpruned raster, reject the acceptance
claim and leave the package open with evidence.

## Concrete Steps

Work from `/home/workdir/wepppy` on host `forest` unless a read-only source
command explicitly names wepp1.

Inspect focused source and history:

    git diff -- wepppy/rq/culvert_rq_helpers.py \
      tests/rq/test_culvert_rq_helpers.py \
      docs/culvert-at-risk-integration \
      docs/adrs \
      docs/work-packages/20261115_culvert_stream_order_resolution_boundary

Run focused validation before forest restart:

    wctl run-pytest tests/rq/test_culvert_rq_helpers.py
    wctl run-pytest tests/culverts/test_culvert_batch_rq.py
    wctl run-stubtest wepppy.rq.culvert_rq_helpers
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

Validate documentation:

    wctl doc-lint --path docs/work-packages/20261115_culvert_stream_order_resolution_boundary
    wctl doc-lint --path docs/culvert-at-risk-integration/weppcloud-integration.spec.md
    wctl doc-lint --path docs/culvert-at-risk-integration/dev-package/README.md
    wctl doc-lint --path <new-adr-path>

Before restart, capture non-secret forest state:

    hostname
    git rev-parse HEAD
    wctl docker compose config --services
    wctl docker compose ps

Use existing RQ inspection commands to record active jobs, worker registrations,
and queue counts. Do not proceed across an active unrelated batch job.

Derive a known-valid Santee MUKEY from the retained Point_ID 1040 soil raster,
then run the repository's real SSURGO collection path from the batch-worker
container with a disposable empty cache. The command shape is:

    wctl exec -T rq-worker-batch python <package-local-probe-script> \
      --mukey <actual-santee-mukey>

The probe script must instantiate
`wepppy.soils.ssurgo.SurgoSoilCollection` with a temporary `cache_db_path`, call
`makeWeppSoils(max_workers=1)`, and verify a parseable, valid result for the
requested MUKEY. It must exit nonzero on `SsurgoRequestError`, an empty table
response, missing requested MUKEY, or invalid WEPP soil. Store only concise
non-secret output. Do not add a fallback or retry loop outside the library's
existing bounded request policy.

After the authorized restart, repeat service, worker, queue, and health readback.
Repeat the uncached SSURGO probe and only then submit the payload with the command
shape in the Plan of Work. Store concise non-secret transcripts and semantic
manifests under this package's `artifacts/` directory. Never copy credentials,
bearer tokens, complete environment dumps, or large rasters into git.

## Validation and Acceptance

The focused test must fail against the pre-change helper for the observed Santee
resolution and pass after the candidate. Existing exact 2 m behavior must remain
two passes, and values above 4 m must remain one pass. The formula that scales
cell size by the accumulation threshold must remain covered.

Forest acceptance requires the exact candidate revision and freshly restarted
batch worker. The parent and child jobs must be real RQ jobs. A raw log must show
the observed source resolution, threshold 100, and three mapped passes. The
generated batch stream/junction rasters and the exact artifacts consumed by
Point_ID 1040 must be semantically read back. File existence, size, timestamp,
job completion, and summary status are insufficient.

Submission admission additionally requires successful pre- and post-restart
uncached SSURGO probes from `rq-worker-batch`. WMesque health, DNS/TLS connection,
an HTTP 200 response without parsed tables, a populated cache, or an existing
soil file is insufficient. If SDA becomes unavailable after submission, record
the external failure and rerun later under a new batch UUID; do not interpret it
as a result of the stream-order candidate.

The scale gate compares the fresh result with approximately 726 subcatchments
and 298 channels from the retained 9.32577 m baseline. Both fresh counts must be
between half and twice their respective baseline values unless the operator
ratifies a revised criterion in the ADR before acceptance. Spatial checks must
also show a connected main drainage path and valid outlet; matching counts cannot
compensate for a broken network.

If the job fails for an unrelated external service after it has produced the
terrain artifacts, those artifacts may support only the stages they directly
prove. They cannot support a successful end-to-end or incident-resolved claim.

## Idempotence and Recovery

All replay data must live under a new, disposable forest batch UUID and must not
overwrite the production UUID or retained baselines. Rebuilding the filtered ZIP
is safe when its manifest is regenerated and compared. Repeated API submission
creates a new UUID; never confuse artifacts across attempts.

Forest service restart is repeatable after the active-job gate. Redis, PostgreSQL,
queues, and volumes remain intact. If the candidate process fails readiness,
restore the prior source revision or patch, restart the same affected services,
and verify their health and worker registrations. Do not use destructive Compose
commands for rollback.

If the Santee replay proves the candidate too aggressive or insufficient, keep
the failed batch and evidence until the correctness review records it. Revert the
candidate mapping locally; do not adjust another boundary or pass count without
updating the ADR and receiving the required decision approval.

## Artifacts and Notes

Retain small, non-secret evidence under
`docs/work-packages/20261115_culvert_stream_order_resolution_boundary/artifacts/`:

- source and filtered payload manifests with relative paths, sizes, and hashes;
- semantic JSON summaries of metadata, Point_ID features, and raster properties;
- forest before/after service and worker identities;
- RQ job tree and concise status/log excerpts;
- generated/consumed artifact identity and semantic comparison;
- baseline/candidate count and duration comparison; and
- completed correctness review.

Do not commit payload ZIPs, DEMs, stream rasters, credentials, browse tokens, or
full environment output.

## Interfaces and Dependencies

Keep the helper signature unchanged:

    def _map_order_reduction_passes(
        *,
        cellsize_m: Optional[float],
        flow_accum_threshold: Optional[int],
    ) -> Optional[int]:

The function must continue returning `None` for missing/nonpositive cell size,
three/two/one for mapped classes, and using threshold 100 when the threshold is
missing or nonpositive. Introduce no new dependency.

The existing rq-engine route, RQ queue, worker service, payload schema, and
response contract remain unchanged. Because queue wiring does not change,
`wepppy/rq/job-dependencies-catalog.md` should not need regeneration. If
implementation unexpectedly requires route, enqueue, dependency, or payload
contract changes, stop: that exceeds this package's bounded authority.

## Revision Note

2026-11-16: Initial ExecPlan created from the operator's request to change the
nominal 1 m boundary, replay Santee Point_ID 1040 as an RQ job on forest, and
authorize restart of the forest stack.

2026-11-16: Added a hard NRCS SDA availability gate after the operator reported
SSURGO down. The replay now requires real uncached Santee-MUKEY soil builds from
the forest batch-worker identity before and after restart.

## Forest execution — 2026-11-16 01:15 UTC

Restarted only rq-engine and rq-worker-batch after confirming no active or queued batch work. Retained container, mount, identity, candidate patch/hash, worker registration, and health evidence in artifacts. Fresh workers map Santee to three passes. Uncached SDA probes passed before restart (01:13:04 UTC), after restart (01:13:36 UTC), and immediately before retry (01:14:24 UTC).

Submission is blocked by HTTP 403 `human_identity_required`: feature-access governance rejects the scoped service credential. The large multipart uploads surfaced early rejection as TLS EOF; a small authenticated request exposed the actual error. No replay batch/job was created. Do not bypass governance or assume a human identity. Resume with an authorized human credential/identity for culvert access. No policy, route, or queue changes were made. Candidate remains provisional; artifact/scale gates and final ADR acceptance remain open. Full suite remains running in `/tmp/culvert-full.log`.

## Service identity correction — 2026-11-16

The human-account blocker was an incorrect diagnosis. The first credential used an unregistered subject (`culvert-resolution-forest`). The existing independent integration registration accepts `culvert-batch-submit-90d`, audience `rq-engine`, service class and `service_groups=culverts`. Minted a 24-hour submit-only forest credential for that existing identity; no policy or human membership changed. An authenticated empty upload now reaches payload validation (400 missing_file), proving service admission passed. Repeating SDA probe and submitting the retained ZIP with this credential.

Replay accepted at 2026-11-16 01:17:10 UTC: batch `402e8594-d597-4c25-a724-008bb72a83e7`, parent RQ job `3cd947ee-01fd-4b07-b07e-284e020e9e1c`. Submission returned HTTP 200 after the fresh 01:16:59 UTC SDA probe. Poller remains active (tool session 22841; `/tmp/culvert-submission-registered.log`). Runtime artifact and scale acceptance remain pending.

## Replay progress — 2026-11-16 01:28 UTC

Parent finished; Point_ID 1040 child `3a1a2911-2a9a-4784-b18b-2c8b7e4772db` is started and finalizer `8a566e01-e88c-4054-8660-41c5dab61c41` deferred. Batch log explicitly selected and executed three pruning passes for 1.0000000000089009 m at threshold 100. Consumer `dem/wbt/netful.vrt` references batch `topo/netful.tif`, not unpruned streams. Newly generated watershed Parquet metadata reports 3,344 hillslopes and 1,339 channels. These preliminary counts exceed the twofold baseline gate (726/298); full semantic validation and job completion remain pending.

## Twofold-limit diagnosis — 2026-11-16

Raster readback proves each saved pass exactly matches original Strahler orders
above 1, 2, and 3 respectively. Final netful matches pass three (251,268 stream
pixels); there is no missing pass. Consumer VRT references this pruned raster.
Point_ID 1040 polygon areas are 21.7008 km² baseline and 21.6927 km² candidate,
so a larger study area does not explain the count gap.

Both payloads specify accumulation threshold 100. Culvert producer source uses
D8 accumulation in cells and passes that threshold to extract_streams. This
corresponds to approximately 100 m² at 1 m versus 8,697 m² at 9.32577 m.
The 87-fold physical extraction-area difference is the primary mechanism for a
denser input network. The extra two Strahler pruning passes are a heuristic,
not a physical contributing-area equivalence. Minimal length pruning also
changes from about 18.7 m to 2 m. Terrain/source-vintage differences remain a
confounder; this comparison does not isolate their contribution.

Generated channels total 239.58 km versus 85.17 km baseline (2.81 times), with
1,339 versus 298 segments (4.49 times); average segment lengths are about 179 m
versus 286 m. Thus the candidate has both more stream length and more branching/
shorter segments, not just more raster pixels on the same channel network.
Hillslope counts are 3,344 versus 726 (4.61 times). The boundary change repaired
nominal classification but three passes do not satisfy this project's scale
criterion. No further threshold/pass-count change is authorized by this
investigation; another pass remains an experiment, not a calibrated conclusion.
Evidence: artifacts/pruning-diagnosis.json and network-scale-comparison.jsonl.

## Four-pass diagnostic — 2026-11-16

Operator requested evaluation of four passes. Generated disposable order-three and binary order-four rasters from the retained order-two intermediate, then regenerated junctions, Strahler order, and TOPAZ subcatchments using the existing Point_ID 1040 bound and outlet. No active run or default was modified. Result: 783 hillslopes and 313 channels, versus baseline 726/298; within twofold. Existing outlet remains a stream pixel; all 313 channels are reachable upstream from the single outlet in netw.tsv. This is terrain-only diagnostic evidence, not full RQ/WEPP acceptance. Outputs: `/wc1/culvert-resolution-replay/four-pass`; evidence: `artifacts/four-pass-diagnostic.json`.

Revision2026-11-16: superseded the unsuccessful three-pass candidate with the reviewed per-run contract and corrected the resolved service-token status.
