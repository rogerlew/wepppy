# Tracker — Single User-Defined landuse and soils

## Quick status

**Started / last updated**: 2026-09-25 UTC
**Phase**: Builder scope approved; WPR-01 through WPR-03 independently closed
**Implementation**: Not started
**Security impact**: `high`; design artifact created, independent security review pending before checkpoint
**Next milestone**: Resolve remaining design choices and complete canonical checkpoint
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
- [ ] Resolve remaining format/content, source OFE count, lifecycle/bounds, and concrete interface decisions.
- [ ] Amend canonical contract/source matrix and parameterization ADR with decision provenance.
- [ ] Complete independent design security review and two contract reviews; close design findings and record ancestor checkpoint.
- [ ] Implement Builder policy, dependency/buffer enforcement, refresh, secure sources, builders, and controls.
- [ ] Validate all four input combinations, non-buffer OFE replication, compatible modifiers/features, and legacy behavior.
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
[package requirements](package.md#confirmed-requirements-and-rationale). Exact
contract/interface and upload-format/lifecycle details remain pending.

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
