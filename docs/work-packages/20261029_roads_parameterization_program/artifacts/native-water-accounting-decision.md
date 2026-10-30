# Decision needed: native negative-water-balance reset

## Finding and proposed action

An exact-binary debugger replay proves a water-accounting defect in pinned
`wepp_261026`, source `b73e93b19a724d1991d341d38a18d11e742231bd`.
The proposed next action is an isolated native fix/control comparison, retaining
261026 unchanged as the control. A validated correction would require a new binary
identity before it could support the Roads parameterization goal. No deployment or
replacement of existing project binaries is proposed.

The operator requested 261026 and the autonomous charter freezes that identity.
Therefore a revised native target requires an explicit scope decision. This is not
permission to weaken physical acceptance, exclude failing configurations, or adjust
soil values merely to avoid a model defect.

## Exact reproducer

Source case under the program scratch root:
`engineered-surface-screen-v1/matrix-v1/birmingham-sand-inbare-gravel-none-erosion_road_cap-project/`.
It has generated sandy soil, the configuration-matched road erosion parameters,
road forest adjustment disabled, upper-200mm conductivity capped by the road
reference, and the complete declared project runtime bundle. All deeper material
and lower boundaries are generated-soil values.

The engine stops on first-year day 9, OFE 2, hour 20. The corresponding rocked-ditch
case also fails. Changing source-informed fill/buffer drainage or restoring legacy
role initial saturation did not resolve the reproducer. These are retained negative
results, not reasons to tune further around the defect.

`hourly-water-trace-v2` uses the pinned binary and snapshotted container libraries.
All seven generated native outputs, including truncated failure outputs, match the
ordinary container run byte-for-byte. `negative-fin-proof.json` retains hashes and
observed state; the debugger script and complete log remain in the scratch root.

Portable fixture: `negative-fin-reproducer.zip` (114,448 bytes), containing only
the declared native input files and a hash manifest. It needs no original project.
Verified command (choose a fresh destination):

```bash
wctl exec weppcloud python docs/work-packages/20261029_roads_parameterization_program/artifacts/reproduce_negative_fin.py --root /wc1/runs/ro/roads-parameterization-program-20261029/portable-reproducer-check-v1
```

The command passes only when the expected stop and all seven native file hashes
match. `git apply --check` also passes for the proposed patch against an isolated
copy of the pinned source. No patched native executable has been built.

| Quantity | Observed value |
| --- | ---: |
| Local rainfall | 41.2000045 mm |
| Residue interception | 2.62361835 mm |
| Net local water input | 38.57638615 mm |
| Signed balance before negative-FIN reset | -22.576984 mm |
| Signed balance after reset | -61.1533709 mm |
| Initial available mobile storage | 50.2315061 mm |

The increase in requested withdrawal equals the discarded net local input to
0.00000075 mm. Upstream `ui_HUrunf` and `runoff(1)` are identical in this event,
so this observation is not an upstream-field substitution ambiguity.
The original hour-20 unmet demand is 0.0436921 mm; the cause is not roundoff at that
threshold. The signed balance was changed by 38.576 mm earlier in the routine.

## Proposed correction, not yet implemented

`proposed-negative-fin-fix.patch` removes the hourly routine's negative-FIN
recalculation. The complete signed balance has already incorporated rainfall,
interception, melt, irrigation and routed runoff. Retain it for the existing signed
hourly allocator. Preserve all inventory checks, finite-value checks and stop
conditions; do not clip a deficit or create replacement water.

This patch is a reviewable proposal against the pinned source, not a tested fix.
Its sufficiency remains unproven. The daily `watbal.for` contains an analogous
recalculation but different handling of negative infiltration, which needs a shared
failure-class assessment before any release. The numerical routines are shared
outside Roads; regression scope must include non-Roads hillslopes and watersheds.
The existing `20261021_watershed_physical_water_repair` package and 261026 sidecar
already leave signed soil/routing exchange open. This proposed local-input repair
must not be represented as closing that broader scientific boundary.

## Required investigation if the scope changes

1. Export the pinned source into disposable build roots, without changing either
   repository branch or the original binary. Build control and patched candidates
   with explicit compiler/library provenance and distinct identities.
2. Establish control parity, then execute the exact reproducer. Check generated
   water and sediment artifacts, not just process completion. Preserve all failures.
3. Cover signed balances with positive local rainfall, interception, snowmelt,
   irrigation and routed/lateral water. Retain a truly overdrawn case that must fail.
   Assess the daily and hourly consumers explicitly; no silent fallback behavior.
4. Re-run the declared Roads screen and native regression/watchlist/smoke gates,
   including non-Roads and watershed consumers, before considering vendoring.
5. If a new native identity is accepted, amend the program's binary manifest and
   ADR explicitly before candidate confirmation. Keep 261026 results as controls;
   acceptance thresholds and withheld sampling do not change.

If the pin remains fixed, retain this as an unresolved native limitation. A
parameterization that hides these failures or silently uses another binary does
not meet the agreed goal.
