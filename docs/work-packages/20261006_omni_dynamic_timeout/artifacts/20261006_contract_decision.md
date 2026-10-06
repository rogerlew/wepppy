# WRT-02 contract decision

## Authority and classification

- **Starting implementation revision**:
  `35cfc8ec5b07cc712c22c483b6f77763f349ad1a`.
- **Operator authorization**: “scaffold and execute a work-package to patch omni
  scenarios/contrasts to use the dynamic timeout,” 2026-10-06 in this Codex
  session.
- **Classification**: intended bounded workflow-scope parameterization/default
  application; Omni leaves change from fixed to workload-derived while WRT-01's
  coefficient, floor, rounding, metadata, and range remain unchanged.
- **Amendment id**: WRT-02.
- **Commit authority**: execution of the requested contract-first work package
  requires and authorizes its standalone ancestor checkpoint.

## Applicable authority

- `docs/schemas/wepp-run-input-contract.md`, WRT-01/WRT-02.
- `docs/adrs/ADR-0076-watershed-runtime-budget.md`.
- `docs/schemas/rq-response-contract.md` (unchanged).
- `docs/schemas/nodb-persistence-concurrency-contract.md` (unchanged).

The closed WRT-01 package and production job are evidence, not normative
authority.

## Exact normative delta

For the existing RQ job-pool concurrency path, a coordinator that will enqueue
one or more Omni scenario leaves or one or more Omni contrast leaves must compute
WRT-01 options once from the base project's normal Climate and Wepp controllers,
after determining that leaves are needed and before enqueueing the first such
leaf. Every newly enqueued `run_omni_scenario_rq` or
`run_omni_contrast_rq` child receives those options.

The calculation occurs before allocating an affected child id, writing affected
child metadata to the parent job, saving that metadata, opening the RQ Redis
connection, or enqueueing an affected leaf. For contrasts it also occurs before
`_rerun_hillslopes_for_contrast_scenarios`. Existing NoDb freshness, stale-run
cleanup, and dependency-state normalization that determine `run_ids` may occur
first; they do not create an RQ leaf or executable rerun artifact.

The WRT-01 formula, metadata schema, positive integer validation, 12-hour floor,
larger caller floor, single-storm behavior, and alarm range are unchanged.
Coordinator, compile, finalizer, and other jobs keep their current timeouts.
Existing jobs are not mutated. Queue names, order, dependencies, retries,
cleanup, auth, locks, inputs, outputs, and completion semantics are unchanged.

## Rationale and compatibility

The observed Omni leaf failed inside watershed execution at the fixed RQ limit.
Omni leaf execution embeds the same continuous watershed workload for which
WRT-01 already supplies a finite measured budget. Reusing that policy is more
compatible and observable than a global constant increase. Additive metadata is
backward compatible. Older workers can execute older jobs unchanged; new jobs
require the code revision that submitted them, as in existing RQ deployment
practice.

## State and input matrix

- **Absent / never used**: no scenarios or no contrasts follows existing return
  or error behavior and does not read timeout workload.
- **Present-empty**: empty/fully skipped leaves do not compute WRT-01 options.
- **Populated continuous**: positive controller years and hillslopes produce one
  finite option dictionary applied to every affected leaf.
- **Populated single-storm**: leaves retain the fixed base timeout and receive no
  `watershed_timeout` metadata.
- **Supported legacy**: accepted positive integer-string years retain WRT-01
  behavior; existing Omni definitions and dependency state remain compatible.
- **Malformed/hostile**: bool, nonintegral, nonpositive, or alarm-range-exceeding
  required workload fails explicitly before the first affected leaf enqueue.

Scenario/contrast definitions, dependency freshness, and stored/filesystem state
remain independently validated by their existing contracts. WRT-02 neither
normalizes nor repairs those states.

## Security and data impact

Security triage is high because RQ resource allowance changes. No input path,
shell command, subprocess argument, authorization rule, secret, network call,
Redis keyspace, or dependency edge changes. Longer finite work may occupy batch
workers longer. Metadata contains model workload counts and selected binary name,
not credentials or new user content.

The authorized submission route, tracked-job conflict checks, configured
scenario/contrast sets, contrast batch size, sequential batch dependencies, and
worker count remain unchanged. WRT-02 adds no fan-out or concurrency. Its
2^31-1-second per-leaf alarm-range maximum can increase aggregate queue occupancy
when many valid leaves are selected; this is an accepted operational risk of the
requested allowance and requires serialized graph plus post-deployment queue
observation, not an unevidenced new cap.

There is no NoDb or artifact schema mutation and no project data compatibility
plan is required. Scientific generation logic and artifact formats remain
unchanged, although a longer-running leaf may complete outputs that a prior
timeout left partial or absent.

## Proposed regression evidence

- Exact calculated timeout and metadata on scenario leaves.
- Exact calculated timeout and metadata on contrast leaves.
- Single-storm fixed behavior.
- Empty/skipped paths do not read unused workload.
- Invalid continuous workload fails before leaf enqueue.
- Compile/finalizer timeouts and all dependency edges remain unchanged.
- Canonical RQ graph check and actual enqueue option inspection.
- Disposable real-Redis serialization, `job_info` dependency-tree inspection,
  and verified cleanup of the uniquely named queue and jobs.

Deployment and retry are separate holds. Rollout requires drained started jobs,
exact revision/container verification, an identified rollback revision, and
post-retry worker/queue review. WRT-02 does not change the known subprocess
cleanup behavior when an RQ timeout does occur.

Two independent read-only reviews and their dispositions must precede the
standalone checkpoint commit. Implementation files remain untouched until that
commit exists.
