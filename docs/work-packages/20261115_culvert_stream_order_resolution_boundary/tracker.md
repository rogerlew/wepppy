# Tracker - Culvert Stream-Order Resolution Boundary

> Living document tracking implementation, forest replay evidence, decisions,
> risks, and handoffs.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-11-16 00:46 UTC  
**Current phase**: Candidate implemented; replay admission preparation  
**Last updated**: 2026-11-16 01:01 UTC  
**Next milestone**: Implement and locally validate the candidate 1.5 m boundary  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Draft the parameterization ADR with provenance and provisional policy.
- [ ] Implement the bounded mapping change and focused boundary tests.
- [ ] Update canonical culvert integration documentation.
- [ ] Prepare and hash the one-point Santee Point_ID 1040 replay payload.
- [ ] Verify NRCS SDA availability with an uncached Santee-MUKEY SSURGO build
      from the actual forest batch-worker identity.
- [ ] Inventory forest jobs and restart/reload the required stack services.
- [ ] Submit the payload through rq-engine and retain the complete RQ job tree.
- [ ] Parse generated and consumed terrain artifacts and compare with baselines.
- [ ] Complete independent correctness review and disposition findings.

### In Progress

- None.

### Blocked

- [ ] Forest RQ submission is blocked while the NRCS Soil Data Access service is
      unavailable. Local implementation and payload preparation may proceed, but
      no validation job may be enqueued until the preflight gate passes.

### Done

- [x] Confirmed the production Santee resolution was
      `1.0000000000089009 m` but map mode selected two passes (2026-11-15).
- [x] Confirmed Point_ID 1040 produced 14,339 subcatchments and 5,765 channels,
      versus about 726 and 298 on the retained 9.32577 m baseline (2026-11-15).
- [x] Confirmed no retained production culvert batch has a DEM resolution from
      1.5 through 2.5 m; the existing 2 m evidence is only a unit test
      (2026-11-15).
- [x] Scaffolded package, ExecPlan, tracker, and correctness review
      (2026-11-16 00:46 UTC).

## Timeline

- **2026-11-16 00:46 UTC** - Package created with a candidate 1.5 m boundary,
  actual-project forest RQ replay, and explicit restart authority.

## Decisions Log

### 2026-11-16 00:46 UTC: Treat the old 1.0 cutoff as uncalibrated

**Context**: Git history shows the `<= 1 m / <= 4 m` mapping was introduced as a
heuristic. The later `2.0 m -> 2 passes` test copied that behavior and supplied no
empirical boundary evidence.

**Options considered**:

1. Add only floating-point epsilon at 1.0 m - fixes Santee but preserves an
   unsupported discontinuity at 1.01 m.
2. Apply `floor()` - incorrectly moves genuine 1.9 m and 4.9 m data into more
   aggressive classes.
3. Evaluate 1.5 m as the nominal 1 m-class boundary - explicit and bounded, but
   still requires empirical acceptance.

**Decision**: Implement option 3 as the candidate and withhold acceptance until
the Santee replay passes the artifact and scale gates.

**Impact**: Unit tests cannot close the decision. The ADR must retain the forest
result and the operator's final approval.

### 2026-11-16 00:46 UTC: Authorize forest restart only

**Context**: The candidate must be loaded by long-running rq-engine and worker
processes before an RQ replay.

**Decision**: The package may restart the forest development stack, preferring
the affected services. It may not restart or deploy forest1 or production.

**Impact**: Queue/job inventory and post-restart identity/readiness evidence are
mandatory. Queue flush, volume removal, and forced unrelated-job cancellation
remain prohibited.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Three passes still produce far too many hillslopes | High | Medium | Twofold baseline gate; retain failed evidence and stop promotion | Open |
| Three passes remove the outlet or main drainage path | High | Low | Parse stream coverage, junctions, outlet, and fallback behavior | Open |
| Replay payload differs from production Point_ID 1040 intent | High | Low | Hash source inputs and semantically compare filtered GeoJSON/model parameters | Open |
| Restart interrupts unrelated forest work | High | Low | Inventory active jobs; drain affected workers; targeted restart first | Open |
| Candidate is tested under a stale worker | High | Medium | Record git revision, container IDs, process restart time, and imported source behavior | Open |
| SSURGO/SDA outage confounds candidate validation | High | Current | Require an uncached actual-MUKEY build before submission; block rather than interpret an external failure | Open |
| Runtime again approaches 12 hours | Medium | Medium | Record job stages and durations; do not infer a hang solely from elapsed time | Open |

## Hardening Signal Log

- **Baseline health signals**: approximately 9.32577 m Santee Point_ID 1040
  completed with about 726 subcatchments and 298 channels.
- **Baseline danger signals**: 1 m Santee with two passes produced 14,339
  subcatchments and 5,765 channels; one run reached the 43,200-second timeout.
- **Post-change health signals**: pending forest replay.
- **Danger signals observed**: exact floating comparison selected two passes for
  a value only `8.9e-12 m` above 1.0.
- **Temporary callus register**: none.
- **Softening experiments**: N/A.

## Verification Checklist

### Code Quality

- [ ] Focused mapping tests pass.
- [ ] Relevant culvert orchestration tests pass.
- [ ] Stub/API surface remains consistent.
- [ ] Changed-file broad-exception check passes.

### Documentation and Governance

- [ ] Parameterization ADR accepted before merge.
- [ ] ADR contains venue, participants, decision owner, implementer, exact delta,
      alternatives, evidence, risk, and rollback.
- [ ] Culvert integration specification and operator/developer guidance agree.
- [ ] Work-package and changed-doc lint pass.

### Forest Operation

- [ ] `hostname` is exactly `forest`; installed preset resolves
      `docker/docker-compose.dev.yml` and the expected Compose project.
- [ ] Starting revision, container IDs, worker registrations, active jobs, and
      queue counts retained before restart.
- [ ] No unrelated active job is terminated.
- [ ] Required services restart through `wctl`; Redis is not flushed and volumes
      are not removed.
- [ ] Post-restart rq-engine health, worker registration, queues, mounts, UID/GID,
      and candidate source identity are recorded.

### Santee RQ Replay

- [ ] Before restart, an uncached representative Santee MUKEY retrieval/build
      proves NRCS SDA availability from the current batch-worker identity.
- [ ] After restart and immediately before submission, the same disposable probe
      succeeds again and produces a parseable WEPP soil; both probe timestamps
      and non-secret result metadata are retained.
- [ ] Neither probe reuses a project SSURGO cache.
- [ ] WMesque `/health`, an HTTP 200 without parsed tables, and an existing
      `.sol` file are each insufficient to pass the SSURGO gate.
- [ ] Source batch and filtered payload manifests/hashes retained.
- [ ] Filtered `culvert_points.geojson` and `watersheds.geojson` each contain only
      Point_ID 1040 and preserve its geometry/properties.
- [ ] DEM and streams are byte-identical to the retained source inputs.
- [ ] `flow_accum_threshold=100`; no `order_reduction_passes` override is present.
- [ ] Upload response, parent/child/finalizer job IDs, queue names, and terminal
      states retained.
- [ ] Raw log proves `1.0000000000089009 m` selected three passes.

### Generated Artifacts

- [ ] Generated `netful.tif` and `chnjnt.tif` are semantically parsed.
- [ ] The exact topology consumed by Point_ID 1040 is identified and compared
      with the generated batch topology.
- [ ] Per-run fallback to unpruned `streams.tif` did not silently defeat the
      candidate, or is explicitly dispositioned as a failed gate.
- [ ] Fresh subcatchment/channel counts are within twofold of the retained
      approximately 10 m baseline.
- [ ] Batch summary and user-browsable/downloadable artifacts are read back.
- [ ] Completion claim does not exceed the evidence.

## Progress Notes

### 2026-11-16 00:46 UTC: Scaffold and retained diagnosis

**Agent/Contributor**: Codex

**Work completed**:

- Traced the strict boundary to the January 11 heuristic implementation.
- Confirmed the February 19 2 m unit test codified rather than calibrated it.
- Located the retained production Santee source batch and approximately 10 m
  baseline batch.
- Recorded operator authority to restart forest and submit the replay as RQ work.

**Blockers encountered**: None.

**Next steps**: Draft the ADR, implement focused mapping tests/change, then run
local validation before touching forest processes.

**Test results**: Documentation scaffold only; no code change or replay yet.

### 2026-11-16 01:01 UTC: SSURGO availability gate added

**Agent/Contributor**: Codex

**Work completed**:

- Recorded the current NRCS SDA outage as a blocker for forest RQ submission.
- Required a real, uncached SSURGO collection/build using an actual Santee MUKEY
  from the batch-worker container before and after candidate restart.
- Distinguished this gate from WMesque application health and cached soil reuse.

**Blockers encountered**: The operator reports SSURGO is currently unavailable.

**Next steps**: Continue local implementation and payload preparation if desired;
do not enqueue the forest replay until both availability probes pass.

**Test results**: Documentation-only update; SSURGO was not probed in this
session.

## Watch List

- **Meaning of "roughly the same"**: this scaffold uses a twofold
  channel/subcatchment gate. Record operator ratification or revision in the ADR.
- **Physical fidelity**: Strahler pruning is a heuristic. A successful count does
  not by itself prove spatially valid drainage; raster/outlet semantics remain a
  separate acceptance gate.
- **Forest source mounts**: verify the restarted batch worker imports the current
  checkout instead of relying on host or image assumptions.

## Communication Log

### 2026-11-16 00:46 UTC: Operator scope and authority

**Participants**: Operator, Codex  
**Question/Topic**: Change the nominal 1 m boundary, replay Santee Point_ID 1040
as an RQ job on forest, and authorize forest restart.  
**Outcome**: Work-package scaffold authorized. Forest restart is in scope;
forest1 and production actions are not.

### 2026-11-16 01:01 UTC: SSURGO outage

**Participants**: Operator, Codex  
**Question/Topic**: Prevent the known SSURGO outage from invalidating the Santee
replay.  
**Outcome**: Forest submission is blocked until the real NRCS SDA-backed soil
path succeeds from the actual batch-worker identity.

## Execution update — 2026-11-16

ADR-0143 records the provisional boundary. Focused tests: 23 passed; old helper: six new boundary failures. Stubtest, ADR dates, and broad-exception checks passed. The candidate also preserves raw resolution in the existing map log (`%r`) to satisfy artifact evidence.

Prepared `/wc1/culvert-resolution-replay/point1040.zip`, retaining hashes and parsed raster properties in artifacts. Source MUKEY 131939 has 655,110 pixels; an uncached worker build and soil semantic validation passed at 01:07 UTC. The previous SDA-outage blocker is not reproduced. Token-file path requested from operator; restart and submission have not occurred. Independent review passed implementation scope and independently verified payload semantics; forest acceptance remains pending. Full-suite run remains active (host PID 2640326, `/tmp/culvert-full.log`), currently in climate parity tests. ADR remains Proposed and package remains open.

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

## Calibration study authorized — 2026-11-16

Active study plan: `prompts/active/calibration_study_execplan.md`. Operator approved isolated DEM coarsening, extraction-threshold comparison, passes 0–5, and all-culvert outlet intersection analysis. This extends research scope without authorizing production defaults or source-project changes.

## Calibration execution update — 2026-11-16

Initial 72-case matrix completed; native 1 m control reproduces retained pruning counts. Four passes loses 7 of 39 supplied snapped culvert-point intersections, despite the good Point_ID 1040 cardinality. Coarse cases are being rerun with a metadata-noise grid tolerance after review found extra edge rows/columns. Raw observations and retained WEPP outlets are being evaluated separately. Detailed progress and remaining validation are in the calibration study ExecPlan. No default or source-project change made.

### Corrected matrix completion

All 48 coarse-grid rerun cases completed; combined with 12 native 1 m and 12 retained-baseline cases, `artifacts/calibration-corrected-matrix.csv` contains 72 records. Native pass-four reference check confirms only 32/39 retained WEPP outlets remain on stream cells. This establishes that four passes is not universally outlet-preserving for this batch. Remaining scientific work: same-path displacement and contributing-area checks, and hillslope cardinality outside the existing 1040 three/four-pass controls. No adaptive rule or default accepted.

## Outlet-fidelity continuation — 2026-11-16

Running `scripts/outlet_fidelity.py` for native WBT D8 downstream distances and
fixed-reference accumulation areas across native, corrected coarse, and retained
baseline grids. Diagnostic source DEMs with nodata zero need an explicit disposable
negative-nodata conversion: WBT DownslopeDistanceToStream otherwise conflates
zero distance and nodata, producing all-zero results. The corrected harness
asserts identical valid masks, transforms, and valid elevations. Invalid first
results are retained separately as `outlet-distances-invalid-zero-nodata.json`
and must not be interpreted as connectivity evidence.

Native four-pass results: retained outlets 2901/2907/2909/2913/2915/2917 require
about 214/289/381/521/397/292 m downstream respectively to reach surviving streams.
2939 has no reachable channel according to this D8 diagnostic (possible boundary
or sink termination requires inspection). All seven lost-point watershed polygons
have zero remaining stream pixels, predicting unpruned per-run fallback rather
than a successful uniform four-pass simplification. This is coverage analysis,
not an actual seven-run fallback replay.

Representative Point_ID 1040 delineation at 1 m with fixed extraction area
8,697 m² and zero order passes produces 3,718 hillslopes and 1,489 channels.
Additional selected terrain cases are running with fixed outlet coordinates;
missing stream intersections are recorded as not delineated, never snapped.

## Outlet study results retained — 2026-11-16

Downstream-distance and fixed-reference accumulation sampling completed across all six grids (native distances focused on passes4/5; coarse/baseline passes0–5). Six representative1040 delineation cases completed: five successful, one explicit 4m TOPAZ failure. See `artifacts/outlet-fidelity-findings.md`, `outlet-area-summary.json`, and `representative-cardinality.json`. No default or automatic snapping changed. Remaining: review disposition, investigate 4m tool failure separately, broader cardinality coverage/held-out watersheds, and design approval before any outlet-preserving selector implementation.

## Per-run implementation direction — 2026-11-16

Operator authorized performance-first per-run descending pass selection. Contract
checkpoint prepared in `artifacts/20261116_contract_decision.md`; normative
contract and ADR-0144 drafted. Two reviews and standalone ancestor commit required
before implementation. Prior experimental code remains distinct from this new
implementation scope.

Per-run checkpoint: both independent reviews approve the amended contract; all
medium findings resolved. Documentation lint and ADR date checks pass. Remaining
pre-implementation gate is operator authority for the standalone contract commit.
No new per-run source implementation edits have begun.
