# Storage operands and execution ownership

The native source base is the complete accepted response `attempt-u2/build/src`
tree, bound through the diagnostic binary reuse chain. The small intervention
`source/` directory is not the compiled-source inventory. Native sources and
patches remain private; the descriptions here are original analysis.

## Producer and consumer map

| Quantity | Producer | Consumer and clock | Evidence |
| --- | --- | --- | --- |
| Structural UL, m | SCON initialization; then initialization WATBAL or WATBAL_HOURLY | Local and upstream GRNA; live array value at that call | Initialization assignment observations plus selected consumed operands |
| Saved liquid STOLD, m | GRNA entry copies the owning OFE's ST, first two computational layers | Local call immediately; downstream calls later reuse the saved upstream values | Ordered local/upstream consumed-layer traces |
| Live liquid ST, m | SCON initialization and subsequent water-balance/freeze processes | Sampled at each local GRNA entry; advanced upstream state is not substituted into STOLD | Local snapshots and intervening hourly water-balance observations |
| Adjusted frozen water FRZW, m | INIDAT initialization and FRWATC freeze/thaw accounting | Live array at each GRNA call, including upstream contributors | All 556 selected consumed operands are zero; no annual ice claim |
| Layer thickness DG, m | Native computational-layer construction | UL assignment and GRNA first-two-layer storage | Assigned initialization and consumed depths; each selected first layer and second layer is 100 mm in this panel |
| Corrected porosity POR, fraction | SCON initialization with entrapped-air correction; later SOIL can update POR | Initialization UL calculation; current POR does not automatically replace that earlier UL operand | Initial and selected-day porosity, exact UL reconstruction |
| Corrected dry-water fraction THETDR | Native soil preparation, rock correction and retention bounds | Subtracted in UL; also defines the liquid/ice bookkeeping offset | Staged initialization observations retain pre-rock, post-rock and final values |
| Minimum conductivity SSCMIN, m/s | SCON's ordered selection across all computational layers | GRNA length-weighted percolation coefficient Kagmin | Assigned running minima and consumed connected coefficient |
| Contributing lengths, m | Native geometry and connectivity | Local product followed by upstream products in decreasing OFE order, divided by effective length | Consumed layer lengths, connected-plane observations and exact arithmetic |

Source assignment locations in the accepted base include `grna.for:198`,
`scon.for:518`, `watbal.for:288`, `watbal_hourly.for:290` and the minimum selection
at `scon.for:529`. Initialization order is in `contin.for:491`; phase-zero
porosity observation is emitted inside SOIL before initialization water balance.
Instrumented source line numbers differ; hashes and observation tags identify
the exact probe boundary.

## Capacity and units

UL is the initialized pore-depth term minus the final corrected dry-water
fraction times computational thickness, with native REAL rounding. The pore
term already includes entrapped air. The native fine-earth volume factor CPM
converts the rock mass fraction using density; it affects dry-water preparation
before subsequent retention limits. Multiplying UL by CPM again would not
reproduce the native definition. FRZW is adjusted frozen storage, not raw total
ice mass; liquid ST likewise uses the native dry-water offset.

For each consumed layer, native ice-adjusted capacity is nonnegative. The layer
adds storage only when saved liquid lies below that capacity. Local and upstream
accumulations have different parenthesization, so the reader preserves each
float32 addition/subtraction in source order. Connected capacity weights each
contributor by its local length and divides by the observed effective length.
The explanatory pore/dry/liquid decomposition uses double precision with its
native rounding residual recorded separately; it does not replace exact checks.

Do not confuse SSCMIN/Kagmin with local KS or equivalent-plane AVEKS. The former
uses the initialized full computational profile and length weights; the latter
belongs to different native hydraulic calculations. Forcing duration, final
routing duration and hourly water-balance support also have different meanings.

## Executed timing

All 252 selected upstream consumed-layer rows follow both the owner's earlier
local GRNA snapshot and its completed hour-24 water balance. Their STOLD values
match the earlier local snapshot. In 184 rows they differ from the intervening
hour-24 liquid state. Live upstream UL and FRZW happen to remain equal to their
earlier local values in these windows. This establishes sequential ownership;
it does not establish a common simultaneous hillslope state or a native defect.

All 432 selected first-two-layer UL values reconstruct exactly from initial
porosity and the corrected dry/depth operands. Substituting current porosity
changes 176 of those reconstructions. Daily density/porosity evolution therefore
must not be silently treated as a new UL assignment. The initialization observer
closes the actual writer/overwrite gap; it does not refresh structural state.

The frozen target and adjacent-day selection covers 216 day/OFE groups. Of these,
64 have no GRNA call and remain unavailable. All nine target buffer contrasts
have observed connected storage. No missing call is represented by zero.
