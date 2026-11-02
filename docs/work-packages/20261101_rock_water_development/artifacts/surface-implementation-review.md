# Surface support implementation review

Disposition: **PASS for the reviewed implementation and focused validation.**
No material source or scientific-contract discrepancy remains. Broad regression,
retained artifact publication and final checkpoint verification remain parent-owned
completion gates. This reviewer changed no production code, tests or raw evidence.

## Contract conformance

The implementation follows the reviewed ancestor acfadc938. Both parquet queries
now retain null-cover rows for reporting, while the original numeric selection
comprehensions and their short-circuit order remain intact. Means, clipping,
source priority, overrides and fallback branches are unchanged. Diagnostics are
computed only after the original selected-value parsing succeeds, so consumed
malformed values retain the existing query-failed report without partial support.

The helper separately counts null, numeric nonfinite and excluded unparseable
cover. Finite out-of-range and zero values keep their actual identities. A finite
out-of-range value still participates when the old selection admitted it; neither
its count nor used_rows implies scientifically valid observed cover.

All finite positive area contributes to known_positive_area, including area with
missing or nonfinite cover. Used area is restricted to the original numerical
selection. Unknown/nonpositive area is counted separately, and no area values are
invented. The known-area ratio can equal one while unknown-area rows remain; the
specification and README explicitly prohibit a complete-footprint interpretation.
Without an area column the area diagnostics are null, not zero.

Excluded malformed values are handled without introducing a new failure: null
cover with malformed area, malformed cover with null area, and nonfinite cover
with malformed area. Narrow diagnostic conversion handlers preserve unknown
support while the original aggregation determines any actual parse error.

## Actual-boundary tests and review corrections

Focused-v3 log retains **48 passed**, with two existing dependency deprecation
warnings. New tests create actual DuckDB parquet inputs and invoke the production
loader rather than substituting a mocked proxy. They cover partial/missing support,
zero, nonfinite and out-of-range cover, unweighted input, empty/all-unusable
recognized columns, excluded malformed fields and consumed malformed failures.

Review identified missing declared coverage for NaN/Infinity/negative area and
unweighted empty/all-unusable inputs. Three added cases close those gaps in v3.
The earlier test-only DuckDB COPY destination-parameter failure remains in v1;
quoting the test path corrected it without changing production behavior.

Both RAP and SBS tests create actual GeoTIFF inputs, execute the C production
path, read the resulting manifest's support object and read C raster pixels.
The expected weighted proxy is independently calculated from the declared rows;
C values are checked against the existing equation, and explicit equivalent
manual controls produce exactly identical C arrays. These checks validate
propagation and retained numerical policy, not field accuracy of the proxy.

The parity tests read the auto manifest/pixels before a manual call overwrites
the same output paths. That is adequate for the assertions but not a durable
paired artifact publication. The parent has been advised to retain auto/manual
publication runs in separate destinations and verify their final files before
citing archive evidence. This review does not claim that unpublished paired
artifacts have already been independently checked.

## Limits and bindings

This metadata change does not produce a survey-cover scalar, revise the existing
auto estimate, validate profile-to-surface conversion, or add native rock mechanics.
No native model execution is required to prove an additive RUSLE C manifest field;
actual native surface/capacity questions remain in the separate program streams.

Exact inspected bytes:

- `wepppy/nodb/mods/rusle/c_integration.py`:
  `631ed7aa7663790dfdc1515c508a602ad4672b92e7b0abc25739db5bf3078159`

- `tests/nodb/mods/test_rusle_c_integration.py`:
  `d2cd9e4a323bce3e05ab3dbb5fc2a1c55226e64d3274f2ad05248ebfb9bb39f9`

- `out/rock-water-development-20261101/surface-focused-v3.log`:
  `4df8cb735f72b5966d281101876713737a1e8de252bcdf20fe221f8c4cc0f081`

Reviewer writers are clear after scoped lint.
