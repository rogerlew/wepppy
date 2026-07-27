# WEPP LOSS Annual Hillslope Consumer Audit

## Revised Dataset

`loss_pw0.all_years.hill.parquet` adds nullable `Hillslope Area` (`Float64`,
`ha`) between `Sediment Yield` and the pollutant fields. Its table-specific
`schema_version` advances from `1` to `2`. Other LOSS datasets, including
average hillslope output, remain schema version `1`.

## Consumer Matrix

| Consumer | Access pattern | Compatibility evidence |
|----------|----------------|------------------------|
| Watershed LOSS native facade | Full generated schema | Integration test asserts 13 columns, schema version 2, units, true legacy nulls, current area, and pollutant positions. |
| Sediment characteristics report | Named `year` count only | Targeted report tests pass; additive area is not projected. |
| GL dashboard and batch dashboard | Cataloged parquet exposed with named measures | Route tests pass; no positional schema assumption found. |
| Features export temporal layer | Catalog/path registration and named projections | Service tests pass; additive source column does not alter existing projection. |
| Query engine / DuckDB | Named-column SQL and dynamic catalog schema | Generated parquet is read during integration and consumer tests; no fixed ordinal projection found. |
| Average hillslope reports, Omni, Roads, and `Loss` facade | `loss_pw0.hill.parquet`, not all-years hillslope | Unaffected; average schema and version remain unchanged and existing integration assertions pass. |
| Interchange migrations | Regenerate from stored `loss_pw0.txt` | Historical 11-field fixture converts with true null area; current 12-field fixture converts with emitted area. |

## Compatibility Conclusion

No WEPPpy production consumer requires a source change. Consumers either select
existing columns by name, expose the dataset dynamically, or use the unchanged
average table. The schema snapshot and native integration expectations were
the only strict all-years schema contracts and were updated.

The parser detects one annual hillslope layout for the complete source file.
It accepts only uniform 11-field legacy or uniform 12-field current input,
preventing a truncated current row from being misclassified as legacy.
