# Tracker — Single User-Defined landuse and soils

## Quick status

**Started / last updated**: 2026-09-25 / 2026-09-26 UTC
**Phase**: Runtime implementation and artifact validation
**Implementation**: In progress after contract ancestor `0efd7ea46`
**Security impact**: `high`; independent design review approved; runtime findings closed; final repository gates running
**Next milestone**: Complete environment acceptance and runtime reviews
**Active plan**: [ExecPlan](prompts/active/single_user_defined_landuse_soils_execplan.md)

## Task board

### Done

- [x] Inspect controls, parser/version precedent, builders, preparation, and configuration authority.
- [x] Complete delegated static dependency tracing and independent package review.
- [x] Record operator-selected Builder policy, independent input choices, multi-OFE support, and compatible modifiers.
- [x] Record operator instruction to disable buffer OFEs whenever the Builder feature is enabled.
- [x] Reconcile current docs/ExecPlan and create pre-checkpoint design security artifact.

### Pending

- [x] Obtain reviewer confirmation of WPR-01 through WPR-03 corrections (2026-09-25 UTC).
- [x] Resolve format/content, source OFE count, lifecycle/bounds, and concrete interfaces in SUDI-01.
- [x] Amend canonical contract/source matrix and parameterization ADR with decision provenance.
- [x] Complete independent design security/contract reviews; record ancestor checkpoint `0efd7ea46`.
- [x] Implement Builder policy, dependency/buffer enforcement, refresh, secure sources, builders, and controls.
- [x] Validate all four input combinations, non-buffer OFE replication, compatible modifiers/features, and legacy behavior.
- [ ] Extend security evidence and complete correctness/UX review; update docs and close out.

## Current decisions

**2026-09-25 UTC — Builder scope:** The operator directed reconciliation of WPR-01
around the Builder checkbox. Unchecked preserves current behavior; checked enables
upload capabilities and excludes Disturbed/SBS/dependent features project-wide.
Independent choice means selecting landuse and soil modes separately, not applying
different disturbance policies. The initial per-domain bypass interpretation is
superseded. No class selectors, mixed-SBS upload workflows, or legacy-only scope.

**2026-09-25 UTC — Buffers:** “disable the buffer ofe when this feature is enabled.”
Disable buffer geometry and buffer management controls, set `watershed.mofe_buffer`
false, and reject attempts to enable it through APIs/builds. Keep this policy when
run modes change or configuration refreshes. Ordinary multi-OFE remains required;
other compatible modifiers remain functional. Existing projects retain buffers.

**2026-09-25 UTC — Review sequence:** WPR-03 is addressed by creating the
[design security artifact](artifacts/20260925_security_review.md) before the
checkpoint and requiring independent design review/disposition at Milestone 1.
Implementation evidence extends that artifact later; approval is not claimed now.

**Compatibility:** Append unused mode identities and preserve legacy metadata/schema
reads. Product decisions and rationale are in
[package requirements](package.md#confirmed-requirements-and-rationale). Exact interfaces, supported formats and lifecycle are ratified in SUDI-01.

## Review disposition

| Finding | Correction | Status |
| --- | --- | --- |
| WPR-01 — conflicting disturbance scope | Current brief, discovery, Builder design, and ExecPlan now use the Builder-wide policy with independent run-mode choice; explicit Builder/refresh/enforcement milestone | Closed; independently confirmed 2026-09-25 UTC |
| WPR-02 — unspecified buffer assignment | Operator chose no buffer OFEs, not retained geometry with replacement management; UI/API/build/refresh and no-buffer artifact tests specified | Closed; independently confirmed 2026-09-25 UTC |
| WPR-03 — security review too late | Dedicated design artifact exists and must be independently reviewed before checkpoint; implementation security evidence added later | Closed; independently confirmed 2026-09-25 UTC |

The [initial review](artifacts/20260925_work_package_review.md) remains the record
of findings against the prior draft. Confirmation of these corrections does not
complete the canonical/security checkpoint or outstanding design decisions.

## Risks and verification gates

| Risk | Required evidence | State |
| --- | --- | --- |
| Excluded feature restored by activation/refresh | Direct/transitive API/task denials before mutation; policy-preserving refresh | Implementation pending |
| Buffer geometry or source override slips into output | No-buffer slope/management/soil topology after create/build/mode switch/refresh/restore | Implementation pending |
| Cleanup or replacement loses/mixes sources | Repeated builds, real publication failure and concurrent-build tests | Design details pending |
| Unsupported file content/version silently changes meaning | Accepted format subset and semantic comparison at actual consumer | Design details pending |
| Compatible features or legacy behavior regress | RAP/Ash/Geneva checks, old BAER alternatives, unchecked disturbance and buffers | Implementation pending |

## Progress and evidence

Initial source inspection used revision
`b96f77e589ec033853970ac90fdab945490c6553`. The
[dependency review](artifacts/20260925_dependency_review.md) identifies exclusions
and conditional preservation. The independent package review found three planning
issues; the operator directed their correction in this session.

No runtime code, live-run data, or deployment was changed. Documentation lint and
relative-link checks are run on this revision before handoff. Source-header counts
and parser inspection are evidence for recommendations, not runtime certification.
The checkpoint, production implementation, and environment acceptance remain pending.

## Correction review and validation — 2026-09-25 UTC

Reviewer `review_upload_work_package` confirmed all three planning findings closed
with no remaining high/medium contradictions in current living docs. Confirmation
is retained in the review artifact. The initial alternative of retaining buffer
geometry was rejected by the operator in favor of disabling buffer OFEs entirely.

All eight package Markdown files and PROJECT_TRACKER pass scoped lint with zero
errors/warnings; all 25 relative file links resolve and diff whitespace checks pass.
Spelling preview retained the country name Chile. These are documentation checks;
independent design security approval, exact canonical checkpoint, and runtime
validation remain pending. No production implementation or deployment occurred.

## Execution authorization and checkpoint

2026-09-25: operator instructed committing the complete worktree then executing
the package. Snapshot commit: `cb09ab422`. Canonical SUDI-01 contract and ADR-0075
are drafted; independent design reviews and checkpoint ancestor remain pending.
No runtime files have been edited.

## Execution design resolution (2026-09-25)

The canonical [SUDI-01 contract](../../schemas/single-user-defined-inputs-contract.md) supersedes earlier pending recommendations.
Initial support is management98.4 and soil7778, exactly one source OFE, for current
Builder default `wepp_260803`; the native reader ignores modern2016.3 fields, so
2016.3 is rejected. Source/raw/generated lifecycle, bounded multipart admission,
exact interfaces and errors are specified there. Uniform assignment is the Build
outcome; subsequent deliberate class edits remain functional and rebuilding
mode5 restores uniform source assignment. Native-reader bounds apply before
execution; no buffer geometry or silent topology truncation is permitted.

Both independent reviewers approved the final design by2026-09-25 21:58 UTC.
All medium/high design findings closed; see
[review dispositions](artifacts/20260925_contract_reviews.md).

Contract ancestor: `0efd7ea46` (standalone, before runtime edits). Milestone2
Builder policy implementation started2026-09-25 22:00 UTC.

Milestones2–3 in progress: Builder/capability/update tests134 passed; Builder
controller19 passed; rendering/watershed251 passed; parser subset26 passed.
Source lifecycle/builders/multipart wiring and end-to-end evidence remain pending.


## Runtime progress — 2026-09-25

All-worktree snapshot: `cb09ab422`; contract ancestor: `0efd7ea46`.
Builder/policy/refresh, source admission, run modes and themed controls implemented;
remaining acceptance and review findings are tracked in the active plan.
Focused evidence:105 parser/routes/MOFE regressions;210 upload-boundary/lifecycle/
render tests;49 Builder/landuse/soil controller tests;28 policy/artifact tests.
Actual `wepp_260803` execution passed for uploaded management/soil at2 and12OFEs.
Config-refresh preview/apply preserves policy, both capabilities, no-buffer setting
and source sentinel. These are local test results, not deployment approval.

Interim reviews found and prompted fixes for ignored modern management fields,
mandatory references, native numeric representation, publication rollback,
malformed metadata recovery, ordinary soil normalization, numeric OFE ordering,
and active initial-condition cover overrides. Final runtime reviews remain open.


## 2026-09-26 validation continuation

Both real authenticated upload requests and their existing default-queue jobs
completed in the disposable acceptance project. Stale worker daemons required a
fresh process within the same worker container (uid1000/gid993); no shared daemon
was restarted. Real generated 2/12-OFE management/soil/slope files executed with
260803 and produced loss files of 10,081 and 35,308 bytes. Controlled topology and
climate limit this evidence to the input/worker/native path.

Latest focused UI/routes: 283 passed. Restored upload transport: 33 Jest tests
passed, including legacy raster mode4 and both mode5 controls. Full Jest previously
passed 915 tests. Test-stub completeness passed. Full Python validation continues
after explicit legacy policy fixture updates. Runtime security review remains open;
excluded direct mutations, crash staging cleanup and lock-conflict responses are
being closed with regression coverage. See the active plan and runtime review for
remaining acceptance gates. User/operator/developer guidance is in
[the input guide](../../dev-notes/single-user-defined-inputs.md).


### Retained runtime acceptance and review

- [Security review](artifacts/20260925_runtime_security_review.md) and
  [correctness review](artifacts/20260926_correctness_review.md).
- [Upload/job acceptance](artifacts/20260926_upload_job_acceptance.json) and
  [native files/output evidence](artifacts/20260926_native_acceptance.json).
- [Real Redis/admission boundaries](artifacts/20260926_boundary_acceptance.json):
  held NoDb lock, read-only, active builds, archive/fork reverse admission, and
  active archive rejection for both input domains; prior sources unchanged.
- [Archive/restore](artifacts/20260926_archive_acceptance.json) and
  [fork with unrelated target](artifacts/20260926_fork_acceptance.json) preserve
  source metadata/hashes; copied summary files are readable.
- A preexisting generic fork bug duplicates target suffixes when the target name
  contains the source name. That initial acceptance target failed usable-summary
  validation and is not counted as successful fork evidence. The correctness
  artifact records the separate defect; this package does not change relocation.
- Runtime stubtest passes for landuse and soils; broad-exception enforcement passes
  after relocating existing allowlist line anchors (no new boundary exemptions).

- Final validation: 258 focused parser/preparation/Omni tests pass; native 32-OFE
  execution passes. Correcting contour/drain reference propagation only for
  checked projects, with asymmetric consumer regression coverage in progress.
- Real publication fault and authenticated download evidence is retained in
  `artifacts/20260926_publication_failure_acceptance.json` and
  `artifacts/20260926_download_acceptance.json`.
