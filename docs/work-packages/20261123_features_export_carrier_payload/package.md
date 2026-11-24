# Features Export carrier payload refactor

Consolidate the repeated column and metadata preparation in the 295-line
`_build_key_first_materialized_layer_payload` function. The service builds
a carrier by joining selected source tables on watershed identifiers. Tabular
formats consume a data frame. Spatial formats attach geometry and consume a
serialized feature collection.

The compatibility target is the existing Features Export specification and
the same public service calls, selected columns, units, geometry, row counts,
warnings and manifest metadata. The complexity budget is private service
functions using existing materializers and writers. Security impact is low.
The change concerns data preparation inside the existing run boundary and
requires no dedicated security review.

The maintainer owns local acceptance. Exercise both payload paths, read back
generated outputs and run the full pytest gate. The operator requested a
local master merge and deferred the PR.

## Outcome

Completed locally on 2026-11-24 UTC. The builder shares column preparation
and manifest metadata assembly across both paths. The [tracker](tracker.md)
records generated artifact checks and the outstanding broad-suite failure.
