# M2 independent code review

## Scope and verdict

Reviewed committed delta `eb6b0d3fb..0e58feced` and the preliminary exact-
image evidence in `20261116_m2_validation.md`. The launcher preserves the
accepted fixed-argv, minimal-environment, process-group drain, provenance and
private-scratch patterns. Direct valid/projected/hostile tests are useful.

**Verdict: CHANGES REQUIRED.** No High finding was identified. Two Medium
correctness/contract findings remain open; M2 must not be closed until both are
fixed and regression-tested.

## Findings

### M2-CR-01 - Medium - Source-bounds readback is tautological

`_loaded_geoparquet_from_payload` passes the parser-declared `source_bounds`
directly into `_loaded_shapefile_from_payload`, then compares the resulting
field to that same parser-declared value
(`wepppy/microservices/shape_converter/convert.py:910-935`). It never computes
bounds from the decoded Shapely geometries. A one-point payload with declared
bounds `[0, 0, 0, 0]` and actual coordinates `[1, 2]` is accepted; direct
review execution returned:

```text
accepted_declared_bounds (0.0, 0.0, 0.0, 0.0) actual_bounds (1.0, 2.0, 1.0, 2.0)
```

This violates the converter specification's requirement to revalidate observed
bounds and means a parser regression/corruption can cross the IPC boundary
without the promised independent reconciliation. The same validation path does
not explicitly reject exponent-overflow JSON numbers such as `1e400` before
Shapely construction; Python decodes that form as infinity even though
`parse_constant` rejects literal `Infinity`.

Required closure: recursively validate finite coordinates, compute bounds from
the decoded geometry objects, and compare those observed bounds with the parser
envelope before CRS planning. Add negative IPC tests for mismatched bounds and
finite-number exponent overflow, plus positive 2D/3D bounds cases.

### M2-CR-02 - Medium - Trusted-parser failures are misclassified as user input

`_run_geoparquet_parser_worker` maps every nonzero status except limit status 4
to HTTP 400 `invalid_vector` (`convert.py:817-829`). The CLI defines status 2
for trusted-launcher argument errors and status 3 for output publication errors;
those are service/converter failures, not malformed user vectors. Signals from
resource enforcement are also folded into `invalid_vector`.

Separately, `_loaded_geoparquet_from_payload` delegates schema/geometry parsing
to `_loaded_shapefile_from_payload`, whose errors are `invalid_shapefile` and in
some serialization paths status 500 (`convert.py:916` and
`convert.py:1303-1391`). Those errors escape without translation. The canonical
contract requires malformed converter output to fail as unavailable and forbids
invalid inputs from becoming 500 responses.

Required closure: map CLI argument/output/internal/signal states to bounded
`vector_converter_unavailable`, `request_timeout`, or the documented resource
limit code as appropriate; translate every malformed GeoParquet IPC/decode or
serialization-boundary error to the canonical vector error family. Add tests
for statuses 1-4, signal termination, malformed geometry, malformed bounds and
serialization rejection.

## Coverage gaps and residual risk

- The seven new tests call conversion internals and replace the normal blocking
  phase. Add route-level tests for `/v1/inspect` and `/v1/convert`, parser-
  unavailable 503 behavior, source/canonical response metadata, and scratch
  cleanup after malformed IPC.
- The GeoParquet readiness probe checks only `feature_count == 1` and
  `geometry_types == ["Polygon"]` (`convert.py:986-1015`). Strengthen it to
  reconcile the canary's known CRS, bounds, geometry coordinates and properties
  so the readiness claim detects semantic parser regressions rather than merely
  a plausibly shaped envelope.
- Exact-image validation covers a representative valid, projected, missing-grid
  and hostile input. Remaining red-corpus/API threshold and cancellation cases
  can be retained for M5 after the two Medium findings close.

## Re-review 1

Focused test command:

```text
/home/workdir/wepppy/.venv/bin/pytest -q \
  tests/shape_converter/unit/test_geoparquet_input.py
16 passed
```

The amendments correctly reject mismatched observed bounds, accept the expected
3D case, reject exponent-overflow floats, translate ordinary CLI statuses and
signals, remove partial output, translate `_loaded_shapefile_from_payload`
errors, and strengthen the readiness canary's known semantic readback.

**M2-CR-01: partially resolved. M2-CR-02: partially resolved. Verdict remains
CHANGES REQUIRED (one Medium malformed-IPC path).** A JSON integer coordinate
that is too large for a double still raises an unhandled `OverflowError` from
Shapely construction. Direct re-review execution with coordinate `10**400`
returned `OverflowError: int too large to convert to float`. The Geo wrapper at
`convert.py:947-956` catches only `ShapeConverterError`, so this malformed
converter envelope can escape the canonical 503 mapping and become an
uncontrolled server failure.

Required final closure: translate `OverflowError` (and any other bounded numeric
conversion exception at this boundary) to `vector_converter_unavailable`, add a
focused huge-integer-coordinate regression, and rerun this review. For strict
schema validation, boolean coordinate/bounds values should also be rejected
rather than accepted through Python's `bool`-is-`int` relationship.

## Re-review 2

Focused suite: **18 passed**. Direct adversarial calls now map both a `10**400`
coordinate and a boolean coordinate to HTTP 503
`vector_converter_unavailable`. The numeric portion of M2-CR-01/02 is closed.

**Verdict remains CHANGES REQUIRED (one Medium strict-IPC depth path).** The new
coordinate validation recursively descends lists and geometry collections
without enforcing the canonical JSON-depth ceiling
(`convert.py:1032-1046`). A malformed parser envelope containing 2,000 nested
coordinate lists raises raw `RecursionError: maximum recursion depth exceeded`
instead of a bounded 503 response. This is the same malformed-converter-output
contract covered by M2-CR-02, and the owned parser already treats depth 16 as
the accepted maximum.

Required closure: enforce the canonical coordinate/geometry tree depth at the
Python IPC readback boundary (preferably without unbounded recursion), translate
over-depth input to `vector_converter_unavailable`, add a focused nested-
coordinate regression, and rerun the final review.
