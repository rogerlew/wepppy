# Climate precipitation scale-map authority

## Authority and scope

The spatial precipitation scale map is configuration-owned and immutable to
browser/API climate submissions. This contract covers `Climate.precip_scale_factor_map`,
the persisted `_precip_scale_factor_map`, and the corresponding climate control.
It does not change scalar/monthly scaling, raster values, or climate dataset selection.

## Resolution and persistence

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
trusting it allowed the former scalar display value `"1.1"` to overwrite the
map. Server-side configuration authority also handles stale pages and corrupted
NoDb snapshots. Rejecting old payloads was rejected because an ignored display
field should not block a valid climate rebuild.

Implementation conformance is pending the registered repair package:
`docs/work-packages/20260909_climate_scale_map_authority/`.
