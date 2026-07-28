# DOM-04A Review and Disposition

## Scope reviewed

The review covered only Map orchestration: the rendered map host/search actions,
coordinate navigation, TOPAZ/WEPP lookup to report drilldown, and the
run-scoped elevation request. DOM-04B owns layers, scales, legends, remote
resources, and feature presentation.

## Disposition

No production mismatch was found. The template now has an actual-render test
for `#setloc_form`, `#input_centerloc`, all three `data-map-action` values,
`#mapid`, `#drilldown`, and `#mouseelev`. The Map Jest suite now asserts the
exact `url_for_run("elevationquery/")` URL and numeric `{lat, lng}` payload.

Existing tests already prove coordinate parsing, invalid-input protection,
TOPAZ/WEPP lookup, channel/subcatchment drilldown URLs, elevation cooldown,
the elevation microservice response, and subcatchment report rendering. No
route, authorization, persistence, RQ, or generated bundle change occurred.

## Evidence

- Focused Python: 121 passed (`test_pure_controls_render.py`,
  `test_elevationquery.py`, `test_wepp_bp.py`).
- Frontend lint: passed.
- Focused Map Jest: 38 passed.
- Full frontend suite: 88 suites and 662 tests passed.
- Full Python suite: stopped after 2,451 passed and 40 skipped on unrelated
  `test_gridmet_interpolation_propagates_unpublished_suffix_to_parquet_and_prn`;
  `_FakeUnits` lacks `degC` while the GridMET client accesses `units.degC`.

## Review requirement

No independent correctness or dedicated security review was required because
this package changed only tests and documentation. Any future production route
repair must re-triage the public-query boundary before modification.
