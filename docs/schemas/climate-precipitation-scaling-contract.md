# Climate precipitation scaling defaults and scale-map authority

## Authority and scope

The spatial precipitation scale map is configuration-owned and immutable to
browser/API climate submissions. This contract covers the new-project
`Climate.precip_scaling_mode` default, `Climate.precip_scale_factor_map`,
the persisted `_precip_scale_factor_map`, and the corresponding climate control.
It does not change scalar/monthly scaling, raster values, or climate dataset selection.

## Resolution and persistence

For new projects, after resolving all configured scaling factors, maps and an
explicit `precip_scale_mode` using existing precedence, an otherwise unset mode
MUST be stored as `ClimatePrecipScalingMode.NoScaling` (0). The climate control
MUST render "No scaling" checked for that default. Configured modes and factors
retain their meaning. This decision does not migrate existing stored `None`
values or change their established unscaled execution behavior.

The operator approved this default on 2026-10-16 to eliminate the blank radio
selection in new projects. Explicit initialization was chosen over a template
fallback so persisted state and presentation agree. Implementation conformance
is pending. See [ADR-0096](../adrs/ADR-0096-new-project-no-scaling-default.md).

This initialization default applies only after existing configuration readers
and mode parsing succeed. Missing or reader-admitted empty settings that leave
the mode unset select NoScaling. Invalid configured modes retain explicit parse
failure; invalid factor/map inputs retain their existing reader and selected-mode
validation behavior. Do not catch configuration failures to select NoScaling.

Resolve the effective map using the run's canonical configuration reader and
path-token expansion. Preserve the existing initialization precedence: the first
non-`None` value among `daymet_precip_scale_factor_map`,
`gridmet_precip_scale_factor_map`, and `precip_scale_factor_map` wins. This is
legacy precedence, not a new dataset-dependent selection algorithm.

If no map is configured, the effective value is `None`. Never substitute a
submitted map, scalar multiplier, or stale persisted string. Configuration
reader failures remain explicit failures.

`Climate.precip_scale_factor_map` MUST return the configured value regardless
of stale persisted state. A successful climate input parse MUST synchronize
`_precip_scale_factor_map` to that configured value within the existing NoDb
lock/rollback transaction. A failed parse retains the existing rollback contract.

## Browser and API compatibility

The map control displays the resolved configured path and cannot be edited or
submitted by the current browser form. Older forms/API callers may still send
`precip_scale_factor_map`; accept and ignore that compatibility field rather
than failing an otherwise valid rebuild. Never assign it to controller state.
Configured and previously corrupted runs retain their existing climate-mode
requirements. An unconfigured map is valid for non-spatial scaling. Spatial
scaling without a configured map retains the existing explicit validation
failure `ValueError("precip_scale_factor_map is None")`; do not fall back to a
client path or scalar. Legacy custom-map callers are transport-compatible but
must configure their map before spatial scaling can run.

## Decision and rationale

On 2026-09-09 the operator directed that Marta's `portland-10-mofe` runs use
the configured `/geodata/extended_mods_data/wepppy-locations-portland/daymet_scale.tif`
and that the map remain immutable. Read-only HTML still submits a field;
trusting it allowed a submitted scalar string `"1.1"` to overwrite the
map. The operator reported an earlier scalar-display bug; the inspected
deployed template already bound the map property. Server-side configuration authority also handles stale pages and corrupted
NoDb snapshots. Rejecting old payloads was rejected because an ignored display
field should not block a valid climate rebuild.

Implementation and live repair evidence are recorded in the repair package:
`docs/work-packages/20260909_climate_scale_map_authority/`.
