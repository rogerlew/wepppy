# Runtime security review — Single User-Defined inputs

## Findings and current verdict

**Bounded security gate: approved for implementation checkpoint
`c1d02d73fdcfa249ee2c424ec0a3ae11c6614a2b` plus the post-checkpoint corrections
reviewed below. All recorded security findings are
resolved.** Final correctness/QA review confirms its findings closed. The final
repository regression gate remains separate and in progress; this approval does
not claim an overall repository pass or authorize production deployment. No
unresolved security finding is accepted as residual risk.

| ID | Severity | Exploit or failure path and evidence | Required action | Status |
| --- | --- | --- | --- | --- |
| SEC-R01 | Medium | Checked projects with stale/restored excluded controllers could call Flask `set_treatments_mode`, `task_set_disturbed_sol_ver`, or `delete_scenarios` and mutate state without checking the creation policy. | Reject before excluded-controller lookup; cover direct mutation routes and any excluded read/report endpoints that restore controllers. Retain direct-route regression evidence. | Remediated: guards precede all affected controller lookups, including Omni queries/reports; three direct mutation regression cases independently passed |
| SEC-R02 | Low | A held soils NoDb lock reached the generic 500 handler; active-job codes differed between the build endpoints. | Return the canonical conflict response before publication/enqueue; test contention preserves the old pointer and source. Align active-job codes with SUDI-01. | Resolved: source correction and retained actual NoDb/Redis boundary evidence show 409/conflict and 409/job_active for both domains, preserving metadata and source bytes |
| SEC-R03 | Medium | Process interruption could retain `.source-UUID` or `.validate-UUID.man` bytes indefinitely. | Idle admission plus module maintenance must precede bounded descriptor-relative cleanup of exact owned regular-file names; preserve symlinks, directories, unrelated entries and retained generations. | Remediated: `_remove_interrupted_staging` scans at most 256 entries; focused cleanup test passed |
| SEC-R04 | High | Earlier management admission accepted native-ignored extra fields and zero mandatory references; generic Python numeric syntax also admitted underscores and values outside native REAL representation. | Enforce strict record widths and references, the certified native count limits, numeric grammar and REAL bounds before publication; reparse serialized management. | Resolved by source readback and focused parser tests, including lexical nonzero underflow; QA-R01/R03 close actual-reader count boundaries and native contour/drain reference propagation |
| SEC-R05 | Medium | Failed metadata publication could leave a candidate or cached pointer inconsistent with the durable controller; malformed saved metadata prevented a valid replacement. | Inspect durable state on failure, retain a durably committed candidate, remove an uncommitted new candidate, restore the cached pointer, and allow valid replacement of malformed metadata. | Resolved: focused filesystem tests plus retained real NoDb/Redis failure-boundary evidence for both domains before/after durable dump; durable selected hashes and previous generations independently read back |
| SEC-R06 | Medium | Earlier read-only admission could write validation staging; nonregular generated files could block or be truncated; unexpected storage errors could expose paths. | Reject read-only projects before storage; use no-follow/nonblocking regular-file checks; translate storage errors to bounded canonical responses. | Remediated by readback and focused filesystem tests |
| SEC-R07 | Medium | Mode-setting routes bypassed active-job admission; checked raster builds could reacquire their own maintenance lock; invalid buffer input could be rejected after accepting a replacement source. | Share admission with mode mutations, avoid nested module acquisition, and validate checked-project buffer requests before source acceptance. | Resolved by readback, focused route tests and real NoDb/Redis admission evidence; queued-receipt tests are not presented as worker timing-race stress tests |
| SEC-R08 | Medium | `require_idle` read only `rq:*` receipts, omitting `archive:job_id`. Archive/restore jobs could overlap source validation/publication; archive could capture mismatched source/pointer state and restore could remove the source directory. Fork admission leased only the destination, allowing a checked source fork to start after an upload's idle check; concurrent forks could overwrite the source's single fork receipt. | Include archive receipts in idle checks; under the shared lifecycle lease, reject checked-project archive/restore while source work is active. For checked-source forks, hold a source lifecycle lease and idle check through source receipt/enqueue commit, before target side effects. Retain both-ordering tests. | Resolved: source readback confirms guards and sorted source/destination leases before mutations, with source checkpoints through receipt/enqueue; live boundary evidence covers active builds blocking archive/fork and active archive/restore receipts blocking uploads |
| SEC-R09 | Low | Eight Omni workers and three SBS/Treatments/Debris Flow project workers evaluated the policy guard before initializing error-telemetry locals. An excluded-project rejection could be masked by `UnboundLocalError`, obscuring the original policy diagnosis. | Initialize `func_name` and `status_channel` before the guard while keeping it before STARTED, recovery, excluded-controller hydration and mutation. Preserve established structured exception telemetry. | Resolved by bounded readback and eleven independently passing checked-policy worker cases; the original policy error propagates without a STARTED event or excluded feature execution |

Unresolved recorded findings: high 0, medium 0, low 0. Resolved rows record
implementation corrections and cited evidence; they do not imply completion of
all release validation.

## Metadata and threat model

- Package: `docs/work-packages/20260925_single_user_defined_landuse_soils/`.
- Reviewer: independent security reviewer `/root/review_single_input_security`.
- Date: 2026-09-25.
- Follow-up readbacks and evidence updates: 2026-09-26 UTC, including SEC-R08 closure,
  actual publication-failure recovery and authenticated source downloads.
- Final runtime snapshot: `c1d02d73fdcfa249ee2c424ec0a3ae11c6614a2b`; earlier interim
  reviews used uncommitted implementation on contract checkpoint `0efd7ea46`.
- Related: [design security review](20260925_security_review.md),
  [contract reviews](20260925_contract_reviews.md), and
  [canonical SUDI-01 contract](../../../schemas/single-user-defined-inputs-contract.md).

Security impact is high: authenticated run writers supply untrusted files that
cross multipart, Python parser, run filesystem, NoDb, RQ and native WEPP boundaries.
Existing authentication, run scope, CSRF/session-token behavior and runtime
identities remain authoritative. The attacker controls request fields, names and
file bytes, not the service account or arbitrary server filesystem writes.
Unexpected stale or malformed saved state must fail explicitly and remain
recoverable. Missing optional source state is valid until mode 5 Build requires it.
Unchecked projects and existing raster uploads must retain their valid workflows.

No new secret, external network destination, dependency, privilege, service,
subprocess construction or deployment topology was found in the reviewed helpers.
Accepted display names are separated from SHA-256 storage identities; uploaded
names are not shell arguments or storage path components.

## Reviewed boundaries

- `wepppy/microservices/rq_engine/single_input_uploads.py`: bounded streaming before
  generic payload parsing, one file, 64 fields, 16 KiB scalar/header bounds,
  5 MiB source parts independent of field order, preserved 500 MiB raster part,
  aggregate limit and all-exit spool cleanup. Unknown or duplicate source fields,
  incomplete bodies and nonmultipart source-file fields reject explicitly.
- `wepppy/wepp/single_input.py` and strict management parsing: UTF-8 text envelope,
  fixed record/count/reference bounds, complete supported-format consumption,
  no native-ignored modern fields, one source OFE, and canonical serialization.
  Certified versions remain management 98.4 and soil 7778 with `wepp_260803`.
- `wepppy/nodb/single_input_sources.py`: managed run/projection roots,
  descriptor-relative no-follow opens, immutable hash publication, fsync before
  metadata, durable-pointer-aware rollback, previous-generation retention,
  malformed-state recovery and regular-file generated output.
- `wepppy/rq/single_input_admission.py`, landuse/soils routes and workers: trusted
  creation policy, read-only and active-job rejection, shared run submission
  lease, module maintenance lock, NoDb mutation and existing queue submission.
- Builder, feature dependency closure, runtime feature visibility and direct
  Disturbed/dependent task surfaces. SEC-R01's Flask gaps are closed. Readback also
  confirms the correctness review's Disturbed effective-management preview guard
  now precedes controller lookup and report links honor the creation policy.

## Independent validation evidence

The following command completed with **56 passed**, six preexisting deprecation
warnings, in the canonical Docker `weppcloud` test environment:

```console
wctl run-pytest tests/microservices/test_single_input_uploads.py tests/nodb/test_single_input_sources.py tests/nodb/test_single_input_policy.py tests/wepp/test_single_input.py --maxfail=1
```

These tests exercise actual streamed multipart parsing and filesystem operations:
valid uploads, dishonest Content-Length, source oversize, duplicate/unknown fields,
incomplete multipart, oversize/too-many scalar fields, closed temporary handles,
symlink containment, supported managed projection roots, read-only rejection,
replacement retention and injected publication failures.

`test_single_input_sources.py` uses a fake `SourceController` for locking, dump,
cache and detached loading. Its filesystem coverage is direct; it does **not**
alone establish real Redis/NoDb concurrency or failure recovery; the separate live
evidence below covers those boundaries. The parser suite is
scoped to the certified subset. The final QA review below adds actual-reader
maximum/maximum-plus-one fixtures; native tests remain representative executions.

After the cleanup change, the independently rerun
`test_idle_replacement_removes_only_owned_regular_staging` passed (one test,
two preexisting warnings). It proves owned regular staging removal and retention
of unrelated files, matching directories, symlinks and the previous generation.

The implementation owner reports native execution at 2 and 12 OFEs and is running
real default-queue worker acceptance under uid 1000/gid 993. The reviewer has now
inspected [upload/job evidence](20260926_upload_job_acceptance.json) and
[native evidence](20260926_native_acceptance.json), independently matched all ten
generated input hashes and both accepted source hashes to the disposable run, and
confirmed nonempty `H1.loss.dat` and `H2.loss.dat` outputs with the recorded sizes.
The [retained job-status readback](20260926_job_status_readback.log) records both
jobs finished on the default queue, with corresponding JSON provenance. The job
records later expired before an `ended_at` capture; no timestamp was invented. Synthetic
hillslope topology and controlled climate do not prove DEM delineation or a full
interactive workflow. An old worker failed to load new enum value 5; acceptance
used a fresh process. No production rollout approval is claimed.

Follow-up independent command completed with **35 passed**, four preexisting
warnings, including the three SEC-R01 route rejections and source lifecycle suite:

```console
wctl run-pytest tests/weppcloud/routes/test_soils_bp.py tests/weppcloud/routes/test_treatments_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/nodb/test_single_input_sources.py --maxfail=1
```

The reviewer inspected the executable acceptance script and retained
[12-case boundary evidence](20260926_boundary_acceptance.json). It exercises real
NoDb locks and Redis queued receipts through the actual authenticated build
routes: lock 409, read-only 403, active-job 409, active source work blocking archive
and fork, and a queued restore receipt blocking source upload. Both source domains
assert unchanged durable metadata and source bytes after rejection. Queued jobs here
are deliberately saved test receipts; the test does not execute destructive
restore work while attempting an upload.

[Archive round-trip evidence](20260926_archive_acceptance.json) runs the real
archive/restore functions in the worker environment under uid 1000/gid 993.
Independent readback matched both source hashes inside the ZIP, after restoration,
and in the unrelated `single-input-copy-20260925` fork. The
[fork acceptance](20260926_fork_acceptance.json) uses an actual RQ worker and
records a finished `fork-archive` job, matching source metadata,
policy and usable management/soil summaries. The generic prefix-target fork
relocation defect is preexisting and retained in the
[correctness review](20260926_correctness_review.md); the failed prefix-target run
does not count as functional acceptance.

Source readback closes the archive/restore reverse-admission branch as well as
fork source admission: sorted lifecycle leases are acquired before target changes,
idle is checked under them, and source lease checkpoints precede receipt/enqueue.
Unchecked project behavior retains its existing admission path.

The reviewer inspected [publication-failure evidence](20260926_publication_failure_acceptance.json)
and its executable `publication_failures()` action. It uses actual controllers,
run submission/module/NoDb locks, filesystem and Redis cache, deliberately raising
`OSError` immediately before or after the real controller `dump()`. All four
domain/phase combinations report bounded 500 errors, a readable durable selected
source, cache/persisted pointer agreement and preservation of the prior generation.
The reviewer independently read the post-fault NoDb JSON, selected source hash and
previous file for both domains. This establishes rollback and postcommit retention
at the publication boundary; it is not a physical ENOSPC or power-loss test.

[Authenticated Browse/download evidence](20260926_download_acceptance.json) uses
the actual Browse application with a run-scoped bearer token. Both listings and
downloads return 200; downloaded SHA-256 values match the accepted source identities.
The reviewer independently matched those retained hashes to the actual source files.
Tokens are generated in memory and are not retained in the artifact.

Readback confirms that both numeric entry paths detect a nonzero mantissa before
accepting a value below native REAL range, including `1e-999` and `-1e-999` that
Python float would otherwise turn into zero. The independently rerun numeric
regressions cover decoder and soil validation: `wctl run-pytest
tests/wepp/test_single_input.py -k native_numeric_values_rejected --maxfail=1`
completed with **5 passed**, two existing warnings.

Final security readback verifies the native-reference correction remains opt-in:
strict uploads/new source summaries enable it, checked-project catalog summaries
propagate it, and segment materialization, synthesis, prepared-file reading and
validation preserve it. Ordinary legacy reads retain the previous default. The
flag is independent of strict upload admission, so corrected reference semantics
do not impose the upload-only grammar on compatible catalog modifiers.

The final [QA review](20260926_qa_review.md) and
[correctness review](20260926_correctness_review.md) independently record
**52 passing tests**: 39 numeric/count-boundary cases and 13 asymmetric reference
cases, including three native `wepp_260803` executions. Security review inspected
those fixture assertions: unequal contour/drain counts, distinct selected values,
persisted summary reload, both synthesis paths, segment materialization, prepared
files and the preserved legacy interpretation. Actual serialized section/event/
year/rotation/layer maximum and maximum-plus-one fixtures, canonical synthesis,
and 32/33-OFE checks close the outstanding QA-R01 proof gap. The separate
32-OFE native regression is recorded in the validation summary. No new security
blocker was found in the committed reference remediation.

[Browser evidence](20260926_browser_controls.json) is bounded to rendered control
partials and shared CSS in three Chromium themes, including native chooser
selection, actual Tab reachability and preserved accepted-file feedback. It does not establish full
controller-bundle submission, browser authentication, read-only
interaction or complete accessibility certification. Controlled native slopes and
climate similarly do not establish end-to-end DEM/model project acceptance.

## Security verdict and remaining repository gate

### Post-checkpoint error-path review

The late `wepppy/rq/omni_rq.py` correction moves only the eight policy guards below
initialization of their error-telemetry locals. The guards still precede STARTED,
root recovery, controller hydration, enqueue and mutations. Independent command
`wctl run-pytest tests/rq/test_omni_rq.py -k
excluded_workers_preserve_policy_error_before_hydration --maxfail=1` completed
with **8 passed**, ten existing deprecation warnings. Each case preserves
`SingleInputPolicyError`, emits one plain EXCEPTION event and never hydrates Omni;
the scenario worker additionally retains its established EXCEPTION_JSON event with
the correct error type. The initial test's one-total-message assertion was corrected
to preserve that existing telemetry contract. The owner's combined late regression
log records 46 passing tests; this reviewer did not rerun that entire set.

The same bounded correction was subsequently applied to `init_sbs_map_rq`,
`build_treatments_rq` and `run_debris_flow_rq` in `project_rq.py`. Each guard remains
before STARTED, cache clearing, module locks, excluded-controller lookup and work.
SBS initialization reuses the existing single Ron lookup for its guard and action.
Independent command `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py -k
excluded_project_workers_preserve_policy_error --maxfail=1` completed with
**3 passed**, five existing deprecation warnings. Each case propagates
`SingleInputPolicyError` and emits exactly one EXCEPTION event. The owner's broader
route/worker log records 120 passing tests; this is distinguished from the three
independently rerun cases. RUSLE, PATH and postfire guard readback confirms their
policy exceptions do not enter the affected uninitialized-local handlers.

Readback also confirms the late `Soils.build` change defers watershed lookup only
when the project policy is unchecked. Checked runs still perform full policy and
buffer validation; unflagged mode 5 still fails `require_enabled`. The five new
capability catalog records now name the actual implementation `first_reader_revision`
`c1d02d73f`; their payloads/hashes and existing catalog records are unchanged.
These narrow post-checkpoint changes introduce no unresolved security finding.

The independent security review approves the bounded implementation at the
recorded commit plus the reviewed corrections above, with high 0, medium 0 and low 0 unresolved findings. The reviewed
controls preserve the contracted valid states within the explicit evidence scope.
Any subsequent material security-path change requires review against this snapshot.

The [validation summary](20260926_validation_summary.md) separately tracks the
repository regression sweep, which remains in progress at this sign-off. Its
management stubtest reports **143 existing incomplete/stale surface entries**;
none identify the changed `Management.load`, `ManagementSummary.get_management`
or `get_management_summary` signatures. The committed stubs include the new
optional parameters. Package-wide management script typing debt is also retained;
these checks are not represented as passing. This existing typing debt is not a
new security finding and is not silently waived by security approval.

No production rollout was performed or approved. Native execution uses controlled
topology/climate; browser coverage is partial; the unrelated-target fork succeeds
while the preexisting source-prefix target defect remains documented. These are
explicit practical limits of the evidence, not claims of exhaustive certification.

No unresolved medium/high finding may be silently accepted at closeout. Operator
authorization to implement does not substitute for the required release evidence.
