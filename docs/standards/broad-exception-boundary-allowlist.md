# Broad Exception Boundary Allowlist

Canonical allowlist for deliberate broad exception boundaries.

Use this file for approved boundary handlers that should be excluded from `tools/check_broad_exceptions.py` findings and changed-file enforcement.

## Entry requirements

- `Allowlist ID`: stable identifier for audit/review.
- `File` + `Line`: exact source location (line numbers are used by the checker).
- `Handler`: one of ``except Exception``, ``except BaseException``, ``except:``.
- `Owner`: accountable subsystem/team.
- `Rationale`: why broad boundary is currently required.
- `Expires on`: revisit deadline (`YYYY-MM-DD`) or explicit no-expiry policy.

## Allowlist entries

| Allowlist ID | File | Line | Handler | Owner | Rationale | Expires on |
|-------------|------|-----:|---------|-------|-----------|------------|
| `BEA-20260222-001` | `wepppy/microservices/rq_engine/bootstrap_routes.py` | 154 | `except Exception` | rq-engine maintainers | Route auth boundary must log and return canonical auth error payloads without leaking raw exceptions. | `2026-05-31` |
| `BEA-20260222-002` | `wepppy/microservices/rq_engine/job_routes.py` | 268 | `except Exception` | rq-engine maintainers | Polling boundary must audit failures and preserve traceback-bearing canonical 500 payloads. | `2026-05-31` |
| `BEA-20260222-003` | `wepppy/microservices/rq_engine/omni_routes.py` | 540 | `except Exception` | rq-engine maintainers | Enqueue boundary keeps canonical error envelope while logging queue/Redis faults. | `2026-05-31` |
| `BEA-20260222-004` | `wepppy/microservices/rq_engine/fork_archive_routes.py` | 488 | `except Exception` | rq-engine maintainers | Archive enqueue boundary preserves canonical API contract on operational failures. | `2026-05-31` |
| `BEA-20260222-005` | `wepppy/rq/project_rq.py` | 272 | `except Exception` | rq worker maintainers | Worker boundary must publish `EXCEPTION` telemetry and re-raise so RQ status semantics stay intact. | `2026-05-31` |
| `BEA-20260222-006` | `wepppy/nodb/base.py` | 1301 | `except Exception` | NoDb maintainers | Redis cache mirror writes are best-effort and must not block `dump_and_unlock` lock-release flow. | `2026-06-30` |
| `BEA-20260222-007` | `wepppy/nodb/base.py` | 1312 | `except Exception` | NoDb maintainers | `update_last_modified` mirror is best-effort to avoid lock-retention regressions on dump. | `2026-06-30` |
| `BEA-20260222-008` | `wepppy/nodb/base.py` | 1323 | `except Exception` | NoDb maintainers | Redis `last_modified` mirror is best-effort and must not fail the persistence boundary. | `2026-06-30` |
| `BEA-20260222-009` | `wepppy/query_engine/app/server.py` | 532 | `except Exception` | query-engine maintainers | HTTP activation boundary logs and returns stable 500 JSON error envelope. | `2026-05-31` |
| `BEA-20260223-010` | `wepppy/weppcloud/routes/user.py` | 525 | `except Exception` | WEPPcloud maintainers | Per-run metadata load boundary in `_build_meta` must skip corrupt/incomplete run workspaces without turning list responses into global 500s; failures are logged with context. | `2026-06-30` |
| `BEA-20260223-011` | `wepppy/weppcloud/routes/user.py` | 558 | `except Exception` | WEPPcloud maintainers | Per-run metadata load boundary in `_build_map_meta` must skip corrupt/incomplete run workspaces without turning list responses into global 500s; failures are logged with context. | `2026-06-30` |
