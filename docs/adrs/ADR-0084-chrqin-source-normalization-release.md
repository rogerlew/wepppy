# ADR-0084: CHRQIN Source Normalization and WEPP 261010

Status: Accepted
Date: 2026-10-10

## Context

The undeployed wepp_261009 exposed a pre-existing CHRQIN indexing error when
its component interface supplied small rainfall volumes separately from return.
The normalization excluded the first real sample on initialized calls, then
delivered that sample with an inflated multiplier. Topanga's January 18, 1993
undisturbed outlet peak reached 707.63910 m3/s. Roger judged that physically
unacceptable; observer-neutral traces and captured native-routine tests located
the first inflation before channel routing.

## Decision

Release the validated candidate as wepp_261010 and vendor its watershed and
hillslope pair in WEPPpy. Remove the never-deployed wepp_261009 pair and their
sidecars from WEPPpy's selectable binaries, retaining historical evidence.

Normalize using every delivered positive-time sample. Subtract qin0(0) only
when nt0=0 and that endpoint was accumulated. Do not restrict the repair to
mixed-return sources: ordinary sources must follow the same sample accounting.
Retain hourly MIXPEAK, PASS v3 and accepted channel-state continuation unchanged.
No model parameters, rrinit, flags, capacities, banner or general project
defaults change. Deployment is a separate action, not part of this decision.

## Decision Provenance

- Decision Venue: Roger/Codex workspace conversation, 2026-10-10,
  America/Los_Angeles; exact message time not retained.
- Participants Present: Roger Lew and Codex.
- Decision Owner: Roger Lew, explicitly requesting release as wepp_261010,
  vendoring and removal of undeployed wepp_261009 after the completed studies.
- Implementer: Codex.

This promotion authorization supersedes the preceding release hold. It does
not erase the reported ordinary-event sediment consequences or establish
their accuracy against observations.

## Rationale and Alternatives

The smallest arithmetic correction fixes the demonstrated defect without
changing routing architecture or inventing precision requirements. Topanga's
target peak falls to 12.50683 m3/s. Mutation and disturbed hillslope results
remain exactly unchanged. Cedar preserves hillslope yield and sampled outlet
volume is +0.001008% versus the wepp_260803 baseline over 24 years.

Retaining the defective denominator to preserve legacy output is rejected.
A reporting-only cap would leave incorrect physical source pulses. Restricting
the fix to surface-return events would preserve the same error in ordinary
sources. Routing reconstruction and comprehensive closure remain out of scope.

## Consequences and Limits

Ordinary-event effects are real: a burned Rattlesnake peak changes 44.54780
to 20.21181 m3/s, while another event's sediment changes 140954.78 to
621811.88 kg with unchanged hillslope sediment inputs. Cedar's accounting gap
is close to the original baseline but worse than 261009's. Neither event
sediment accuracy nor universal conservation is established by this release.

Use fresh same-build hillslope passes for every watershed rerun. Local projects
explicitly selecting 261009 must select 261010 and regenerate; do not silently
alias the retired name. Historical reported results retain their true build
identity. The existing paired v3 reader and combiners remain required.

## Evidence

- [Mechanism and native reproducer](../work-packages/20261009_topanga_jan1993_outlier/mechanism-findings.md)
- [Four watershed comparisons](../work-packages/20261009_topanga_jan1993_outlier/candidate-results.md)
- [Mutation and disturbed rankings](../work-packages/20261009_topanga_jan1993_outlier/hillslope-studies.md)
- [Fresh Cedar comparison](../work-packages/20261009_topanga_jan1993_outlier/cedar-results.md)

## Risk and Rollback Notes

Keep the bounded native regression and independently generated watershed
evidence. Reassess if representative cases expose unacceptable consequences;
do not compensate by tuning parameters or silently changing source eligibility.
Binary rollback requires an explicit scientific/operator decision, a paired
historical executable selection and fresh matching passes. Do not restore
261009 as a silent fallback. Required gates use committed resources; external
watershed studies remain supplementary evidence.
