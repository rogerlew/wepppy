# GridMET admission call inventory

Audited 2026-09-07 after contract checkpoint
`1b4835ca73bc67c9c84ecbb26f596aab4078e234` with:

```bash
rg -n 'retrieve_nc|retrieve_historical_(precip|wind|timeseries)|request_single_location_json' wepppy tests
rg -n 'admission=|GridMetAdmissionConfig.from_env' wepppy/climates wepppy/nodb/core
```

## Acquisition and forwarding boundaries

| Caller | GridMET target | Configuration ownership |
| --- | --- | --- |
| GridMET public precipitation, wind, and full-timeseries clients | `request_single_location_json` | Forward keyword-only `admission=None`; never read environment |
| `gridmet.client.retrieve_timeseries` | `retrieve_nc`, every measure/year | Forward the same explicit configuration |
| `build_observed_gridmet` | GridMET full timeseries | Resolve environment once per helper operation |
| `get_gridmet_p_annual_monthlies` | GridMET precipitation | Resolve environment once before retrieval |
| `build_observed_prism` | PRISM public client, then GridMET wind | Resolve once when wind enabled; PRISM forwards explicitly |
| `build_observed_daymet` | Daymet public client, then GridMET wind | Resolve once when wind enabled; Daymet forwards explicitly |
| `build_observed_snotel` | GridMET full timeseries supplement | Resolve once when supplementation enabled |
| `_apply_depnexrad_daily_temp_overrides`, GridMET branch | GridMET full timeseries | Resolve once before acquisition |
| `run_observed_daymet_multiple_build` | Interpolation helper and `_resolve_daymet_wind` | Resolve once when effective wind enabled; share immutable configuration across both helpers |
| `_interpolate_daymet_hillslope_series` | Daymet `interpolate_daily_timeseries` | Forward operation configuration |
| Daymet `interpolate_daily_timeseries` | Process-pool `_retrieve_historical_timeseries_wrapper` | Pass immutable configuration as task keyword; preserve existing wind-disabled interpolation |
| Daymet `_retrieve_historical_timeseries_wrapper` | Daymet public timeseries | Forward literal `None` or configuration without environment lookup |
| `_resolve_daymet_wind` | GridMET public wind | Forward operation configuration |
| `ClimateGridmetMultipleBuildService.build` | `_retrieve_gridmet_netcdfs` and process-pool `retrieve_nc` | Resolve once in build; task arguments contain only immutable configuration; preserve local four-worker ceiling |

`climate.py` retains legacy imports of the public GridMET/PRISM aliases but
contains no direct calls. Daymet/PRISM precipitation-monthlies helpers and their
DEP NEXRAD temperature branches use wind-disabled clients and therefore make
no GridMET request. Library `__main__` examples retain omitted admission, whose
contracted meaning is disabled. All existing positional parameters remain
compatible; new public forwarding parameters are keyword-only. Updated Daymet
`.pyi` signatures match the runtime API.

## Regression evidence

```bash
wctl run-pytest tests/nodb/test_climate_build_helpers.py tests/nodb/test_climate_gridmet_multiple_build_service.py tests/climates/test_gridmet_propagation.py tests/climates/daymet/test_daymet_singlelocation_client.py --maxfail=1
```

Result: **56 passed**, 4 existing dependency/projection deprecation warnings.
The tests cover exact configuration forwarding through observed GridMET,
precipitation monthlies, PRISM/Daymet wind, SNOTEL, DEP NEXRAD, and both
multiple-build paths; one environment resolution shared by Daymet interpolation
and wind; explicit `None` under an enabled environment; and successful pickling
of actual process-pool task arguments while retaining the GridMET four-worker
ceiling. HTTP/Redis lifecycle and live-process concurrency evidence belongs in
the dedicated acquisition/admission and Forest validation artifacts.

Additional gates: `wctl run-stubtest
wepppy.climates.daymet.daymet_singlelocation_client` reported no issues in one
module; `wctl check-test-stubs` reported all stubs complete. The inventory and
updated existing Daymet boundary-allowlist line references passed documentation
lint. Full-suite and live Forest validation are coordinated by the root agent.

Correctness review regression: Daymet multiple builds with GridMET wind disabled
ignore malformed admission environment because they perform no GridMET calls.
The existing final-output test covers both effective wind states.
