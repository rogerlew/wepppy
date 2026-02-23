# Target Module Broad-Exception Classification

This artifact tracks final broad-catch disposition for the Phase 2 target modules.

- Baseline in-scope broad catches (`--no-allowlist`): **523**
- Final in-scope broad catches (`--no-allowlist`): **475**
- Broad catches removed via narrowing/removal during this phase (count delta): **48**

## Final Disposition Summary

- `boundary+allowlisted`: 475
- `narrowed`: 48 (count-based delta from baseline to final no-allowlist scan)
- `removed`: included in `narrowed` count where broad handlers were deleted (not separately distinguishable from scanner output alone).

### Final Broad Catches by Subsystem

- `weppcloud/routes`: 175 (all `boundary+allowlisted`)
- `rq_engine`: 150 (all `boundary+allowlisted`)
- `rq`: 150 (all `boundary+allowlisted`)

## Files with Reduced Broad-Catch Counts

| File | Baseline | Final | Delta |
|---|---:|---:|---:|
| `wepppy/microservices/rq_engine/admin_job_routes.py` | 7 | 5 | -2 |
| `wepppy/microservices/rq_engine/landuse_routes.py` | 3 | 2 | -1 |
| `wepppy/microservices/rq_engine/landuse_soils_routes.py` | 2 | 1 | -1 |
| `wepppy/microservices/rq_engine/migration_routes.py` | 7 | 3 | -4 |
| `wepppy/microservices/rq_engine/rap_ts_routes.py` | 3 | 2 | -1 |
| `wepppy/microservices/rq_engine/run_sync_routes.py` | 6 | 4 | -2 |
| `wepppy/microservices/rq_engine/session_routes.py` | 3 | 1 | -2 |
| `wepppy/microservices/rq_engine/treatments_routes.py` | 5 | 2 | -3 |
| `wepppy/rq/auth_actor.py` | 3 | 0 | -3 |
| `wepppy/rq/path_ce_rq.py` | 7 | 2 | -5 |
| `wepppy/weppcloud/routes/_common.py` | 1 | 0 | -1 |
| `wepppy/weppcloud/routes/_security/logging.py` | 7 | 0 | -7 |
| `wepppy/weppcloud/routes/_security/oauth.py` | 7 | 0 | -7 |
| `wepppy/weppcloud/routes/gl_dashboard.py` | 3 | 0 | -3 |
| `wepppy/weppcloud/routes/readme_md/readme_md.py` | 9 | 6 | -3 |
| `wepppy/weppcloud/routes/test_bp.py` | 3 | 0 | -3 |

## Line-by-Line Final Disposition

| Path | Line | Handler | Disposition | Notes |
|---|---:|---|---|---|
| `wepppy/microservices/rq_engine/admin_job_routes.py` | 110 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/admin_job_routes.py` | 218 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/admin_job_routes.py` | 241 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/admin_job_routes.py` | 269 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/admin_job_routes.py` | 285 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/ash_routes.py` | 185 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/ash_routes.py` | 324 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/batch_routes.py` | 49 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/batch_routes.py` | 63 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/batch_routes.py` | 69 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/batch_routes.py` | 87 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/batch_routes.py` | 123 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/batch_routes.py` | 133 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 154 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 166 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 193 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 206 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 233 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 242 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 269 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 278 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 306 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 320 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 348 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 366 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 394 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 407 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 435 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 448 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/climate_routes.py` | 60 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/climate_routes.py` | 73 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/climate_routes.py` | 100 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/culvert_routes.py` | 88 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/culvert_routes.py` | 168 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/culvert_routes.py` | 189 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/culvert_routes.py` | 221 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/culvert_routes.py` | 310 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/debris_flow_routes.py` | 69 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/debris_flow_routes.py` | 125 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/debug_routes.py` | 55 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/dss_export_routes.py` | 76 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/dss_export_routes.py` | 193 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/export_routes.py` | 86 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/export_routes.py` | 101 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/export_routes.py` | 129 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/export_routes.py` | 149 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/export_routes.py` | 177 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/export_routes.py` | 197 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/export_routes.py` | 242 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/export_routes.py` | 271 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 72 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 135 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 143 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 237 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 419 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 452 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 494 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 523 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 573 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 602 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 640 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/job_routes.py` | 268 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/job_routes.py` | 334 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/job_routes.py` | 398 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/job_routes.py` | 434 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/job_routes.py` | 463 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/landuse_routes.py` | 75 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/landuse_routes.py` | 200 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/landuse_soils_routes.py` | 66 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/migration_routes.py` | 87 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/migration_routes.py` | 170 | `except Exception as exc:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/migration_routes.py` | 185 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 525 | `except Exception as exc:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 542 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 580 | `except Exception as exc:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 650 | `except Exception as exc:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 664 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 702 | `except Exception as exc:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 764 | `except Exception as exc:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 799 | `except Exception as exc:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 836 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 873 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 906 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/omni_routes.py` | 936 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/openet_ts_routes.py` | 50 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/openet_ts_routes.py` | 82 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/payloads.py` | 91 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/payloads.py` | 100 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/project_routes.py` | 245 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/project_routes.py` | 275 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/project_routes.py` | 303 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/project_routes.py` | 314 | `except Exception as exc:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/project_routes.py` | 324 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/project_routes.py` | 332 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/project_routes.py` | 337 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/project_routes.py` | 342 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/rap_ts_routes.py` | 99 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/rap_ts_routes.py` | 157 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/rhem_routes.py` | 49 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/rhem_routes.py` | 83 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/run_sync_routes.py` | 151 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/run_sync_routes.py` | 204 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/run_sync_routes.py` | 223 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/run_sync_routes.py` | 232 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/session_routes.py` | 437 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/soils_routes.py` | 68 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/soils_routes.py` | 111 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/swat_routes.py` | 70 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/swat_routes.py` | 91 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/swat_routes.py` | 119 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/swat_routes.py` | 159 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/swat_routes.py` | 187 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/swat_routes.py` | 217 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/treatments_routes.py` | 73 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/treatments_routes.py` | 152 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | 37 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | 134 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | 145 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | 173 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | 205 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | 265 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | 276 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | 317 | `except Exception as exc:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_climate_routes.py` | 64 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_climate_routes.py` | 94 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_climate_routes.py` | 110 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_disturbed_routes.py` | 58 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_disturbed_routes.py` | 99 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_disturbed_routes.py` | 127 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_disturbed_routes.py` | 154 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_helpers.py` | 94 | `except Exception as exc:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_huc_fire_routes.py` | 56 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_huc_fire_routes.py` | 64 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_huc_fire_routes.py` | 80 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_huc_fire_routes.py` | 114 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_huc_fire_routes.py` | 127 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/upload_huc_fire_routes.py` | 134 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/watershed_routes.py` | 475 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/watershed_routes.py` | 509 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/watershed_routes.py` | 539 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/watershed_routes.py` | 626 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/watershed_routes.py` | 654 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/watershed_routes.py` | 710 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/watershed_routes.py` | 740 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/watershed_routes.py` | 866 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/wepp_routes.py` | 151 | `except Exception as exc:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/wepp_routes.py` | 163 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/wepp_routes.py` | 182 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/wepp_routes.py` | 211 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/microservices/rq_engine/wepp_routes.py` | 262 | `except Exception:` | `boundary+allowlisted` | rq-engine API boundary with canonical contract handling; allowlisted. |
| `wepppy/rq/batch_rq.py` | 94 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 124 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 129 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 184 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 256 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 262 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 282 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 318 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 359 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 368 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 436 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 461 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 482 | `except Exception as meta_exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 491 | `except Exception as publish_exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 510 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/batch_rq.py` | 520 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 149 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 413 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 520 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 548 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 598 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 621 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 681 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 689 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 844 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 1464 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 1500 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 1562 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq.py` | 1605 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq_helpers.py` | 53 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq_manifest.py` | 103 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq_manifest.py` | 115 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq_manifest.py` | 172 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq_manifest.py` | 187 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq_manifest.py` | 208 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq_manifest.py` | 223 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq_manifest.py` | 229 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq_manifest.py` | 248 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/culvert_rq_manifest.py` | 263 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/exception_logging.py` | 39 | `except Exception as exc:  # pragma: no cover - best-effort logging only` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/exception_logging.py` | 58 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/interchange_rq.py` | 143 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/job_info.py` | 106 | `except Exception as exc:  # pragma: no cover - defensive guard` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/job_info.py` | 122 | `except Exception as exc:  # pragma: no cover - defensive guard` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/land_and_soil_rq.py` | 116 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/migrations_rq.py` | 114 | `except Exception as e:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/migrations_rq.py` | 139 | `except Exception as version_err:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/migrations_rq.py` | 161 | `except Exception as restore_err:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/migrations_rq.py` | 169 | `except Exception as e:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/migrations_rq.py` | 177 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/omni_rq.py` | 190 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/omni_rq.py` | 207 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/omni_rq.py` | 250 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/omni_rq.py` | 498 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/omni_rq.py` | 631 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/omni_rq.py` | 657 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/omni_rq.py` | 685 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/omni_rq.py` | 708 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/omni_rq.py` | 736 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/omni_rq.py` | 745 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/path_ce_rq.py` | 167 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/path_ce_rq.py` | 170 | `except Exception as status_exc:  # pragma: no cover - best-effort cleanup only` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 272 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 348 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 363 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 369 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 448 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 502 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 552 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 626 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 663 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 709 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 743 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 786 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 816 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 850 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 880 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 914 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 948 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 975 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 1026 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 1068 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 1135 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 1155 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 1217 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 1264 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 1278 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 1307 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq.py` | 1322 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_archive.py` | 149 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_archive.py` | 157 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_archive.py` | 238 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_archive.py` | 331 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_archive.py` | 344 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_delete.py` | 48 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_delete.py` | 162 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_delete.py` | 173 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_delete.py` | 191 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_delete.py` | 239 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_delete.py` | 278 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_delete.py` | 324 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/project_rq_fork.py` | 217 | `except Exception as exc:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/rq_worker.py` | 110 | `except Exception as exc:  # pragma: no cover - defensive logging` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/rq_worker.py` | 130 | `except Exception as exc:  # pragma: no cover - defensive logging` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/rq_worker.py` | 155 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/run_sync_rq.py` | 77 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/run_sync_rq.py` | 136 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/run_sync_rq.py` | 373 | `except Exception as e:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/run_sync_rq.py` | 459 | `except Exception as e:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/swat_rq.py` | 87 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/swat_rq.py` | 125 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/swat_rq.py` | 161 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/swat_rq.py` | 184 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/swat_rq.py` | 207 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq.py` | 242 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq.py` | 273 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq.py` | 304 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq.py` | 334 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq.py` | 369 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq.py` | 395 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq.py` | 485 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq.py` | 541 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq.py` | 640 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq.py` | 703 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_dss.py` | 125 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_dss.py` | 142 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_finalize.py` | 107 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_post.py` | 81 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_post.py` | 113 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_post.py` | 142 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_post.py` | 167 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_post.py` | 187 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_post.py` | 205 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_post.py` | 283 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_post.py` | 302 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_post.py` | 321 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_post.py` | 431 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_post.py` | 449 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_prep.py` | 33 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_prep.py` | 58 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_prep.py` | 76 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_prep.py` | 99 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_prep.py` | 119 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_prep.py` | 139 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_prep.py` | 159 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_prep.py` | 218 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/wepp_rq_stage_prep.py` | 242 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/weppcloudr_rq.py` | 50 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/weppcloudr_rq.py` | 112 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/rq/weppcloudr_rq.py` | 174 | `except Exception:` | `boundary+allowlisted` | RQ task/worker boundary with failure telemetry semantics; allowlisted. |
| `wepppy/weppcloud/routes/agent.py` | 93 | `except Exception as exc:  # pragma: no cover - enqueuing failure is rare` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py` | 43 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py` | 62 | `except Exception as e:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py` | 117 | `except Exception as e:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/batch_runner/batch_runner_bp.py` | 225 | `except Exception as err:  # pragma: no cover - defensive path` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/batch_runner/batch_runner_bp.py` | 320 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/bootstrap.py` | 66 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/bootstrap.py` | 91 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/bootstrap.py` | 110 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/bootstrap.py` | 124 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/bootstrap.py` | 143 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/bootstrap.py` | 157 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/bootstrap.py` | 177 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/combined_watershed_viewer.py` | 46 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/command_bar/command_bar.py` | 71 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/command_bar/command_bar.py` | 100 | `except Exception as exc:  # pragma: no cover - defensive logging` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/command_bar/command_bar.py` | 133 | `except Exception:  # pragma: no cover - defensive` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/command_bar/command_bar.py` | 197 | `except Exception as exc:  # pragma: no cover - defensive logging` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/command_bar/command_bar.py` | 237 | `except Exception as exc:  # pragma: no cover - defensive logging` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/fork_console/fork_console.py` | 34 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/huc_fire.py` | 64 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/jsoncrack.py` | 128 | `except Exception as e:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/locations.py` | 83 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 189 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 218 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 266 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 333 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 364 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 391 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 428 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 486 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 520 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 558 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 587 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 600 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | 629 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` | 224 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` | 242 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` | 301 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` | 309 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` | 135 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` | 159 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` | 184 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` | 208 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` | 268 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` | 285 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` | 296 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/observed_bp.py` | 45 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/observed_bp.py` | 52 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/omni_bp.py` | 142 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/omni_bp.py` | 159 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/omni_bp.py` | 180 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/omni_bp.py` | 194 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/omni_bp.py` | 221 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/omni_bp.py` | 321 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/path_ce_bp.py` | 111 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 212 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 222 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 233 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 284 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 292 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 302 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 326 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 358 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 368 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 388 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 513 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 548 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 579 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | 605 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/rangeland_bp.py` | 195 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/rangeland_bp.py` | 240 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/rangeland_bp.py` | 258 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/rangeland_cover_bp.py` | 92 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/rhem_bp.py` | 33 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/rhem_bp.py` | 59 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/rhem_bp.py` | 87 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/rhem_bp.py` | 115 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/rhem_bp.py` | 130 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/soils_bp.py` | 61 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/soils_bp.py` | 106 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/soils_bp.py` | 126 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/soils_bp.py` | 153 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/treatments_bp.py` | 37 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/unitizer_bp.py` | 28 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/unitizer_bp.py` | 51 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/unitizer_bp.py` | 73 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/watar_bp.py` | 152 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/watar_bp.py` | 164 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/watar_bp.py` | 176 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/watar_bp.py` | 195 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/watar_bp.py` | 226 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/watar_bp.py` | 253 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/watar_bp.py` | 270 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/watar_bp.py` | 334 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 46 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 56 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 87 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 175 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 251 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 393 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 398 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 473 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 520 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 538 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 556 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 607 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 634 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 641 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 648 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 720 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 844 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 895 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 902 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 945 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 956 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 1133 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 1150 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 1195 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 1214 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 1239 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/pivottable.py` | 536 | `except Exception as e:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/readme_md/readme_md.py` | 156 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/readme_md/readme_md.py` | 314 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/readme_md/readme_md.py` | 325 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/readme_md/readme_md.py` | 368 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/readme_md/readme_md.py` | 385 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/readme_md/readme_md.py` | 405 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/recorder_bp.py` | 46 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/recorder_bp.py` | 80 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/rq/info_details/routes.py` | 153 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 330 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 338 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 349 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 361 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 494 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 593 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 647 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 839 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 869 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 928 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/run_sync_dashboard/run_sync_dashboard.py` | 65 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/stats.py` | 30 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/stats.py` | 38 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/stats.py` | 59 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/stats.py` | 67 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/stats.py` | 84 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/stats.py` | 91 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/stats.py` | 108 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/stats.py` | 115 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/user.py` | 255 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/user.py` | 409 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/user.py` | 463 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/user.py` | 508 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/user.py` | 527 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/user.py` | 560 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/user.py` | 610 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/user.py` | 688 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/user.py` | 714 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/user.py` | 734 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloud_site.py` | 120 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloud_site.py` | 414 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloud_site.py` | 442 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloud_site.py` | 465 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloudr.py` | 102 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloudr.py` | 265 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloudr.py` | 280 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloudr.py` | 331 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloudr.py` | 356 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloudr.py` | 392 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloudr.py` | 419 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloudr.py` | 469 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloudr.py` | 531 | `except Exception as exc:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloudr.py` | 544 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
| `wepppy/weppcloud/routes/weppcloudr.py` | 584 | `except Exception:` | `boundary+allowlisted` | HTTP route boundary with telemetry; allowlisted. |
