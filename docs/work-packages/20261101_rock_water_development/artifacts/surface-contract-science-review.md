# Surface proxy support contract: scientific review

Disposition: **PASS for the additive metadata contract and implementation plan.**
This is not approval of implementation, a new proxy/default policy, automatic
SSURGO aggregation, or native surface-rock mechanics. Production code was not
edited or executed by this reviewer.

## Reviewed semantics

The recognized-column report retains its original numerical meaning while adding
record/support diagnostics. NULL, numeric nonfinite, unparseable excluded values,
finite out-of-range values and reported zero remain distinct. `used_rows` means
numerically included records; it does not imply independent measurements, valid
surface-cover evidence or field support. Zero and out-of-range counts are subsets
of finite records rather than mutually exclusive top-level support partitions.

The area denominator is all finite positive source-table area, including rows
whose cover is missing or unusable. The numerator is area admitted by the original
aggregation. Consequently the fraction exposes selection on known area; unknown
area cannot become zero area or a complete-footprint claim. Null area fields when
no area column exists distinguish absent area support from an observed zero sum.
Area units remain whatever the source column supplies, without inventing square
meters or assuming survey component percentages are project geometry.

Original selection, mean, clamp, source priority, overrides, fallback values,
C raster values and existing manifest keys must remain unchanged. Finite cover
outside0–100 is diagnosed but retains its existing numeric participation. This
is appropriately narrower than revising or scientifically admitting the proxy.
Historical manifests remain valid; metadata appears only on recalculation.

## Review issues resolved before ancestor approval

The initial successful-query wording was ambiguous for nonnumeric values returned
by a valid SQL query. The final contract requires successful parsing of numerical
aggregation inputs and permits existing query/parse-error reports without partial
support. Empty/all-NULL numeric columns still retain diagnostics.

Reading all rows for metadata can expose malformed values that original selection
never evaluated. The final contract explicitly preserves NULL-cover/bad-area,
bad-cover/NULL-area and nonfinite-cover/bad-area exclusions. Excluded unparseable
cover gets its own count rather than being called numeric nonfinite. Consumed
malformed values retain the original unavailable/error behavior. These changes
prevent a metadata-only feature from altering proxy selection or fallback.

## Required implementation evidence

The declared actual-parquet and RAP/SBS GeoTIFF/manifest path is appropriate.
Controls must distinguish missing files/columns from recognized empty/all-unusable
columns, measured zero from absence, known-area selection from unknown-area rows,
and malformed excluded values from malformed consumed values. Read the generated
manifest rather than relying only on loader mocks. Compare actual C/cover raster
values and source selection against independently frozen prior-behavior expectations.
The contract's short-circuit controls are meaningful compatibility coverage.

No new numerical parameter/formula is proposed, so a parameterization ADR is not
needed for this metadata-only contract. Required code reviews and production
regression gates still follow after the reviewed ancestor commit. The change
must not be represented as validation of the survey-to-Roads or profile-to-surface
relationship; those remain separate scientific questions.

## Exact reviewed bindings

- `wepppy/nodb/mods/rusle/specification.md`:
  `0130e56ad8b72bffca4935cbd467de60529cf51cd1d58a7aa43359b183360b99`
- `docs/schemas/rock-fragment-representation-contract.md`:
  `2560586e2f1b734ac351bf5f213411f18d9e3c8740c7e1e81e91ce7aeb498eac`
- `artifacts/20261101_surface_contract_decision.md`:
  `8d08c323447ed4629cca5d001f34ed2c2059fb9ba79e38acfdf87996559e889b`

No old evidence or raw root was written. Reviewer writers are clear after lint.
