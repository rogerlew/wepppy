# Engineered-surface findings

## Hydraulic role diagnostic

Thirty cases isolate `ksatadj` by road, fill, buffer, road+fill and all roles on six
known development profiles. Disabling the road adjustment resolves Birmingham/sand
and Flagstaff/sand/clay failures in this diagnostic. Buffer-only changes do not.
Birmingham/clay with the legacy rock-volume treatment still fails under every flag
combination. Site/loam accounting differences remain. See
`hydraulic-role-diagnostic.json`; no generated horizons or boundaries changed.

## Full 384-case screen

Four policies run across the same 96 development configurations with full declared
runtime settings. Road Ki/Kr/critical shear follow the configuration-matched legacy
values; generated material is preserved. The surface cap sets each road horizon
ending at or above 200 mm to `min(source Ksat, reference road avke)` and disables
road forest saturation adjustment. It does not increase source Ksat, alter rock
volume, replace texture or change deeper horizons. Reference effective conductivity
is an explicit engineering prior, not asserted identical to modern horizon Ksat.

| Policy | Magnitude passes / 96 | Native failures | Negative-flux cases | Other accounting cases |
| --- | ---: | ---: | ---: | ---: |
| Disable road adjustment | 80 | 4 | 0 | 5 |
| Disable road+fill adjustment | 79 | 4 | 1 | 5 |
| Road adjustment off + surface cap | 93 | 2 | 0 | 4 |
| Road+fill adjustment off + surface cap | 93 | 2 | 1 | 4 |

`engineered-surface-score.json` verifies declared membership, artifact hashes,
references and unchanged gates. The road-only cap policy meets the screen's
numerical gates but fails physical acceptance. Its sole completed magnitude failure
is site/loam/rocked-ditch/paved/no-traffic: 32.56308 versus 343.98144 kg/year,
ratio 0.0946652. The other two failures are native stops, not zero yields.

Nine new scope tests cover nonmutation, deeper material, other roles, no increase
of conductivity, finite positive caps and the 200 mm treatment boundary. Combined
focused suite: 30 passed. After execution, the driver moved profile loading into
`main()` for hermetic imports and rejects nonfinite caps; the exact originally
executed source remains frozen in the scratch batch. These changes do not alter
any declared finite treatment.

## Accounting explanation without rewriting outputs

All four nonnegative accounting discrepancies in the road-only cap policy were
traced, not a favorable subset. `engineered-accounting.json` contains per-case
observations, unchanged precision bounds and seven-file byte parity. In every case,
positive `ofelod` is excluded from reported `avsole` by the observed zero-`qout`
branch. Subtracting that independently observed definition difference leaves the
annual residual within the original bound, and accounts for the dated EBE mismatch.
Original values and failed strict comparisons remain retained. This is a source-
explained report distinction, not sediment clipping or a global tolerance change.

The road+fill policy's negative flux is a separate physical rejection. A trace of
one such case correctly returns `source_explained=false`; the positive-load export
gate does not excuse negative boundary flux.

## Remaining failure investigations

Eighteen cases apply the earlier source-informed fill, buffer or both lower-boundary
conductivities to six road-cap configurations. They resolve some accounting cases,
but all three variants of the remaining Birmingham/sand/no-traffic case still stop.
Another 18 cases restore current Roads/reference initial saturation on road, fill,
or all roles. The remaining native failure persists. These are retained in
`engineered-boundary-diagnostic.json` and `initial-state-diagnostic.json`.

The remaining bare/rocked-ditch failures share a hydraulic mechanism. Exact pinned
binary tracing proves that the negative-FIN reset drops net local rainfall. See
[native water-accounting decision](native-water-accounting-decision.md) and
`negative-fin-proof.json`. Do not select more soil parameters solely to avoid this
known defect. `candidate-disposition.json` retains the promising candidate as
**rejected pending native resolution**, not accepted or independently validated.

An explicit operator decision has been requested because changing the final native
target conflicts with the requested 261026 pin. The proposed fix, portable reproducer
and non-Roads regression scope are reviewable; no patched binary has been built.
The six withheld materials remain untouched and the user-facing view remains pending.
