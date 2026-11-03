# Specialized 9005 and RAP consumer contract

Status: MIPA-03 operator decision accepted on 2026-11-03 UTC; implementation
conformance pending reviewed standalone ancestors and validation.

## Authority and reference

The operator directed: “preserve reference. that is anurag's domain”. Preserve
Anurag Srivastava's specialized numerical rules from model source
`2e5928702edd5526a119216bd6be5997729ec72e` in `wepp-forest-revegetation`.
The committed historical `wepp_reveg_2e59287` matches the installed artifact at
SHA256 `2c79a5ecb392a6ed7f70102ff7b6caac888d0cb9df1ce303c93eb10d447740a0`.
Historical compiler flags are not established by a contemporary sidecar.

This is a bounded port into undeployed Linux 261029, preserving the selected
release's ordinary behavior, PMET mappings, layer/OFE FC/HK ownership, retention
policy, output formats and execution defaults. It does not adopt an entire
divergent branch. An isolated reference growth routine is permitted to preserve
its interacting numerical sequence without changing ordinary GROW. Remove only provably unreachable CO2 and
annual-only branches within the reference perennial-only active-growth gate;
do not import their unrelated management parameters. All new
specialized decisions remain Anurag's scientific domain; no inferred correction,
new clamp, epsilon, fallback or recalibration is authorized.

## Mode and input matrix

| State | Required behavior |
| --- | --- |
| No `cancov.txt`, non-9005 soil | Preserve selected ordinary reader, growth and hydraulic behavior |
| Soil 9005, with or without cover flag | Read extended fields and apply reference 9005 conductivity when `ksatadj==1` |
| Empty `cancov.txt` present, continuous hillslope simulation | Activate reference RAP growth/cover and effective-conductivity bypass; load current hillslope cover |
| Empty `simfire.txt` present with RAP | Select reference transformed-forest rule; absence selects observed rule |
| RAP flag absent | Do not consume optional cover/fire files or change ordinary growth |
| Missing fire date with RAP | Initialize fire year/day to zero as in a fresh historical executable; no exact-year burn event; retain reference canopy comparisons |
| Populated fire date | Read normalized Gregorian month/day/four-digit year, preserving actual saved date interpretation |
| Malformed/missing activated cover, mismatched calendar/OFE/row counts, nonfinite numeric input | Explicit input failure with visible diagnostics; no successful completion claim or silent truncation/fallback |
| Single-event execution with RAP requested | Explicit unsupported-mode error; reference protocol and acceptance cover continuous daily/hourly execution |
| Watershed routing of paired hillslope passes | Preserve selected routing behavior and formats; cover is consumed when simulating hillslopes, not reapplied to routed passes/channels |

Both final binary roles must support their existing hillslope simulation paths;
match watershed/hill outputs and passes. Do not inherit hardcoded 20-OFE/50-year
reference storage limits. Allocate cover for the current hillslope and requested
calendar within existing compiled OFE bounds; no global capacity change. Processing
a new hillslope reloads its own cover, without borrowing another hill's state.
Derive the cover basename from the current soil basename, not digits in parent
paths. Current generated `p<ID>.sol` maps to run-directory `p<ID>.cov`.

## Soil 9005 records and dynamics

Preserve producer order: `ksatadj`, quoted land use, burn code, quoted texture
label, texture enum, `uksat`, `lkeff`. Bind every field to its OFE. Texture enum
has no new physics consumer. Conductivities are mm/hour on input. Each OFE has
its ordinary soil header, declared horizon rows (including existing appended
Rosetta values), and exactly one `slflag ui_bdrkth kslast` restrictive record.
Preserve existing depth, density, retention, hydraulic sentinel and layer-remap
behavior. Do not silently reinterpret unset -9999 values as new defaults.

Retain the preceding existing `avsat >= avpor*avcpm` adjustment to .99 of
that product; the additional factor below then yields .9801 at that boundary.
For 9005 with adjustment enabled, preserve the reference sequence:
`ks=avks`, `sat_frac=avsat/(avpor*avcpm)*.99`, `scl=.3` for forest codes
300–399 and `.1` otherwise, `scu=1`, `grndcover=max(rescov,.3)`.
Interpolate `kfs` between base `avks*3.6e6` and `uksat`, and `kus` between
`lkeff` and `uksat`, using the reference expressions and evaluation order:

    kfs = uksat - (uksat-avks*3.6e6)/(1-scl)
          + (uksat-avks*3.6e6)/(1-scl)*grndcover
    kus = uksat - (uksat-lkeff)/(1-scl)
          + (uksat-lkeff)/(1-scl)*grndcover
    psi = (log(1500)-log(33))/(log(avthetafc)-log(avthetadr))
    lambda = 1/psi
    keff = max(kfs*sat_frac**(2*lambda+3),kus)

Store `ks=keff/3.6e6` and feed that conductivity to layers 1/2 as in the
reference. Preserve the source's parenthesization, not a new algebraically
rearranged implementation. When RAP is active bypass the reference's generic
crust/effective-K adjustment block, taking `ks=avks`; do not remove the selected
ordinary frozen/saturated limit in RAP-off non-9005 paths. Non-9005 adjustment
formulas remain selected-release behavior even with RAP, apart from the explicitly
RAP-activated bypass. No new FC/HK refresh schedule accompanies this feedback.

## RAP records, dates and producer reconciliation

A `.cov` contains one row of calendar years and six rows per OFE in numeric order:
TREE, SHRUB, PERENNIAL, ANNUAL, LITTER, BARE. Values are percentages. The first
four bands sum into total vegetation; dynamic consumers divide by 100 exactly
as in the reference. Correct the reference's reversed last-two-row bindings;
neither field gains a dynamic consumer. Require exact consecutive simulation
calendar labels and exactly the current OFE blocks, including OFEs 2 before 10.
Reject duplicate, missing, reordered or extra labels/records rather than silently
accepting the reference's ignored header. Finite values are retained without
invented sum-to-100 normalization or caps; reference numerical domain failures
remain explicit failures, not valid histories.

Producer transformations retain existing fire-year anchoring, pre-fire values,
curve indexing/final-value extension and single-OFE previous-year-or-zero fallback.
Resolve both integer and hydrated string year keys consistently; do not change
fallback selection. Validate complete climate/RAP year equality, not only extrema.
Normalize executable fire dates using the producer's established accepted formats
and two-digit-year mapping, without mutating saved user text. Invalid dates fail.
Clearing the transform/date must remove stale `simfire.txt`/`firedate.txt` activation
from the executable deck; leaving 9005 clears its specialized presence flags.
Retain superseded flag/date bytes in visible run-directory attempt records,
included by existing project browse/archive/restore. No hidden archive exclusion,
new route, queue or permission boundary is introduced. Failed preparation is not
a ready deck; rerun normal preparation after correcting durable inputs.

## Reference vegetation and fire semantics

Preserve reference heat-unit gates, January reset, canopy increment constants
(.50/.80 and .15/.25), stress scaling, biomass inversion, canopy-height scaling,
LAI/root behavior and initialization/management resets in the RAP lane. Preserve
all interacting reference GROW arithmetic in that lane, including its crop-wide
`rdmax` mutation and potentially order-dependent specialized root behavior.
This is an explicit specialized compatibility exception to generic identity
expectations, not permission to undo FC/HK ownership or change ordinary roots.

Keep `year>=fireyr AND sdate>=firejulday`: later years re-enter the pre-fire
canopy branch before the anniversary. For transformed moderate/high forest,
compare canopy to shrub+perennial+annual but assign TREE. Shrub/perennial
comparison and assignment use their different reference quantities unchanged.
These operations can increase canopy; do not replace them with inferred caps.
Keep clamp/log ordering, including potential log(0) failure at canopy 1; do not
move the .999 clamp or add a numeric floor. Failed domains are disclosed and
excluded from successful-history claims rather than silently repaired.

On the exact fire year/day, preserve reference residue multipliers .75/.25/.05
for low/moderate/high forest/shrub/perennial classes, regardless of transformed
mode. Preserve specialized LAI behavior at initialization and cutting and
`ccmxfr` resets at initialization, planting, growth stop and inactive growth.
Unused accumulated rainfall/runoff diagnostics need not be ported: they have no
active state/output consumer. Do not import unrelated reference management,
cutting/removal, queue or output changes.

## Acceptance, scope and rollback

Require actual compiled reader and dynamic-consumer evidence for distinct OFEs,
unequal layers, one/multiple OFEs including 2/10, calendar and fire transitions,
observed/transformed modes, daily/hourly consumers and malformed/absent states.
Compare candidate specialized consumers directly against bound reference source
on identical state; inherited reference quirks are expected compatibility results.
Reference historical whole-model outputs are context, not an oracle for unrelated
selected-release repairs. Observe off/on exact ordinary-output neutrality;
quantify runoff, ET, drainage, storage and vegetation consequences separately
from outlet fluxes or full conservation claims. Prove unchanged ordinary controls.

Complete canonical preparation on supported disposable forks under normal service
identity/mounts/configuration, read consumed state and fresh interchange/reports,
then run mandatory native and WEPPpy gates on exact final artifacts. Preserve
revision-6 binaries/sidecars/reports before revision 7; retain failed attempts and
independent contract, correctness, QA, security and publication reviews. No
production deployment, executable default switch, Windows release, uploaded-input
version expansion, installed Rust replacement or bulk regeneration is authorized.

## Parser and publication boundary details

Each cover header/band is one physical whitespace-delimited record with exactly
the expected numeric token count. Reject list-directed nulls, slash termination,
repeat notation, partial numbers and cross-record continuation. A numeric token
has at most 128 characters (a lexical bound, not a scientific-value clamp).
Check dimension products and record-buffer/calendar arithmetic for integer overflow;
check allocation status and fail explicitly without reducing the requested model.
Reject extra records and nonfinite values before dynamic consumption.

Specialized producer destinations must be regular files or absent; reject symlinks
and other file types. Never truncate a hardlinked destination. Changed/cleared
existing flags or dates move by rename into a fresh visible
`wepp/runs/revegetation-input-<unique>/` directory under their original basenames.
Write replacements to visible exclusive temporary files and atomically replace
only the requested destination. Unchanged bytes are a no-op; absent optional
clears are a no-op. Failed attempts and retired files remain visible and included
in existing archive/restore; do not remove their only useful copy after failure.
No history path may traverse a symlink. A publication error fails preparation;
file existence alone cannot mark the deck ready.
