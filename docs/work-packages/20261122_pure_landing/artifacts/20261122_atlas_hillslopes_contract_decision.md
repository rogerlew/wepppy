# Size Atlas markers by hillslope count

Starting revision `16234b319`. The operator explicitly corrected the
Atlas marker encoding. Marker size represents the number of hillslopes
in the run. The [landing contract](../../../ui-docs/contracts/pure-landing-contract.md#run-atlas)
records this requirement. Use the existing public `hillslopes` field.
Scale marker radius with its square root to encode counts as area and retain
bounded display size and a minimum size for missing or zero values.
Update the key and tooltip. Access count remains optional tooltip data.

The correction is limited to map presentation and the existing public
snapshot fields. No parameterization, model output, data publication,
authorization, plot provider or cutover changes are authorized. Verify
the browser layer's actual marker accessor with contrasting counts and
with missing, zero and supported legacy string counters.

## Independent reviews

Two independent read-only reviews found no high or medium issues.
Check uncapped counts with inverted access rankings, the upper limit,
and equal minimum marker size for zero and missing counts. Distinguish
zero from unknown in the tooltip and retain normalized legacy strings.
