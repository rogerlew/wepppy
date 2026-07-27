# Compatibility and Regression Plan

## Schema Mutation

`loss_pw0.all_years.hill.parquet` gains one additive `Float64` column named
`Hillslope Area` with unit metadata `ha`. Existing column names, data types,
units, and values remain unchanged. Historical 11-field annual rows are a
supported source format and receive a null area; corrected 12-field rows
preserve the emitted value. Other widths remain invalid.

## Consumer Audit

The audit covers direct parquet readers, DuckDB SQL, dataframe column lists,
strict schema assertions, report adapters, interchange validation, and fixture
comparisons. Each consumer is classified as named-column compatible,
schema-aware and updated, or unaffected.

## Generated-Output Evidence

The rebuilt py312 native extension must convert an incident-derived fixture.
Validation inspects the generated annual hillslope parquet and proves:

1. `Hillslope Area` equals `1.539` for the representative row;
2. pollutant values remain in their named columns;
3. all prior annual fields remain present with unchanged types and units;
4. average annual output remains unchanged;
5. a malformed column count still fails explicitly.

## Rollback

Revert the WEPPpyo3 source and release-artifact commit, rebuild the WEPPpy
image against the prior WEPPpyo3 ref, and redeploy. No persisted NoDb migration
is required; affected parquet artifacts can be regenerated from stored WEPP
text output.
