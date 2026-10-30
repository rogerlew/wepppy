# Development surface screen

Declared before execution in `surface-screen-v3/declaration.json` under the program
scratch root. This is a mechanism screen, not candidate acceptance. It has 576 runs:
three climates (site, Birmingham, Flagstaff), four known development soils, two
insloped ditch designs, two surfaces, two traffic levels (high/none), six treatments.
No withheld material is used. All modern runs use `wepp_261026` with `wepp_ui.txt`;
project-specific snow, PMET and groundwater files remain a later parity requirement.

## Hypotheses and unchanged inputs

- `roles`: generated bare/bare/forest baseline.
- `erosion`: configuration-matched legacy road Ki, Kr and critical shear only.
- `rock`: erosion treatment plus gravel/paved road rock parameter through 200 mm.
- `compact1`, `compact3`, `compact10`: rock treatment plus road Ksat of 1, 3 or
  10 mm/hour through 200 mm, with neutral dynamic conductivity adjustment.

Every treatment preserves fill/buffer properties, lower boundaries, generated
texture, and road horizons below 200 mm. Every source horizon above that boundary
is treated, including profiles with a preexisting boundary shallower than 200 mm.
These brackets are hypotheses, not measured compaction values. Rock fraction is a
soil-model input with hydrologic consequences, not merely a visualization of surface
cover. A favorable sediment ratio alone cannot justify adopting this representation.

FSWEPP2 commit: `c0fe47499406955afc547827cdae8d02ccada432`. Matched WEPP2010 records
are rehashed, and climate, management, slope and run prompt must match exactly.
Legacy soil contents must match exactly after the shared 200 mm normalization.
The old WEPP2010 runs retain their original unnormalized inputs; this distinction
is deliberate and cannot be represented as byte-identical native soil consumption.

## Physical context and limitations

The original [WEPP:Road technical documentation](https://forest.moscowfsl.wsu.edu/fswepp/docs/wepproaddoc.html)
distinguishes ditch critical shear and road flow paths. Thus restoring configuration
semantics is necessary before evaluating a generated-soil model. It also recommends
longer climate sequences than this 16-year screening panel, especially for dry sites.
Final model assessment should include duration sensitivity rather than treating
screening means as stable long-term climatology.

[Elliot, Lewis and Cannard (2023)](https://research.fs.usda.gov/treesearch/67273)
report calibrated conductivities of 3.0 and 1.3 mm/hour for two high-traffic gravel
road designs, with strongly different erodibilities. This supports exploring
road-specific hydraulics and erosion jointly. It does **not** establish direct
equivalence between their effective conductivity and modern horizon Ksat, nor justify
transferring a single site's calibration to every climate or soil. The present
1/3/10 brackets were declared before retrieving this paper; it supplies context,
not retrospective selection of a favored result.

## Retained preflight failures

- `surface-screen-v1`: byte comparison exposed the historical reference's missing
  200 mm split in fill/buffer. Require exact equality after only the canonical
  normalization; do not permit an unrestricted semantic comparison.
- `surface-screen-v2`: readback equality exposed string-valued 9002 conductivity
  metadata versus numeric values in the treatment object. Use the parser's native
  string representation; retain strict emitted-value equality.
- `surface-screen-v3`: 128 completed native runs retained; native execution stopped
  on paved/loam/site `compact3` cases with `HOURLY_WATER_UNMET`. Both high and no
  traffic failed. The process terminated (exit 1), verified before recovery.
- `surface-screen-v4`: same declared treatments/panel, explicit native-failure
  records so rejection does not stop the remaining screen. Completed v3 cases may
  be reused only after matching case, all consumed input hashes, parsed treatment
  and all native output hashes. Reused records are linked by SHA256. Failed cases
  remain failures; they cannot disappear from the denominator or pass a model gate.

Seven scope tests cover unchanged generated material, deeper horizons, other roles,
nonmutation and missing-boundary rejection. Together with existing runtime and
negative-flux tests, the focused suite passes 14 tests. Native audits additionally
check the mode banner, complete finite calendar, hashes, soil readback, signed
sediment budgets, EBE consistency and buffer water routing.
