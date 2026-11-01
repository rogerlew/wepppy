# Initialized capacity explains the selected storage contrasts

B1/B2/B3's lower generated available storage primarily reflects lower initialized
structural UL, including both pore volume and the dry-water offset. Saved liquid
differences are much smaller; all 556 selected consumed ice operands are zero.
The opposite-direction underprediction controls combine higher structural UL
with less occupied storage. This explains the **storage arithmetic**, not the
storage-only cause or annual share of the sediment discrepancies.

## Scope and validation

The study retains all nine frozen legacy/generated pairs and both roughness
modes from the accepted 36 complete 16-year histories. Generated means the
conditioned U12 `erosion_road_cap` lane, not raw generated soil: matched road
erosion coefficients, disabled dynamic road conductivity adjustment and
reference-capped road conductivity in the upper 200 mm remain unchanged.

Existing traces exactly reproduce 152 native float32 storage calculations from
556 consumed layer rows. The reader preserves all 216 selected day/OFE groups,
including 64 with no GRNA call. Independent implementation and scientific
readers reproduce the arithmetic and execution ordering separately.

A necessary initialization-producer gap justified a predeclared, independently
reviewed observation-only probe. All 36 fresh original-period replays retain
**252 ordinary output files and 72 existing observation traces byte-for-byte**.
All 586 computational layers pass assigned capacity, air/rock, dry-water and
minimum-conductivity readback. All 152 connected minimum-conductivity values
reconstruct exactly from the initialized per-OFE minima. Accepted original
inventories, hashes, sizes and modification times remain unchanged. Exact
parity preserves the accepted modes' prior physical and strict-particle results;
it does not add a claim of complete physical water closure.

## All nine target-event contrasts

Values below are generated minus legacy, in mm over the connected equivalent
plane, with roughness persistence on. Positive dry-water offset consumes more
structural capacity; the liquid column is already signed as a contribution to
available storage. Native float32 checks are exact; displayed explanatory
components use double precision and retain rounding residuals in the tables.
All target calls use the same three contributing OFEs within each paired case.

| Case | Pore-depth difference | Dry-offset difference | UL difference | Liquid contribution | Available-storage difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| B1 | -11.908 | +14.475 | -26.383 | +2.645 | -23.738 |
| B2 | -25.570 | +7.328 | -32.898 | -0.164 | -33.062 |
| B3 | -25.570 | +7.328 | -32.898 | +0.220 | -32.677 |
| B4 | -21.766 | +14.497 | -36.263 | +20.635 | -15.628 |
| B5 | +24.900 | +8.948 | +15.952 | +25.011 | +40.963 |
| B6 | +32.103 | +8.275 | +23.828 | +9.101 | +32.929 |
| B7 | -11.908 | +14.475 | -26.383 | +6.722 | -19.661 |
| B8 | -6.995 | +15.127 | -22.122 | +20.340 | -1.782 |
| B9 | +40.812 | +11.120 | +29.692 | +4.908 | +34.600 |

B1/B2/B3 generated available storage is 66.067/39.658/50.779 mm versus legacy
89.806/72.720/83.456 mm. Both less pore volume and greater corrected dry offset
matter; this is not a porosity-only explanation. B4 and B7 retain passing annual
magnitude status despite storage differences in the same direction. B5/B6/B9
underprediction controls show the opposite available-storage direction. No
uniform parameter correction follows.

B8's large structural difference is largely offset by less saved liquid;
available storage is only 2.681 versus 4.463 mm. Its large annual sediment
response to roughness persistence cannot be assigned to storage from this event.
Across all nine cases, target-entry storage is nearly unchanged between roughness
modes, despite annual sediment differences. [Both-mode numeric contrasts](target-contrasts.csv)
and [hydraulic context](hydraulic-context.csv) preserve these distinctions.

## Structural semantics and clocks

The actual first two computational layers are each 100 mm in this panel. This
observed fact does not equate input horizons, the normalized 200 mm boundary
and computational layers generally. Minimum conductivity considers the full
computational profile, including deeper layers.

UL subtracts corrected dry-water depth from air-corrected pore depth. Rock
correction acts through native fine-earth volume and retention preparation;
applying it again to UL would change the native definition. Initialization
observations retain each stage rather than treating final dry water as a raw
input times one factor. Twelve layer observations exercise a dry-water floor;
214 exercise the moisture cap without changing dry water; 360 need neither.
No frozen-conductivity substitution executes in these initialization records.

SCON assigns UL, then initialization hourly water balance assigns it again.
Their observed values and operands match. All 432 selected first-two-layer UL
values match that initialized capacity. Substituting current-day porosity
changes 176 reconstructions: later porosity evolution is not a new UL assignment.

GRNA saves local liquid at entry. All 252 selected upstream consumed-layer rows
reuse that earlier snapshot after their owning OFE's hour-24 water balance;
184 differ from the intervening end-of-day liquid. Live UL and adjusted ice
happen to remain equal to earlier local values in these windows. This establishes
sequential state ownership, not a simultaneous hillslope snapshot or a defect.
See the [producer/consumer map](ownership.md) and [gap dispositions](evidence-gaps.md).

Final routing duration/length, local versus upstream hourly depths, equivalent
conductivity, initialized minimum conductivity, forcing and incoming water have
separate support. The context table preserves their labels; final routing length
must not replace GRNA's entry effective length. Neither net sediment exchange nor
receiving-duration mass identifies tagged origins or gross erosion/deposition.

## Scientific decision

No new native defect is demonstrated. Review the physical meaning of initialized
pore/dry-water capacity, its bulk versus fine-earth volume basis and its relation
to evolving porosity and water accounting before deciding whether any behavioral
ablation is warranted. Do not silently refresh UL, change layer depths or fit
roughness, porosity or conductivity from these contrasts.

Roughness persistence remains an insufficient remedy, and no parameter is
promoted. The full-matrix baseline remains 713/766 meaningful and 31/74 small
passes. Original reference envelopes, separate development/withheld gates and
human UI specification/layout approval remain unchanged. Withheld materials,
production defaults, release binaries and UI implementation are untouched.
The Roads program remains active. [Reproduction instructions](reproduce.md)
describe the source-free analysis and private evidence boundary.
