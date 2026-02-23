# Milestone 6 Resolution Matrix

- Baseline source: `artifacts/milestone_6_residual_baseline.json`
- Postfix source: `artifacts/milestone_6_postfix.json`
- Baseline unresolved findings: **51**
- Postfix unresolved findings: **0**

## Disposition Summary

- `narrow`: 43
- `true-boundary+allowlist`: 7
- `remove`: 1

## Finding-Level Disposition

| Path | Line | Handler | Disposition | Owner | Rationale | Expiry |
|------|-----:|---------|-------------|-------|-----------|--------|
| `services/cao/ci-samurai/diagnose_artifact.py` | 70 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/cao/ci-samurai/diagnose_artifact.py` | 112 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/cao/ci-samurai/run_fixer_loop.py` | 46 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/cao/ci-samurai/run_fixer_loop.py` | 127 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/cao/ci-samurai/run_fixer_loop.py` | 158 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/cao/ci-samurai/run_fixer_loop.py` | 174 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/cao/ci-samurai/run_fixer_loop.py` | 360 | `except Exception as e:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/cao/ci-samurai/run_fixer_loop.py` | 422 | `except Exception as e:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/cao/scripts/wojak_bootstrap.py` | 160 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/cao/wepppy/cli_agent_orchestrator/services/flow_service.py` | 102 | `except Exception as exc:  # Broad by design to avoid extra deps` | `true-boundary+allowlist` | cao maintainers | Test-facing shim boundary translates persistence-layer duplicate-name failures into a stable ValueError contract. | `2026-09-30` |
| `services/profile_playback/app.py` | 237 | `except Exception as exc:  # pragma: no cover - defensive logging` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/profile_playback/app.py` | 602 | `except Exception as exc:  # pragma: no cover - defensive logging` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/profile_playback/app.py` | 629 | `except Exception as exc:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/profile_playback/app.py` | 829 | `except Exception as exc:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/profile_playback/app.py` | 895 | `except Exception:  # pragma: no cover - defensive logging` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `services/profile_playback/app.py` | 904 | `except Exception as cleanup_exc:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/all_your_base/all_your_base.py` | 264 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/all_your_base/all_your_base.py` | 281 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/all_your_base/all_your_base.py` | 345 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/all_your_base/all_your_base.py` | 347 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/all_your_base/all_your_base.py` | 364 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/all_your_base/geo/geo.py` | 636 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/all_your_base/geo/locationinfo.py` | 222 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/all_your_base/geo/webclients/wmesque.py` | 66 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/all_your_base/geo/webclients/wmesque.py` | 156 | `except Exception as e:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/all_your_base/geo/webclients/wmesque.py` | 176 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/all_your_base/hydro/objective_functions.py` | 299 | `except Exception:  # pragma: no cover - guard against unexpected errors` | `true-boundary+allowlist` | all_your_base maintainers | Per-metric evaluation boundary: logs metric-specific failure and returns NaN so batch evaluation continues. | `2026-09-30` |
| `wepppy/config/redis_settings.py` | 23 | `except Exception:  # pragma: no cover - redis is optional for typing` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/export/gpkg_export.py` | 210 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/export/gpkg_export.py` | 305 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/landcover/rap/rangeland_analysis_platform.py` | 135 | `except Exception as e:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/locales/canada/bc/soils/sift/sift.py` | 133 | `except Exception:` | `true-boundary+allowlist` | locales soils maintainers | Best-effort SIFT horizon enrichment boundary; rosetta failures are logged and do not abort soil build. | `2026-09-30` |
| `wepppy/locales/canada/bc/soils/sift/sift.py` | 138 | `except Exception:` | `true-boundary+allowlist` | locales soils maintainers | Best-effort SIFT horizon enrichment boundary; conductivity failures are logged and do not abort soil build. | `2026-09-30` |
| `wepppy/locales/canada/bc/soils/sift/sift.py` | 143 | `except Exception:` | `true-boundary+allowlist` | locales soils maintainers | Best-effort SIFT horizon enrichment boundary; erodibility failures are logged and do not abort soil build. | `2026-09-30` |
| `wepppy/locales/canada/bc/soils/sift/sift.py` | 148 | `except Exception:` | `true-boundary+allowlist` | locales soils maintainers | Best-effort SIFT horizon enrichment boundary; anisotropy failures are logged and do not abort soil build. | `2026-09-30` |
| `wepppy/locales/conus/openet/openet_client.py` | 184 | `except Exception as exc:  # pragma: no cover - API/network errors` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/locales/earth/soils/isric/__init__.py` | 245 | `except Exception:` | `true-boundary+allowlist` | locales soils maintainers | ThreadPool boundary cancels pending WMS tasks on unexpected failure, logs context, and re-raises to avoid partial outputs. | `2026-09-30` |
| `wepppy/profile_coverage/runtime.py` | 71 | `except Exception as exc:  # pragma: no cover - logging only` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/soils/ssurgo/ssurgo.py` | 77 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/soils/ssurgo/ssurgo.py` | 99 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/soils/ssurgo/ssurgo.py` | 107 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/soils/ssurgo/ssurgo.py` | 175 | `except Exception as exc:  # pragma: no cover - unexpected spawn errors` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/soils/ssurgo/ssurgo.py` | 1827 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/soils/ssurgo/ssurgo.py` | 2010 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/topo/peridot/peridot_runner.py` | 25 | `except Exception:  # pragma: no cover - optional catalog support` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/topo/peridot/peridot_runner.py` | 229 | `except Exception:  # pragma: no cover - catalog refresh best effort` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/topo/peridot/peridot_runner.py` | 312 | `except Exception:  # pragma: no cover - catalog refresh best effort` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/topo/peridot/peridot_runner.py` | 512 | `except Exception:  # pragma: no cover - catalog refresh best effort` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/topo/topaz/topaz.py` | 694 | `except Exception:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/topo/wbt/wbt_topaz_emulator.py` | 1219 | `except Exception as exc:` | `narrow` | module maintainers | Replaced broad catch with expected typed exceptions to preserve explicit failure semantics. | - |
| `wepppy/watershed_boundary_dataset/usgs_wbd.py` | 151 | `except Exception:` | `remove` | module maintainers | Removed dead broad handler; operation now fails explicitly on unexpected errors. | - |
