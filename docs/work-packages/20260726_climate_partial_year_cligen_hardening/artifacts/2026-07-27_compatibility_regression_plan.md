# Compatibility and Regression Plan

## Artifact Contract

The change preserves all existing filenames, parquet/PRN schemas, NoDb fields,
and sub-climate mappings. Full historical years retain their observed overlays.
Partial current years retain CLIGEN-generated values only where the upstream
variable is unpublished.

## Downstream Propagation

Validation must demonstrate that:

1. source missingness reaches PRN as `9999`, not numeric zero;
2. CLIGEN output remains a complete 365/366-day year;
3. finite observed radiation, dewpoint, and wind values reach the CLI;
4. generated suffix values remain unchanged by post-processing;
5. Daymet and GridMET multiple paths stage the station file before submitting
   any worker future.

## Regression Matrix

| Case | Expected result |
|------|-----------------|
| Complete historical variable | Every date is overlaid |
| Trailing unpublished suffix | Finite prefix overlaid; generated suffix retained |
| First missing value followed by finite value | Explicit internal-gap failure |
| All values missing | Generated full-year variable retained |
| Concurrent multiple build | One finalized parent copy before worker pool |
| Slow destination copy | No worker can observe the temporary file |

## Rollback

Revert the shared staging and overlay helpers together. No persisted schema
migration is required. Existing run artifacts can be rebuilt from their stored
NoDb configuration after rollback.
