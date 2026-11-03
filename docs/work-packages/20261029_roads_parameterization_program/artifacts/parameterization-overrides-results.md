# Roads parameter override characterization results

Date: 2026-11-03. **18 declared profiles completed; zero strict EVENT particle flags.**
Independent raw-output review **passed** for all 18 profiles. No production wiring or
scientific defaults changed. These studies characterize explicit inputs, not field
calibration or recommended intervals.

## Design and evidence

Two production-template contexts use the same median fixture, gravel/loam/low
traffic and 16-year climate: road-only bare ditch; road/fill/buffer rutted. Each
has baseline plus half/double road AVKE, Ki, Kr and critical shear. Canonical
builder output is preserved before a study-only numeric-header edit. Fill/buffer
parameters, geometry, management and climate are invariant in each paired contrast.
Only `p1.sol` differs. Actual installed r7 binary/source identities are bound in
the declaration and native source receipt.

Baseline road inputs: AVKE 8.1 mm/h; Ki 500,000 kg s/m4; Kr 0.000075 s/m;
critical shear 2 Pa. Thus tested values are AVKE 4.05/8.1/16.2,
Ki 250,000/500,000/1,000,000, Kr 0.0000375/0.000075/0.00015, and
critical shear 1/2/4. All are strictly positive. Native nonpositive sentinels are
not tested or endorsed as zero-effect controls.

## Annual responses

Runoff is native PASS volume; sediment is PASS EVENT particle export. Terminal
ELEMENT sediment is retained separately, including different non-EVENT support.
Values below are annual means over 16 years.

| Road override | Road-only runoff m3/yr | Road-only sediment kg/yr | Road/fill/buffer runoff m3/yr | Road/fill/buffer sediment kg/yr |
| --- | ---: | ---: | ---: | ---: |
| baseline | 2.921936 | 6.913739 | 61.228691 | 4.767988 |
| avke half | 5.700965 | 10.358004 | 62.607121 | 6.309964 |
| avke double | 1.759198 | 4.317757 | 60.606469 | 3.866828 |
| ki half | 2.921936 | 3.888621 | 61.228691 | 2.655396 |
| ki double | 2.921936 | 12.963947 | 61.228691 | 8.775481 |
| kr half | 2.921936 | 6.482857 | 61.228691 | 4.578873 |
| kr double | 2.921936 | 7.775251 | 61.228691 | 5.146113 |
| shcrit half | 2.921936 | 7.951676 | 61.228691 | 5.166280 |
| shcrit double | 2.921936 | 6.681453 | 61.228691 | 4.693605 |

Conductivity produced both higher and lower runoff and sediment. Ki and Kr
produced both higher and lower sediment with identical runoff; critical shear
changed sediment in the opposite direction, also without changing runoff.
Downstream delivery attenuated the response, especially runoff. These are useful
road controls; they do not establish universal monotonicity, proportional output
scaling, or fill/buffer response bounds.

## Native baseline versus event-adjusted values

The 98.4 soil reader consumes AVKE and converts mm/h to m/s. `tilage.for` uses
positive AVKE for primary/secondary tillage-layer conductivity. Native output
confirms baseline Keff 8.1 versus 4.05/16.2 in the conductivity contrasts.
Runtime erosion coefficients are adjusted after reading baseline inputs. For
example, a baseline first-event Tcrit is 4 Pa despite input critical shear 2 Pa.
The retained `runtime-coefficient-readback.json` gives per-role min/max event
values and baseline inputs. `sedout.for:510–512` reports Ki divided by 1,000,000
and Kr multiplied by 1,000; the readback restores matching physical units.
The user view must distinguish baseline inputs from runtime-adjusted diagnostics.

## Validation and limitations

All 18 calls completed with current hourly-water, groundwater and PMET markers.
All calendars and strict EVENT particle checks pass. Checks cover finite
nonnegative raw WAT/sediment fields, complete per-role WAT calendars, emitted
native OFE areas, and existing printed LOSS/ELEMENT and EBE/ELEMENT bounds.
This narrower physical readback does **not** certify full water-storage closure
or repeat the earlier cross-role water-transfer audit. No tolerances were widened.

Only road-role overrides were varied; fill/buffer coefficients remained fixed.
This is one climate, one texture/surface/traffic combination and two geometries.
No new scientific defaults, withheld-material use, real-project mutation, browser
workflow certification or generated-soil adoption is implied.

## Retained preexecution corrections

No native execution failed. Before the first call, the script/declaration evolved
additively: v2 bound native reader/source identities; v3 corrected inherited
three-OFE/historical-calendar assumptions; v4 repaired fresh-root declaration
reproduction; v5 preserved the inherited nonempty EBE predicate. Original
declarations and source snapshots remain in the raw root. An early v2 approval
was revoked before execution; the actual execution approval binds v5. All18
scientific input capsules stayed byte-identical across those binding revisions.

The private particle reader instance changes only the terminal-OFE selector to
the actual declared profile membership, preserving its numerical predicates.
The generic calendar and readback adapter does not modify frozen audit sources.

## Reproduction and artifacts

Raw root: `/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-overrides-v1`.
Use `parameterization_overrides.py declare --root <new-exclusive-root>` through
`wctl run-python`; retain an independent `execution-review-v5.json` binding the
new declaration before `run --root <root>`, then `analyze --root <root>`.
The release source checkout must be available at its declared path.
For this completed study, the supplemental runtime readback uses the recorded root.

- [Protocol](parameterization-overrides-protocol.md)
- [Machine-readable results and receipt hashes](parameterization-overrides-results.json)
- [Study script](parameterization_overrides.py)
- [Runtime coefficient readback](parameterization_overrides_readback.py)
- [Independent review](parameterization-overrides-science-review.md)
