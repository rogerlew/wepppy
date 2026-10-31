# ADR-0114: Preserve equivalent-plane melt support and count storage once

- Status: Accepted for the bounded equivalent-melt and storage repairs in 261029 artifact revision 2.
- Date: 2026-10-30.
- Decision venue: WEPPcloud Roads development conversation, America/Los_Angeles.
- Participants: project owner and Codex, with independent implementation/scientific agents.
- Decision owner: project owner, explicitly authorizing continued ablation and remediation.
- Implementer: Codex.

## Context

The pinned `wepp_261029` correctly rejects unfunded water withdrawals in two
Roads generated-soil fixtures. The earlier local-boundary water formulation in
[ADR-0113](ADR-0113-native-roads-boundary-accounting-ablation.md) is rejected:
it changed hydraulic support and deposition semantics. Source tracing now
identifies narrower legacy defects, independently reproduced by native probes.

IRS averages daily melt over connected hillslope lengths. IDAT/DISAG previously
scaled the receiving element's melt shape to that total. At the Charleston stop,
ten hours of upstream melt were compressed into one hour; Birmingham compressed
eleven hours into five. GRNA already preserves upstream pre-event STOLD when
it runs, so ordinary upstream soil updates were not the demonstrated cause.

Separately, GRNA initializes STROFE outside its upstream loop, then repeatedly
adds the accumulated storage at each upstream length. Identical 20 mm available
capacity becomes 20/20/26.67/35 mm across 1/2/3/4 connected elements.

## Proposed decision

For nonchannel connected melt, form a local hourly vector:

`m_eq[h] = sum(L_j * m_j[h]) / sum(L_j)`.

Use the same contiguous IUPRUN footprint as IRS. A positive current WMELT is
required before an upstream HRMLT contributes; WMELT resets daily, whereas
HRMLT can persist when WINTER is skipped. Keep that element's length in the
denominator even when its current source is zero. Derive the existing fitted
melt duration and peak from this weighted vector once, without scaling its
already-weighted depth again. Do not modify the source arrays or hydraulic
geometry. Channel IUPRUN has a different meaning; channels and disconnected
hillslopes retain the original producer path.

Reset GRNA STROFE for each upstream element so each available-capacity term
contributes once. Preserve the existing contributing-set selection, all water
inventory guards, QINF recession calculation, soil parameters, thresholds and
output schemas. Retain the independently validated U2c current-event repair.
These corrections apply to their shared native consumers, not a Roads-only,
material-specific or climate-specific selector.

## Rationale and alternatives

Preserving physical source support fixes the observed deficit without clipping
water, tuning soils or replacing connected hydraulic routing. The storage reset
repairs an explicit summation error; it can increase runoff by removing false
capacity. Rejected alternatives include the C3 local hydraulic formulation,
a return-triggered method switch, global EFFLEN changes, and a new ST snapshot
that would be a null intervention on the actual failure paths.

Independent review also rejected two intermediate implementation details:
channel aggregation based on IUPRUN alone, and stale upstream hourly melt when
current WMELT is zero. Both have retained red/green native controls.

## Validation and limitations

Canonical native package:
`/workdir/wepp-forest-release-20261009/docs/work-packages/20261030-roads-native-accounting/`.
The four original full-period fixtures, native producer controls, heterogeneous
storage sums, unchanged warm/rain-only controls, frozen 840-case Roads replay,
Disturbed matrix and fresh matched Cedar study provide separate gates. Exact
input/output hashes and rejected lanes remain evidence; no magnitude threshold
or withheld material is changed.

Existing DISAG still fits an abstract melt event rather than preserving absolute
clock gaps. This decision does not repair every mixed-rain/breakpoint or
upstream-only-melt branch. GRNA's legacy channel traversal uses processing-order
IUPRUN indices rather than watershed topology; the storage reset changes
multiplicity within that existing set, and does not establish topology-correct
channel capacity. Source-melt channel parity does not imply full-model channel
parity. These limits require explicit non-target assessment, not hidden fallbacks.

## Release and rollback

The owner-authorized revision 2 replaces the undeployed installed binary pair.
Existing project selections, Roads defaults and UI remain unchanged.
A failed scientific gate requires rollback of that candidate while retaining
its evidence. Release promotion is separate; the Roads configuration specification
and layout remain human-gated before implementation.

## Revision 2 acceptance

The final matched source `ba9f2ad91b5165d5cd2954bd64b5df608798541e` is
scientifically accepted for the bounded repairs above and vendored under the
owner-authorized undeployed `wepp_261029` identity, artifact revision 2.
Validation includes 1,059 native tests, 840 Roads physical cases, 99 Disturbed
tests, 18 watchlist cases and fresh matched Cedar outputs. The full 24-year
channel audit has zero negative/nonfinite class transfers, with all nine
standard outputs unchanged by observation. Operational release evidence and
the preserved original identities are in the
[reissue package](../work-packages/20261030_wepp_261029_rerelease/package.md).

Cedar outlet sediment is 517,815.77 kg, about 187.456% above the original
release, principally from recovered channel transport. This is not field
calibration or complete physical budget closure. Regenerate all contributing
hillslope, PASS and watershed outputs with the exact matched pair. Roads
magnitude acceptance remains unmet (719/766 meaningful-reference and 30/74
small-reference cases); defaults and the human UI specification/layout gate
remain unchanged. Earlier experimental dispositions above are retained as
history and do not authorize the rejected C3 formulation.
