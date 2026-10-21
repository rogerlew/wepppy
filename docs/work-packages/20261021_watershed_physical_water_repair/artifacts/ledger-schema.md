# Independent accounting ledger

## Keys and provenance

Every row has executable SHA256, source lane, case, mode, Gregorian year/day,
element/OFE and timestep where relevant. Duplicate/missing dates, nonfinite data
or absent observations fail validation. Unknown terms remain null/unobserved;
never replace an unknown initial store by zero. Preserve the configured period
and check the actual final date/count independently of success markers.

## Physical quantities and conventions

| Boundary | Units and normalization | Independent observations |
| --- | --- | --- |
| OFE | WAT depths in mm; local area m² | QOFE times local area, Q times cumulative area, upstream surface/lateral volume; ET=Ep+Es+Er and Dp use local area |
| Hourly allocation | Native depths m, one OFE/hour | Requested signed input, layer stores before/after and unallocated remainder; frozen water is separate |
| Groundwater | Native m³ per hillslope | Initial depth/1000 times total area; local Dp recharge; baseflow/deep seepage; pre-withdrawal state and post-withdrawal endpoint distinguished |
| PASS | Selected daily volumes m³ | Fresh ASCII v3 fields; event-selection omissions separate from transfer errors |
| Channel sources | Native m³/day and m³/s arrays | Upstream and lateral source arrays, local rainfall excess, net transmission, all index-zero values |
| Channel solver | Spatial node discharge, coefficients, timestep, geometry | Solver-specific temporal quadrature and independent geometric/discrete storage; no inferred balancing store |
| Published output | m³/day | Fresh channel/EBE volume compared with routed discharge integral and observed storage |

Dp is internal recharge in the combined soil plus groundwater domain. Terminal
surface/lateral exports are counted once. Channel lateral rate is per length
only after WSHCHR divides it; multiply the observed rate by channel length.
Rectangular positive-index source sums and trapezoidal solver sums are retained
separately. MC uses trapezoidal upstream forcing and point-mode lateral forcing;
cell-mode lateral forcing uses interval means. Index zero is a state boundary.

## Bounds and reporting

Native binary32 local arithmetic controls use relative 2e-6 unless an exact
zero/state-preservation assertion is possible. Whole-domain closure is not
accepted using that local bound without propagation of all operations and
printed-field precision. WAT E15.7 has seven significant digits, PASS E11.5 five;
fixed lateral WAT fields resolve 0.01 mm. Report signed sum, absolute sum,
maximum absolute daily residual and cumulative residual. Cancellation is not
closure. Outflow-minus-publication and geometric-balance residuals are separate.

## Current observation limitations

The full-node portable MC probe now observes beginning/end node arrays and
fixed daily coefficients; it independently inverts rectangular Manning geometry.
Its frozen-grid/positive-coefficient lane separates geometry from algebraic
storage without a remapping or negative-clipping confounder. The large-run
channel probe observes incoming/outgoing temporal arrays and reported
endpoint storage but not all spatial states/coefficient changes. Those observations
can disprove closure, not establish independent physical storage closure. Initial
soil/interception/snow inventories remain incomplete in the predecessor readers.
A full-domain passing claim is prohibited until those terms are observed. The
current lane analysis is deliberately a boundary diagnosis, not M3 acceptance.
