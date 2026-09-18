# Omni Scenario Data

Scenario artifacts compare complete base and treatment simulations at watershed, hillslope, and channel scales. Values are average annual results unless a column says otherwise.

This file is generated from the Parquet files currently present in this directory. Regenerate the Omni reports after changing an artifact schema.

## Interpretation notes

- Each `scenario` value identifies the base run or a complete Omni treatment scenario.
- Do not sum density or depth columns across elements; use the corresponding mass or volume columns.
- `scenarios.out.parquet` is long-form, while hillslope and channel summaries are wide-form. Their column sets intentionally differ.

## `scenarios.out.parquet`

Long-form, average-annual watershed outlet metrics for the base run and each Omni scenario.

Rows: 77.

### Columns

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| `key` | `string` |  | WEPP outlet metric name. See the Metric keys table for the observed values. |
| `value` | `double` | varies by `key` | Metric value for the row; equivalent to `v` when both columns are present. |
| `units` | `string` |  | Units for `value`, `v`, and the corresponding control/difference values. |
| `scenario` | `string` |  | Base-run or Omni scenario name. |

### Metric keys

This is a long-form table: the modeled variables are values in `key`, not separate columns.

| Key | Units | Description |
| --- | --- | --- |
| `Avg. Ann. P. delivery per unit area of watershed` | kg/ha/yr | Mean annual outlet phosphorus discharge divided by the contributing watershed area. |
| `Avg. Ann. Phosphorus discharge from outlet` | kg/yr | Mean annual phosphorus mass leaving the watershed at the modeled outlet. |
| `Avg. Ann. Precipitation volume in contributing area` | m^3/yr | Mean annual precipitation volume over the area contributing to the outlet. |
| `Avg. Ann. Sed. delivery per unit area of watershed` | tonne/ha/yr | Mean annual outlet sediment discharge divided by the contributing watershed area. |
| `Avg. Ann. irrigation volume in contributing area` | m^3/yr | Mean annual irrigation volume over the area contributing to the outlet. |
| `Avg. Ann. sediment discharge from outlet` | tonne/yr | Mean annual sediment mass leaving the watershed at the modeled outlet. |
| `Avg. Ann. total channel soil loss` | tonne/yr | Mean annual gross soil loss reported across all channel elements. |
| `Avg. Ann. total hillslope soil loss` | tonne/yr | Mean annual gross soil loss reported across all hillslope elements; this is not the mass delivered at the outlet. |
| `Avg. Ann. water discharge from outlet` | m^3/yr | Mean annual water volume discharged at the watershed outlet. |
| `Sediment Delivery Ratio for Watershed` |  | Outlet sediment discharge divided by total hillslope plus channel soil loss; dimensionless. |
| `Total contributing area to outlet` | ha | Watershed area that drains to the modeled outlet. |

### Preview

key | value | units | scenario
--- | --- | --- | ---
Total contributing area to outlet | 1810.92 | ha | undisturbed
Avg. Ann. Precipitation volume in contributing area | 32733947 | m^3/yr | undisturbed
Avg. Ann. irrigation volume in contributing area | 0 | m^3/yr | undisturbed
