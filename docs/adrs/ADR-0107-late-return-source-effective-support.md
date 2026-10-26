# ADR-0107: Late return-only source metadata and effective support

Status: Accepted — shipped in wepp_261026
Date: 2026-10-26

## Context

A dry-day CONTIN path skips IRS, then hourly water balance creates terminal
surface drainage. Legacy EVENT can contain positive volume with zero duration,
zero peak and inactive SRC3. 261021 rejects this untyped source. 261010 and 260803
also emit it; the new stop exposed a longstanding producer-contract defect.

## Decision and exact change

Capture the terminal OFE's 24 hourly return amounts immediately after the existing
late water-balance call, using separate daily-reset state. Eligibility requires
continuous hourly hillslope execution, no contour, no preceding runoff, zero
rain/melt/irrigation and duration, and no existing active mixed source. For a
positive late return, serialize authoritative terminal runvol directly into a
return-only SRC3 component. Retain all original EVENT values and schema v3.

Use unchanged MIXRETURN effective support T=3600*sum(weights)/max(weights) for
return-only sources, as a constant-rate block from midnight. This preserves the
caller-supplied volume through overlap integration, subject to existing printed
precision. It does not preserve hourly occurrence or establish travel time.
No repeated water balance, area multiplication, rainfall-duration substitution,
physical peak/erosion change or consumer guard removal is allowed.

## Decision provenance

Decision Venue: this Codex/operator conversation, 2026-10-26, America/Los_Angeles.
Participants Present: project operator and Codex; independent science-review agent.
Decision Owner: project operator (Roger Lew).
Implementer: Codex.
Authorization: “complete the release gates…release as wepp_261026” following
recommendation to ship this bounded repair with the disclosed existing limitation.
No deployment or binary-default change was requested.

## Rationale and alternatives

The tested correction preserves 491-hill non-target outputs exactly, changes only
two source records, and completes the nine-year primary watershed. Source probes
cover both reported triggering hillslopes, all calendars, reset, invalid data,
area ownership and numerical reconstruction. Literal-hour forcing was previously
rejected after late pulses/recession enlargement; a shifted rectangle introduces
an unvalidated timing rule. Disabling the guard or inventing a 24-hour duration
would hide source provenance. Keep timing refinement separate.

## Evidence, consequences and rollback

Native incident: docs/ablation/20261026_redoubled-catmint_zero-duration in
wepp-forest. Release evidence: [261026 package](../work-packages/20261026_wepp_261026_release/package.md).
Effective supports in retained witnesses are 4.72, 6.41 and 1.27 hours, beginning at
midnight despite afternoon/evening hourly bins. This limitation is accepted for
the bounded release, not observational validation or universal water closure.

Complete both affected watersheds, native/compatibility gates and final reviews
before release. Preserve older binaries/reports. Roll back by choosing a prior
matched pair and regenerating contributing hills/PASS/watershed outputs; prior
versions may reproduce the stop or mishandle untyped sources. No silent fallback.
