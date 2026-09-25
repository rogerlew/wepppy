# Independent work-package review

**Date**: 2026-09-25 UTC
**Reviewer**: delegated reviewer `review_upload_work_package`
**Scope**: package brief, ExecPlan, tracker, discovery/Builder assessment, dependency review, and PROJECT_TRACKER entry
**Initial verdict**: Useful discovery package; not ready for implementation
**Current disposition**: WPR-01 through WPR-03 closed after independent re-review; canonical checkpoint still pending
**Evidence**: Read-only document review and source spot checks; no runtime tests

These findings are planning defects, not claims of production failures. The
reviewer made no edits. The parent retained this report and recorded open findings;
no unresolved product choice has been silently ratified.

## Findings

### WPR-01 — High: contradictory disturbance requirements

`package.md:34` rejects a global Disturbed disable, and `tracker.md:38` repeats
that earlier interpretation. `notes/builder_upload_option_assessment.md:9`
proposes a creation-time project-wide disable. The ExecPlan at line 194 still
instructs per-domain bypass implementation and tests uploaded modes with changing
SBS maps. Its introductory caveat defers reconciliation rather than supplying a
consistent executable plan.

Distinguish independent landuse/soil mode selection from the separately selected
creation-time disturbance policy. Mark the earlier bypass matrix historical or
conditional. Once configuration scope is settled, reconcile requirements, decision
logs, milestones, and acceptance. Add explicit implementation milestones for
Builder serialization/resolution, refresh preservation, and feature-policy
enforcement; these are currently concentrated in assessment notes.

**Initial disposition**: Open. Closed by the correction confirmation below.

### WPR-02 — Medium: buffer OFE source assignment is unspecified

The assessment requires uploaded sources across every OFE while the discovery note
preserves non-disturbed modifiers. Neither specifies buffer management behavior.
`wepppy/nodb/core/landuse.py:1562` replaces the final buffer OFE's management with
`mofe_buffer_selection`, independently of Disturbed.
`wepppy/weppcloud/templates/controls/landuse_pure.htm:170` exposes that selection
for multi-OFE projects; `subcatchments_pure.htm:78` separately enables buffer
geometry.

Separate buffer geometry from overriding its management source. The all-OFE
requirement suggests retaining geometry while assigning the uploaded management
to the buffer too. Record that interpretation explicitly before implementation,
including how the buffer-landuse control behaves in uploaded mode. Require
buffered-hillslope consumed-input checks and switching-back tests preserving
ordinary-mode behavior.

**Initial disposition**: Open. Closed by the correction confirmation below.

### WPR-03 — Medium: security artifact comes too late

`package.md:110` schedules dedicated security review during implementation; the
ExecPlan's final milestone schedules it at closeout. For this high-impact
cross-owner enhancement, `docs/standards/contract-first-change-standard.md:162`
requires a dedicated security artifact before the canonical checkpoint along
with independent reviews and dispositions.

Create the design-level security artifact during Milestone 1. Cover upload bounds,
authorization, publication/locking, and feature-policy enforcement. Extend it with
implementation and runtime evidence before closeout. This does not require
runtime proof during documentation scaffolding.

**Initial disposition**: Open. Closed by the correction confirmation below.

## Positive observations and limits

The Builder approach remains plausible. The package correctly identifies supported
management content, source OFE count, upload lifecycle, and configuration
combinations as pending decisions. Static dependency tracing and the
source-to-consumed-artifact acceptance chain are useful. Runtime compatibility
remains unproven and is not represented as complete.

Parent documentation checks before review: all six package Markdown files pass
lint; all 23 relative file links resolve; `wctl doc-refs` confirms the root tracker
entry. These checks establish document integrity, not implementation readiness.

## Next gate

The required WPR correction/re-review is complete. Resolve remaining format and
lifecycle decisions and complete canonical amendments, independent security and
contract reviews, and the contract ancestor before implementation. Runtime
validation remains a separate gate.

## Correction confirmation — 2026-09-25 UTC

Reviewer `review_upload_work_package` re-read the revised living documents and
confirmed: **WPR-01, WPR-02, and WPR-03 are resolved as planning findings**, with
no remaining high/medium contradictions found.

- WPR-01: the brief supersedes per-domain bypass and the ExecPlan now includes
  Builder serialization/resolution, project exclusions, backend enforcement, and
  refresh preservation. Independent run-mode choice remains intact.
- WPR-02: the operator explicitly chose no buffer OFEs. The plan disables buffer
  geometry and management controls for the entire opted-in project, with UI/API/
  build enforcement and generated-topology/mode-switch/refresh/restore acceptance.
  Legacy buffer behavior remains unchanged.
- WPR-03: the design security artifact is present and independent review/disposition
  is required before the canonical checkpoint. No security approval is implied.

The reviewer noted a nonblocking help-text synchronization; the parent had already
updated the Builder assessment help to explicitly mention buffer OFEs during the
review and verified its readback. No production code or runtime tests changed.
Planning closure does not settle pending file-format/lifecycle decisions or approve
the independent security/canonical contract checkpoint.
