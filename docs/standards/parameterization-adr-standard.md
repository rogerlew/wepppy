# Parameterization ADR Standard

## Purpose

Parameterization decisions change scientific behavior and are often made in meetings where implementers may not be decision owners. This standard exists for memory, not blame.

The goal is to preserve:

- what changed,
- why it changed,
- who was present for the decision,
- and what evidence supported the decision.

## Requirement

Any change that modifies model or workflow parameterization must have an ADR in `docs/adrs/` before merge.

This includes changes to:

- default values,
- formulas or transfer functions,
- thresholds or cutoffs,
- unit conversions or scaling factors,
- fallback heuristics when data is missing,
- classification bins that alter generated model inputs.

If an urgent incident fix must merge first, the ADR must be added within one business day.

## Minimum ADR Content for Parameterization Changes

Parameterization ADRs must include the normal ADR sections plus explicit decision provenance:

- Decision Venue: meeting name/channel (for example, "WEPP-in-the-Woods"), date/time, timezone.
- Participants Present: list of attendees present when the decision was made.
- Decision Owner(s): who made or approved the decision.
- Implementer(s): who implemented it.
- Change Summary: exact parameterization delta (old vs new behavior).
- Rationale: why this change was chosen now.
- Alternatives Considered: what was rejected and why.
- Evidence: links to artifacts/runs/plots/issues/work packages.
- Risk and Rollback Notes: known risks and revert conditions.

## Process

1. Draft ADR when parameterization change is proposed.
2. Capture decision provenance at or immediately after the meeting.
3. Implement change with ADR link in PR/work-package tracker.
4. Keep ADR updated if the parameterization is revised later.

## Non-Goal

This standard is not for assigning fault. It is a continuity mechanism so maintainers can understand prior choices without relying on informal memory.
