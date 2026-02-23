# NoDb Broad Exception Resolution Matrix

This artifact maps every baseline NoDb broad-catch finding to its final disposition.

- Baseline findings (`--no-allowlist`): 137
- Final findings (`--no-allowlist`): 93
- Disposition counts: `boundary+allowlisted=93`, `narrowed=44`, `removed=0`

| Baseline File | Baseline Line | Baseline Handler | Final Disposition | Final Line | Final Handler | Notes |
|---|---:|---|---|---:|---|---|
| `wepppy/nodb/base.py` | 334 | `except Exception as e:` | `boundary+allowlisted` | 525 | `except Exception as exc:  # pragma: no cover - unexpected spawn errors` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 347 | `except Exception as e:` | `boundary+allowlisted` | 798 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 360 | `except Exception as e:` | `boundary+allowlisted` | 915 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 373 | `except Exception as e:` | `boundary+allowlisted` | 933 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 505 | `except Exception as exc:  # pragma: no cover - unexpected spawn errors` | `boundary+allowlisted` | 941 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 776 | `except Exception:` | `boundary+allowlisted` | 980 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 889 | `except Exception:` | `boundary+allowlisted` | 1021 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 906 | `except Exception:` | `boundary+allowlisted` | 1149 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 913 | `except Exception:` | `boundary+allowlisted` | 1218 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 952 | `except Exception as e:` | `boundary+allowlisted` | 1271 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 971 | `except Exception as e:` | `boundary+allowlisted` | 1324 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 1094 | `except Exception:` | `boundary+allowlisted` | 1379 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 1150 | `except Exception:` | `boundary+allowlisted` | 1390 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 1199 | `except Exception:` | `boundary+allowlisted` | 1401 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 1252 | `except Exception:` | `boundary+allowlisted` | 1525 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 1301 | `except Exception:` | `boundary+allowlisted` | 1536 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 1312 | `except Exception:` | `boundary+allowlisted` | 2346 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 1323 | `except Exception:` | `boundary+allowlisted` | 2353 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/base.py` | 1447 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/base.py` | 1457 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/base.py` | 2266 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/base.py` | 2273 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/batch_runner.py` | 264 | `except Exception as e:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/climate.py` | 669 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/climate.py` | 783 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/climate.py` | 799 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/climate_artifact_export_service.py` | 74 | `except Exception:` | `boundary+allowlisted` | 74 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/climate_artifact_export_service.py` | 90 | `except Exception:` | `boundary+allowlisted` | 90 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/climate_artifact_export_service.py` | 238 | `except Exception:` | `boundary+allowlisted` | 238 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/climate_artifact_export_service.py` | 293 | `except Exception:` | `boundary+allowlisted` | 293 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/climate_artifact_export_service.py` | 320 | `except Exception:` | `boundary+allowlisted` | 320 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/climate_artifact_export_service.py` | 327 | `except Exception:` | `boundary+allowlisted` | 327 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/climate_artifact_export_service.py` | 360 | `except Exception:` | `boundary+allowlisted` | 360 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/climate_build_helpers.py` | 765 | `except Exception as exc:` | `boundary+allowlisted` | 765 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/climate_build_helpers.py` | 899 | `except Exception as exc:` | `boundary+allowlisted` | 899 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/climate_build_helpers.py` | 1101 | `except Exception:` | `boundary+allowlisted` | 1101 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/climate_gridmet_multiple_build_service.py` | 402 | `except Exception:` | `boundary+allowlisted` | 402 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/landuse.py` | 136 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/landuse.py` | 162 | `except Exception as exc:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/landuse.py` | 1457 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/landuse.py` | 1471 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/landuse.py` | 1526 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/landuse.py` | 1537 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/ron.py` | 1456 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/ron.py` | 1462 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/soils.py` | 585 | `except Exception as exc:` | `boundary+allowlisted` | 585 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/soils.py` | 1406 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/soils.py` | 1420 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/soils.py` | 1462 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/soils.py` | 1473 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/watershed.py` | 369 | `except Exception:` | `boundary+allowlisted` | 369 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 391 | `except Exception:` | `boundary+allowlisted` | 391 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 399 | `except Exception:` | `boundary+allowlisted` | 399 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 722 | `except Exception:` | `boundary+allowlisted` | 722 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 798 | `except Exception:` | `boundary+allowlisted` | 798 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 839 | `except Exception as exc:` | `boundary+allowlisted` | 839 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 845 | `except Exception as exc:` | `boundary+allowlisted` | 845 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 851 | `except Exception as exc:` | `boundary+allowlisted` | 851 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 863 | `except Exception as exc:` | `boundary+allowlisted` | 863 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 879 | `except Exception as exc:` | `boundary+allowlisted` | 879 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 978 | `except Exception as e:` | `boundary+allowlisted` | 978 | `except Exception as e:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 1030 | `except Exception as exc:` | `boundary+allowlisted` | 1030 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 1052 | `except Exception:` | `boundary+allowlisted` | 1052 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 1076 | `except Exception:` | `boundary+allowlisted` | 1076 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/watershed.py` | 1168 | `except Exception as exc:` | `boundary+allowlisted` | 1168 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/wepp.py` | 884 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/wepp.py` | 918 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/wepp.py` | 1671 | `except Exception as exc:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/wepp.py` | 1676 | `except Exception as retry_exc:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/wepp.py` | 1682 | `except Exception as exc:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/core/wepp_prep_service.py` | 263 | `except Exception as exc:` | `boundary+allowlisted` | 263 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/wepp_prep_service.py` | 276 | `except Exception as exc:` | `boundary+allowlisted` | 276 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/wepp_prep_service.py` | 501 | `except Exception as exc:` | `boundary+allowlisted` | 501 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/wepp_prep_service.py` | 511 | `except Exception as exc:` | `boundary+allowlisted` | 511 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/wepp_prep_service.py` | 571 | `except Exception:` | `boundary+allowlisted` | 571 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/wepp_run_service.py` | 87 | `except Exception as exc:` | `boundary+allowlisted` | 87 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/wepp_run_service.py` | 125 | `except Exception as exc:` | `boundary+allowlisted` | 125 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/wepp_run_service.py` | 161 | `except Exception as exc:` | `boundary+allowlisted` | 161 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/core/wepp_run_service.py` | 322 | `except Exception as exc:` | `boundary+allowlisted` | 322 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/culverts_runner.py` | 553 | `except Exception as exc:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/__init__.py` | 56 | `except Exception:  # pragma: no cover - fallback during partial imports` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/ag_fields/ag_fields.py` | 49 | `except Exception:  # pragma: no cover - optional dependency` | `boundary+allowlisted` | 200 | `except Exception as exc:  # pragma: no cover - best effort` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/ag_fields/ag_fields.py` | 200 | `except Exception as exc:  # pragma: no cover - best effort` | `boundary+allowlisted` | 601 | `except Exception as e:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/ag_fields/ag_fields.py` | 601 | `except Exception as e:` | `boundary+allowlisted` | 614 | `except Exception as e:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/ag_fields/ag_fields.py` | 614 | `except Exception as e:` | `boundary+allowlisted` | 766 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/ag_fields/ag_fields.py` | 766 | `except Exception as exc:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/ash_transport/ash.py` | 808 | `except Exception as exc:` | `boundary+allowlisted` | 808 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/ash_transport/ash.py` | 825 | `except Exception:` | `boundary+allowlisted` | 825 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/baer/sbs_map.py` | 86 | `except Exception:` | `boundary+allowlisted` | 144 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/baer/sbs_map.py` | 123 | `except Exception:` | `boundary+allowlisted` | 167 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/baer/sbs_map.py` | 144 | `except Exception:` | `boundary+allowlisted` | 190 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/baer/sbs_map.py` | 167 | `except Exception:` | `boundary+allowlisted` | 227 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/baer/sbs_map.py` | 190 | `except Exception:` | `boundary+allowlisted` | 264 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/baer/sbs_map.py` | 227 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/baer/sbs_map.py` | 264 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/disturbed/disturbed.py` | 434 | `except Exception:` | `boundary+allowlisted` | 434 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/disturbed/disturbed.py` | 1132 | `except Exception as exc:` | `boundary+allowlisted` | 1132 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/observed/observed.py` | 623 | `except Exception as exc:` | `boundary+allowlisted` | 623 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/observed/observed.py` | 684 | `except Exception:` | `boundary+allowlisted` | 684 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/omni/omni.py` | 181 | `except Exception as exc:  # Boundary: cache cleanup should not break clone teardown.` | `boundary+allowlisted` | 181 | `except Exception as exc:  # Boundary: cache cleanup should not break clone teardown.` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/omni/omni.py` | 191 | `except Exception as exc:  # Boundary: lock cleanup should not break clone teardown.` | `boundary+allowlisted` | 191 | `except Exception as exc:  # Boundary: lock cleanup should not break clone teardown.` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/omni/omni.py` | 231 | `except Exception as exc:` | `boundary+allowlisted` | 231 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/omni/omni.py` | 795 | `except Exception:  # pragma: no cover - catalog refresh best effort` | `boundary+allowlisted` | 795 | `except Exception:  # pragma: no cover - catalog refresh best effort` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/omni/omni.py` | 1181 | `except Exception:  # Boundary: return-period refresh should not block run finalization.` | `boundary+allowlisted` | 1181 | `except Exception:  # Boundary: return-period refresh should not block run finalization.` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/omni/omni_artifact_export_service.py` | 634 | `except Exception as exc:  # pragma: no cover - best effort restore` | `boundary+allowlisted` | 634 | `except Exception as exc:  # pragma: no cover - best effort restore` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/omni/omni_artifact_export_service.py` | 691 | `except Exception as exc:  # pragma: no cover - best effort restore` | `boundary+allowlisted` | 691 | `except Exception as exc:  # pragma: no cover - best effort restore` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/omni/omni_contrast_build_service.py` | 1197 | `except Exception as exc:  # Boundary: malformed user geometry should not abort all features.` | `boundary+allowlisted` | 1197 | `except Exception as exc:  # Boundary: malformed user geometry should not abort all features.` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/omni/omni_run_orchestration_service.py` | 176 | `except Exception as exc:  # Boundary: status tracking must record any run failure before re-raising.` | `boundary+allowlisted` | 176 | `except Exception as exc:  # Boundary: status tracking must record any run failure before re-raising.` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/omni/omni_station_catalog_service.py` | 191 | `except Exception as exc:` | `boundary+allowlisted` | 191 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/omni/omni_station_catalog_service.py` | 200 | `except Exception as exc:` | `boundary+allowlisted` | 200 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/openet/openet_ts.py` | 287 | `except Exception as exc:` | `boundary+allowlisted` | 287 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/openet/openet_ts.py` | 468 | `except Exception as exc:` | `boundary+allowlisted` | 468 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/path_ce/data_loader.py` | 78 | `except Exception as exc:  # pragma: no cover - pandas/pyarrow exceptions are diverse` | `boundary+allowlisted` | 78 | `except Exception as exc:  # pragma: no cover - pandas/pyarrow exceptions are diverse` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/path_ce/path_cost_effective.py` | 25 | `except Exception:  # pragma: no cover - optional dependency` | `boundary+allowlisted` | 395 | `except Exception as exc:  # pragma: no cover - filesystem errors` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/path_ce/path_cost_effective.py` | 277 | `except Exception:` | `boundary+allowlisted` | 434 | `except Exception:  # pragma: no cover - best effort` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/path_ce/path_cost_effective.py` | 395 | `except Exception as exc:  # pragma: no cover - filesystem errors` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/path_ce/path_cost_effective.py` | 434 | `except Exception:  # pragma: no cover - best effort` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/rap/rap_ts.py` | 247 | `except Exception as exc:` | `boundary+allowlisted` | 247 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/rap/rap_ts.py` | 354 | `except Exception as exc:` | `boundary+allowlisted` | 354 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/rhem/rhem.py` | 215 | `except Exception as exc:` | `boundary+allowlisted` | 215 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/rhem/rhem.py` | 281 | `except Exception as exc:` | `boundary+allowlisted` | 281 | `except Exception as exc:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/skid_trails/skid_trails.py` | 38 | `except Exception:  # pragma: no cover - optional dependency` | `boundary+allowlisted` | 361 | `except Exception:  # pragma: no cover - catalog refresh best effort` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/skid_trails/skid_trails.py` | 361 | `except Exception:  # pragma: no cover - catalog refresh best effort` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/swat/swat.py` | 771 | `except Exception:` | `boundary+allowlisted` | 771 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/swat/swat.py` | 796 | `except Exception:` | `boundary+allowlisted` | 796 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/mods/swat/swat.py` | 818 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/swat/swat.py` | 900 | `except Exception as exc:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/swat/swat.py` | 995 | `except Exception as exc:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/swat/swat.py` | 999 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/swat/swat.py` | 1007 | `except Exception as exc:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/swat/swat.py` | 1014 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/mods/treatments/treatments.py` | 161 | `except Exception:` | `boundary+allowlisted` | 161 | `except Exception:` | Residual boundary retained and allowlisted. |
| `wepppy/nodb/unitizer.py` | 458 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/unitizer.py` | 537 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/unitizer.py` | 588 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/unitizer.py` | 615 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
| `wepppy/nodb/unitizer.py` | 657 | `except Exception:` | `narrowed` | - | `-` | Broad catch removed or narrowed to expected exception types. |
