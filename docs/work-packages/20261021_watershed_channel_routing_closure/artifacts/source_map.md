# Source map and accounting boundaries

Execution started 2026-10-21. Source identity is in `provenance.json`.
This is a source map, not proof that a generated trajectory closes.

| Boundary | Producer and consumer in wepp-forest | Units and accounting |
| --- | --- | --- |
| OFE soil water | `src/watbal.for`, `src/watbal_hourly.for`; daily/hourly adapters and process kernels | Local depths require each OFE area; internal runon cancels only after converting each side to volume. |
| Terminal surface export | `src/wshpas.f90` to `hbp_legacy_capture` | `runoff(nplane)` is m; `runvol(nplane)` is m3. Preserve physical and event-selected quantities separately. |
| Terminal lateral export | `src/wshpas.f90:146,216` | `sbrunf(nplane) * slplen(nplane) * fwidth(nplane)` is m3. Never multiply terminal lateral depth by total hillslope area. |
| PASS selection | `src/wshpas.f90:139-253` | EVENT at surface depth >= 0.001 m; otherwise SUBEVENT for positive lateral volume > 0.01 m3 or tile conditions; NO EVENT otherwise. Exact nesting matters. |
| Binary payload | `fpm-src/hillslope_binary_pass_legacy_adapter.f90:182` and binary writer | Adapter records raw quantities; serialization depends on event kind. A raw adapter field is not evidence that every event carries it. |
| Loaded hillslope flux | `fpm-src/hillslope_binary_pass_reader.f90:451-563` | Reader converts serialized volumes into routing arrays. Actual opened `.hbp` and loaded day must be joined; text PASS is not a substitute. |
| Groundwater | `src/contin.for`, `gwbfv`, `gwdsv`, PASS state registry | Dp is a soil export and groundwater recharge. Baseflow and seepage are separate groundwater exports; Dp must not also be an external combined-domain loss. |
| Channel inflow | `src/wshcqi.f90`, `src/wshdrv.f90` | Hillslope/channel connectivity and lateral/top contributions feed route kernels. Identify channel-local additions separately. |
| Channel balance | `src/wshchr.f90:768-846`, `fpm-src/watbal_route_kernels.f90` | Existing diagnostics expose inflow, outflow, transmission loss, storage change and baseflow in m3. Residual = inflow + baseflow - outflow - loss - storage increase. |
| Channel downstream export | `src/wshchr.f90:850-876` | Published `runvol`/`tmpvol` must be checked against diagnostic outflow, including low-volume branches. |
| Impoundment | `src/wshiqi.f90`, `src/wshimp.for`, routing kernels | Independent storage/loss boundary; channel-only diagnostics cannot establish its closure. |

## Required control volumes

The soil profile includes surface/interception/snow stores when those stores
participate in the selected interval. Groundwater has its own recharge, baseflow,
seepage and storage ledger. Each channel/impoundment has incoming transfers,
local additions, exports, losses and storage. The combined domain cancels internal
transfers once by connectivity and time. Unknown stores are unknown, never zero.

## Initial provenance findings

The workbook is retained with its hash, but its original decks and binary are
not identified. `reconciled_condenser_pw0` is a metadata fixture, not a complete
watershed replay deck. The live path named by the plan is absent locally.
The complete `up_pedantry_h5` fixture retains six configured years and shared
runtime files; a baseline attempt is retained under the provenance holdout root.

The default native make link omits zlib despite binary PASS calling `compress2`
and `uncompress`. The failed build log is retained. Explicit
`LDFLAGS='-mcmodel=medium -no-pie -lz'` supplies the existing dependency without
changing source or simulation flags.
