# MIPA-03 specialized consumer reference discovery

Status: read-only source discovery and compiled actual-reader baseline; no
production edits or new scientific policy. Recorded 2026-11-03 UTC.

## Provenance

Selected release checkout `/home/workdir/wepp-forest-release-20261009` is on
`wepp_260430_negmeltfix_comparator`, matching `origin/HEAD`, at
`4f0728984`. It has no 9005 or RAP/fire consumers. Its existing PMET and
FC/HK corrections are separate and must survive the port.

The capable historical reference is **another repository**:
`/home/workdir/wepp-forest-revegetation`, remote
`https://github.com/wepp-in-the-woods/wepp-forest-revegetation`, clean `main`
at `6139c922b86c9ea3a2e068b1841fdc4f960d3184`. No local AGENTS file exists there.
That commit adds `release/wepp_reveg_2e59287`; the model-source ancestor is
`2e5928702edd5526a119216bd6be5997729ec72e`. The only `src/` difference from
that ancestor to HEAD is an added Windows makefile, not model source.

The historical release artifact and WEPPpy's
`wepp_runner/bin/wepp_reveg_2e59287` are byte-identical, SHA256:
`2c79a5ecb392a6ed7f70102ff7b6caac888d0cb9df1ce303c93eb10d447740a0`.
This binds the installed artifact to committed reference release evidence;
there is no contemporary build sidecar establishing exact historical compiler
flags. The actual source reader was separately compiled below.

`reveg.cfg` selects this specialized binary. `reveg-mofe.cfg` instead selects
`wepp_260714`, SHA256
`a7e1a5152fe9097c08685eee98853ffd6ab8fe52cb835e239a972d12f6ee6e36`,
introduced in WEPPpy commit `27856bd8a`. The latter has none of the
`cancov.txt`, `simfire.txt`, or `firedate.txt` strings found in the specialized
artifact. The selected native repository's `wepp_260714_agfields` history also
has no specialized reader. The configuration name is not a compatible-engine
proof; do not switch configured defaults as part of this task.

## Observed protocol and consumers

All source line references in this section refer to the specialized reference
checkout, except the explicit producer column. This table describes observed
behavior, not newly ratified intent.

| Input/mode | Producer and units | Reference binding and dynamic use | Limits / discrepancy |
| --- | --- | --- | --- |
| 9005 header | Seven fields: adjustment flag, land use, burn class, texture name, texture enum, upper K, lower effective K; conductivity in mm/h | `src/input.for:534` binds per-OFE `stexclass`, `uksat`, `lkeff` after first four fields | Selected release consumes only five fields; enum is misbound to lower K |
| 9005 restrictive layer | One restrictive-layer record per OFE | `src/input.for:708` excludes 9005 from the extra generic record read | Selected release lacks exclusion; subsequent OFE alignment can fail |
| 9005 hydraulic response | `uksat`, `lkeff` are per-OFE parameters | `src/infpar.for:634` has a distinct cover-dependent formula; final `ks` and first two `ssc` entries are m/s | Extending the 9003 branch would implement the wrong formula |
| `cancov.txt` | Empty presence flag from either cover writer | `src/main.for:194` activates `cc_run`; `src/contin.for:585` calls `readrap` for continuous simulation | Missing flag preserves ordinary growth; empty flag is valid activation |
| `p*.cov` vegetation rows | Header years then TREE, SHRUB, PERENNIAL, ANNUAL, LITTER, BARE for every numeric-ordered OFE; values percent | `src/readrap.for:104` stores first four bands and sums them to `totcc`; `src/grow.for:639` consumes index `year-ibyear+1` and divides by 100 | Reader discards year labels; six rows per OFE and `numyrs` values consumed positionally |
| `.cov` final two rows | LITTER then BARE | `src/readrap.for:108` reads BARE then LITTER | Confirmed reversal; reference has no dynamic `barec` or `litc` consumers, so correction is state identity rather than a demonstrated flux change |
| Soil texture enum | Per-OFE enum from ordinary/debug 9005 serializers | Read into `stexclass(iplane)` | No further native consumer found; do not invent enum-dependent hydraulics |
| `simfire.txt` | Empty flag only for transformed cover | `src/main.for:210` selects simulated-fire forest cap assignment in `src/grow.for:653` | Ordinary prep does not remove an existing flag; stale transformed state is possible |
| `firedate.txt` | `Wepp._prep_firedate` writes saved month/day/year string verbatim | `src/readrap.for:57` list-reads three integers, computes Gregorian Julian day | Slash/hyphen input is validated by producer splitting but written unchanged; native list-directed syntax is not the same protocol |
| Fire timing | One dated disturbance | `src/grow.for:639,652,675` tests `year>=fireyr AND sdate>=firejulday` | Post-fire branch recurs only after anniversary day in later years; exact legacy behavior vs corrected chronological comparison requires decision |
| Observed forest recovery | Untransformed annual bands | Moderate/high forest: if canopy exceeds shrub+perennial+annual sum, assign that sum | Pre-fire and other forest branches cap at total vegetation sum |
| Simulated forest recovery | Transformed annual bands, producer scales fire-year baseline by curve, keeps pre-fire years, repeats final curve value | Moderate/high forest: compare canopy to shrub+perennial+annual sum, then assign TREE | This can increase canopy and is not a simple upper bound; threshold/assignment mismatch requires explicit disposition |
| Shrub/perennial recovery | Annual band percentages | Compare canopy to SHRUB or PERENNIAL alone, then assign shrub+perennial+annual sum (`src/grow.for:639,675`) | Threshold differs from assignment; potentially raises canopy despite cap-oriented documentation |
| Fire residue effects | Burn class and fire date | `src/decomp.for:1285` on exact fire date multiplies residue masses by .75/.25/.05 for low/moderate/high forest/shrub/perennial | Applies whenever RAP active, regardless of `simfire`; `fireflg` is not used to guard the branch |
| Daily/hourly growth | Existing `PTGRP`→`GROW` call chain | Both daily and hourly balances reach perennial growth; RAP alters canopy, biomass, height and root depth | Hourly reference also accumulates unused post-fire rainfall/runoff diagnostics; not evidence of daily/hourly numerical parity |

## Actual hydraulic formula and growth boundaries

Reference `src/infpar.for:634–693`, under `ksatadj(iplane)==1` and 9005:

- `ks=avks`; `sat_frac=avsat/(avpor*avcpm)*.99`.
- `scl=.3` for forest burn codes 300–399, otherwise `.1`; `scu=1`.
- `grndcover=max(rescov,.3)`.
- `kfs = uksat - (uksat-avks*3.6e6)/(1-scl)
  + (uksat-avks*3.6e6)/(1-scl)*grndcover`.
- `kus = uksat - (uksat-lkeff)/(1-scl)
  + (uksat-lkeff)/(1-scl)*grndcover`.
- `psi=(log(1500)-log(33))/(log(avthetafc)-log(avthetadr))`;
  `lambda=1/psi`; `keff=max(kfs*sat_frac**(2*lambda+3),kus)`.
- `ks=keff/3.6e6`; assign `ssc(1:2,iplane)=ks`.

The 9003 branch instead uses `avks*3.6e6` and clamps to constant `lkeff`.
Reference RAP activation also bypasses generic effective-conductivity adjustments
at `src/infpar.for:388–605`. Neither distinction may be silently omitted.

Growth is more than reading cover caps. `src/grow.for` resets growing degree days
on January 1, evolves canopy through heat-unit and stress equations
(`ccmx1=.50`, `ccmx2=.80`, `frgrw1=.15`, `frgrw2=.25`), applies the class/fire
limits, derives biomass from `log(1-cancov)/(-bb)`, scales height with canopy,
and modifies root depth. `ccmxfr` state is initialized/reset in `initgr`,
`ptgrp`, and `grow`. Reference code caps canopy to 1 **before** the logarithm,
then clamps to .999 later: exactly 1 can cause a logarithm-domain failure.
There are unconditional changes in reference `grow.for` (including commented
ordinary biomass updates); copying the whole file would alter non-RAP modes.

`crap.inc` allocates all bands with hardcoded dimensions `(mxhill,20,50)`.
`hillid.for` extracts every digit from a ten-character soil filename; it is not
a safe current long-path basename protocol. These are reference limitations,
not automatically ratified target restrictions. The selected release needs
capacity-compatible storage and current path handling.

## Compiled actual-reader baseline

Fresh evidence root:
`/wc1/holdouts/mipa-native-r7-20261103/reference-baseline`.
`run.sh` compiles the unchanged reference `src/readrap.for` with a small observer
caller, system `/usr/bin/gfortran`, original includes, `-std=legacy -fcheck=all`.
It does not edit the reference repository. Retained artifacts include
`readrap_probe.for`, `p1.cov`, `firedate.txt`, `readrap_probe`, `output.txt`,
and `sha256.txt`.

The two-OFE/two-year fixture deliberately labels years `2050 1980`. Native
execution succeeds and stores the first and second columns as indices 1 and 2,
proving labels are ignored and no increasing-year validation exists.
For OFE 1, year index 1, producer-order values TREE=11, SHRUB=21,
PERENNIAL=31, ANNUAL=41, LITTER=51, BARE=61 become native
`trcc=11,shcc=21,prcc=31,ancc=41,barec=51,litc=61,totcc=104`.
The second OFE has distinct values and retains its own six-record block.
`firedate.txt` containing `7 15 2020` yields `fireflg=1,fireyr=2020,
firejulday=197`. The harness only observes actual reads; it does not reimplement
the intended native logic. Percent sums above 100 here deliberately discriminate
binding and are not a scientific-validity claim or full growth history.

## Decisions and validation still needed

The parent is asking the operator about the legacy recurring anniversary-day
fire condition and mismatched simulated-forest threshold/assignment. No dependent
implementation is authorized by this discovery record. Also resolve the analogous
shrub/perennial threshold mismatch explicitly, instead of silently repairing it.

Retain selected-release failing reader cases; specify exact accepted year/OFE
sets, date syntax, bounds and optional-state cleanup before edits. Validate
missing fire date explicitly: the reference sets `fireflg=0` but leaves year/day
state without a guarded downstream contract. Compare actual native dynamic
operands and histories for RAP on/off, daily/hourly, transformed/untransformed,
fire boundaries, ordinary modes, and exact final release binaries. This baseline
does not prove release compatibility or establish a new hydraulic interpretation.

## Port boundary inventory: conditional and unguarded divergence

The reference is a divergent physics branch, not a reader-only extension.
Normalized selected-versus-reference diffs are retained in the baseline directory
for `grow`, `ptgrp`, `initgr`, `infpar`, `decomp`, `watbal_hourly`, `main`,
`infile`, `contin`, `ccrpvr3a.inc`, and `cvgpar.inc`.

| Site | Reference change relevant to RAP | Selected-release conflict / required boundary |
| --- | --- | --- |
| `grow:311` | Reset `sumgdd` on January 1 when RAP active | Preserve reset timing only in RAP lane |
| `grow:317–356` | Replaces top-level growth predicate; non-senescing perennials stop at max height | Unguarded branch difference; must decide whether it is intended specialized semantics and scope it explicitly |
| `grow:470–486` | Replaces active-growth gate with perennial-only, pre-senescence predicate | Removes annual heat-unit alternative unconditionally; wholesale copy violates ordinary-mode preservation |
| `grow:497,520–561` | Comments PAR calculation and ordinary biomass updates; skips DDM in RAP mode | Ordinary calculations must remain selected-release behavior; specialized canopy-derived biomass must be isolated |
| `grow:596–710` | Heat-unit canopy increment, class/fire limits, biomass inversion, `rtmass=vdmt*rsr` | Core RAP physics, including all constants and exact threshold/assignment decisions; `log(0)` possibility needs explicit finite-domain contract |
| `grow:729` | `canhgt=hmax*cancov` when RAP active | Direct specialized growth consequence, not just output decoration |
| `grow:763–875` | Senescing perennials alter root-depth logic; cap global crop `rdmax` to current soil thickness; RAP tree roots scale with height and floor .1 m | `rdmax` mutation is by crop type, so one OFE can affect another; conflicts with heterogeneous ownership intent. Do not silently copy or silently invent a repair |
| `grow:909–921,1097–1107` | For `jdsene!=0`, set `lai=xmxlai*cancov` in growth and senescence | Not guarded by RAP; also occurs in reference `initgr:95` and `ptgrp:292` after cutting. A faithful specialized lane must inventory all three |
| `grow:1286` | Reset `ccmxfr` if top-level growth gate not active | Must accompany initialization and management resets |
| `initgr:68`; `ptgrp:745,782` | Reset `ccmxfr` at initial growth, JDSTOP and planting | Shared per-OFE state declared in `ccrpvr3a.inc`; include both sizing variants if applicable |
| `ptgrp:709`, `ptgra:565`, `range:332` | Pass `ihill` to changed GROW signature | All three callers must agree if port chooses signature extension; no reason to copy unrelated management changes |
| `infpar:388–605` | `cc_run==1` bypasses crust/surface-adjusted `eke`, sets `ks=avks` | This is a hydraulic model change under RAP even without 9005; define intended mode matrix explicitly |
| `infpar:569–600` | Comments saturated/frozen layer limiting loop and `ks=eke` even for RAP-off branch | Unconditional reference divergence must not leak into ordinary modes; selected limit remains unless a ratified specialized lane overrides it |
| `infpar:628–632` | Under any `ksatadj==1`, reset `ks=avks`, use `sat_frac=ratio*.99` | Selected uses existing adjusted `ks` and `min(ratio,1)`; exact 9005 reference semantics include this distinction. Applying it to 9001/9003 would alter supported modes |
| `infpar:690–693` | After adjustment, writes `ks` plus `ssc(1:2)` | Selected writes `ks` only. Layer conductivity feedback can affect subsequent averaging, drainage, FC/HK initialization timing and history; selecting one policy requires recorded rationale and dynamic tests |
| `decomp:1285–1359` | Exact-fire-day residue mass reduction for forest, shrub and perennial burn classes | No `simfire` distinction and no `fireflg` guard; date absence must not spuriously activate |
| `watbal_hourly:928–944` | Accumulate rainfall+melt and runoff in mm after fire for `burncode>=302` (the additional `==303` is redundant) | `afrfcum/afruncum` only occur in commented debug output elsewhere; no active model/output consumer. Do not import unrelated hourly changes for these unused diagnostics |

Other unguarded reference growth changes include annual canopy/vegetation
harvest-index handling, CO2 growth additions, and nonnegative senescence clamps.
Reference `ptgrp` also changes cutting/removal, residue operations and management
options unrelated to RAP. Preserve selected behavior outside specifically
ratified specialized transitions.

`stexclass`, `barec`, and `litc` have no active dynamic readers beyond initial
input assignment. They still need correct per-OFE identity, but using them to
change hydraulics or ground cover would introduce new scientific behavior.
`afrfcum` and `afruncum` likewise have no active consumers.

The focused operator decision therefore cannot be represented solely by fixing
two fire predicates. A full port contract must state the chosen 9005 saturation
factor, layer-conductivity feedback, RAP effective-K bypass, canopy/logarithm
bounds, growth/senescence gates, root-depth/LAI specialization, and crop-wide
parameter ownership. Existing reference formulas provide concrete alternatives;
this discovery does not ratify one.
