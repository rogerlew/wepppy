# ADR-0114: Preserve equivalent-plane melt support and count storage once

- Status: Proposed; C5a implemented for native validation, not released.
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

No installed binary, existing project selection, Roads default or UI is changed.
A failed scientific gate requires rollback of that candidate while retaining
its evidence. Release promotion is separate; the Roads configuration specification
and layout remain human-gated before implementation.
