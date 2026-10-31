# Generated-role hydraulic audit on revision 3

The emitted 200 mm break is present for all 21 development role profiles (96
horizons). The road-cap experiment preserves generated density, organic matter
and water retention while replacing conductivity in the upper 200 mm. This is
an incomplete constructed-surface hypothesis, not evidence that SSURGO or the
shared soil writers are defective.

## Executable evidence

`hydraulic_role_inventory_r3.py` verifies seven raw-source hashes, all emitted
horizons, restrictions and the source dependencies. Native source is pinned to
`6112b68bce0e21a77f510bde5c24af067a47a647` through a retained Git archive.
`hydraulic_init_probe_r3.py` adds stdout observations at SCON completion and
WATBAL initialization only. All 14 complete-period generated/legacy replays
exactly match the released binary's complete raw-output inventory and bytes.
No native checkout or released artifact changed. Observation build setup retries
are retained separately; the successful declaration pins the final driver/build.

For material 2711184, initialized road density/porosity is 0.8 g/cm³ / 0.669
for generated soil and 1.563 g/cm³ / 0.394 for legacy soil. Generated road/fill/
buffer all have approximately 0.669 porosity; the legacy roles separate to
0.394/0.486/0.573. This measures a real state difference, not its causal share
of sediment. The earlier first-day observations are not initialization evidence.

## Source-to-native mapping

Paths below are relative to the frozen native source unless stated otherwise.

| Stage | Verified behavior | Implication |
| --- | --- | --- |
| WEPPpy `builder_bridge.py:roles` | Bare/forest lookup conditioning; blank density override; preparation saturation 0.75 | Preserving density is intended by this experimental adapter, not a failed override. |
| WEPPpy `builder_bridge.py:inject` | Road erosion anchors, `ksatadj=0`, upper-200-mm conductivity cap | Fill retains bare saturation-dependent conductivity; buffer retains forest treatment. |
| `src/input.for`, soil read | 9002 supplies density, conductivity, FC/WP; 98.4 zeroes these for estimation and reads `avke` | Textual values across formats are not interchangeable native states. |
| `src/input.for`, limits/remapping | Positive density clipped to 0.8–2.0 g/cm³; OM capped at 10%; rock capped at 85%; density ×1000, depth /1000, K /3.6e6, percentages /100 | The 0.78 density /11% OM source is consumed as 0.8 /10%, before depth averaging. |
| `src/input.for`, 200-mm remapping | Weighted constituent averages, harmonic K; top-200-mm K assignment; original bottom extended by 200 mm and bounded at 1800 mm | Preserve normalization and distinguish source horizons from native computational layers. |
| `src/tilage.for` | Averages tillage-layer inputs; legacy positive `avke` replaces upper-layer K | Legacy `avke` is an effective-conductivity prior, not the deeper saturated-K profile. |
| `src/scon.for` | Derives missing density; computes porosity from 2650 kg/m³ with entrapped-air adjustment; derives missing FC/WP | Modern explicit retention bypasses legacy estimation. |
| `src/scon.for` | Rock-volume correction multiplies FC/WP; retention is constrained against pore space; initializes water storage | Density, rock, saturation, retention and storage are coupled. A density-only edit is not a complete physical rule. |
| `src/soil.for` | Management/tillage and reconsolidation can modify density and porosity | SCON state, completed initialization and first-day output are distinct observation stages. |
| `src/infpar.for` | Suction depends on texture, porosity, water and rock; `ksatadj=1` reduces effective K by saturation fraction and FC/WP-derived exponent | A shared K input does not imply a shared effective infiltration state. |
| `src/input.for`, `cvgpar.inc` | Appended 9002 VG values are read/averaged; source search finds no downstream consumer in this revision | Recomputing only appended Rosetta values would not change the active FC/WP/K path. |
| `src/winter.for` | Frost call is gated by `ksflag==1` | Read the executable condition, not the broader soil-version comment. Both compared decks use `ksflag=0`. |

Modern restrictions (`slflag`, bedrock thickness, lower K) remain recorded and
unchanged. This audit does not reopen the rejected restriction-flag experiment.
Disturbed already offers an optional density override and optional Rosetta FC/WP
recalculation; its blank lookup density entries do not request compaction.
No general Disturbed or soil-writer change follows from this audit.

## Physical support and limits

Martin et al. measured coupled hydraulic changes on forest skid trails: surface
saturated water content decreased on average by 0.02 m³/m³, and conductivity by
a factor of 2.4. Their results also show substantial site/depth variability and
limitations for severely degraded soils. These support a bounded sensitivity,
not universal road-density targets. [Primary study](https://doi.org/10.1186/s13595-024-01265-4).

Road-specific work distinguishes low-conductivity constructed surfaces from
adjacent forest soils. It supports separate role treatment without establishing
a density-to-conductivity conversion for these seven materials.
[Elliot, Foltz and Luce](https://forest.moscowfsl.wsu.edu/engr/library/Elliot/Elliot1998c/1998c.pdf).

## Declared contrast

`road_pore_screen_r3.py` freezes three incremental road-only lanes on all 96
misses and 20 passing controls: pore/retention, conductivity, and their combination.
The pore lane subtracts 0.02 from raw porosity by adding 0.053 g/cm³ to the native-
clamped source density, and scales FC/WP by the new/old raw pore-volume ratio.
This preserves a normalized retention shape; it is a research assumption, not
measured retention. K is divided by 2.4 from the existing capped candidate.
Appended VG scale values follow the same factors; shape parameters stay fixed.

The 0–200 mm uniform treatment extends a surface observation to the existing
experimental treatment depth. Skid trails are not constructed gravel/paved roads;
those transfer and depth assumptions require scientific review. The experiment
also measures incremental change on an already capped surface, not an independent
estimate of total construction effects. No new fill compaction rule is supported.

Every non-target soil line, all other inputs, restrictions, deeper material and
runtime settings remain byte-identical. No erosion or OM fitting, per-climate
constants, withheld inspection, threshold changes or UI implementation. Reject
standalone promotion on control regression; even a successful selected panel
requires full development, regional-runtime, geometry and withheld validation.
