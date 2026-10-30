# Roads buffer drainage and storage experiment

Status: complete; no production candidate accepted. Design staged 2026-10-30 01:01 UTC (2026-10-29 Pacific).
Authorized by the operator to execute the recommended follow-up experiment.

Diagnose the high sediment exports of generated-soil Roads profiles using the exact
`wepp_261026`, without changing production parameters. Four frozen cases: site sand
unrutted gravel/high, site clay unrutted paved/high, Birmingham clay unrutted paved/low,
and Denver loam rutted gravel/low. Road and fill inputs remain identical to the
preceding all-on hydraulic endpoints.

Run a 2 × 3 factorial for each case (24 native runs): buffer restrictive-layer
conductivity current versus source-based; buffer final input depth minus 1 mm,
unchanged, or plus 1 mm. Preserve every material property, every other horizon
boundary, erosion coefficients, initial saturation, management, climate and geometry.
The ±1 mm perturbation probes the native 200 mm discretization threshold; it is not
a proposed physical soil-depth correction. Both depth and conductivity endpoints
are declared before any new native results are inspected.

For sand use 0.42 um/s × 3.6 = 1.512 mm/h; clay 0.91 × 3.6 = 3.276 mm/h,
from the frozen source provenance, versus the current 0.00151/0.00328 mm/h.
Loam has no detected restrictive layer; its alternative uses the deepest emitted
horizon Ksat, versus the current 0.01 mm/h proxy. This is a distinct no-throttle
counterfactual, not a measured bedrock value or a recommended new default.

Native source `input.for:564–572` adds 200 mm to the last cumulative depth;
lines 698–728 select whole 200 mm computational layers. Bottom depths 399/400/401
therefore predict 400/600/600 mm computational profiles. For loam,
1599/1600/1601 predicts 1600/1800/1800 mm. Verify these in actual WAT outputs.

Compatibility: additive experimental records only, fresh scratch root, frozen
source hashes and native binary. Existing studies and source projects are immutable.
Security impact: none; no dedicated security review required. Complexity budget:
reuse owned soil utilities, native runner, Rust readers and prior audited accounting;
no new dependency, native rebuild, production writer changes or deployment.
A future production parameter change requires its own ADR and broader validation.

See [plan](prompts/completed/study_execplan.md) and [tracker](tracker.md).

## Results

See the [report](report.md): 24 completed runs. Source-based buffer drainage
reduces the selected sand/clay exports to 47.33/450.97 kg/year, both inside
factor ten. Every sediment budget reconciles; upstream model coupling is retained
explicitly. No production parameter or physical candidate acceptance.

Closed 2026-10-30 01:29 UTC. Repository coverage: 12,168 passed, 298 skipped;
documentation, stub completeness and whitespace checks pass.
