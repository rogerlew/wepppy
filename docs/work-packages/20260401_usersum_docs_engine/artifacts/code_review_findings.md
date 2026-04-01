# Code Review Findings - Usersum Docs Engine

Review date: 2026-04-01  
Reviewer: Codex (self-review, risk-focused)  
Scope: usersum contracts/tooling/runtime/layout/search changes in this package.

## Findings (ordered by severity)

1. Medium - Broad exception boundary added in usersum role detection.
File: `wepppy/weppcloud/routes/usersum/usersum.py`  
Detail: `_caller_max_role()` used `except Exception`, which violated changed-file broad-catch gate and could mask runtime defects unrelated to optional import handling.  
Resolution: narrowed to `except ImportError` and reran broad-exception enforcement.

2. Medium - PostgreSQL search backend instance recreated per request.
File: `wepppy/weppcloud/routes/usersum/usersum.py`  
Detail: backend recreation reset `_last_synced_signature`, causing unnecessary `ensure_synced()` write work and avoidable load.  
Resolution: introduced `_cached_postgres_search_backend(db_url)` with `@lru_cache(maxsize=2)` and routed backend creation through cache.

3. Medium - Canonical usersum links ignored site prefix in proxied deployments.
Files: `wepppy/weppcloud/routes/usersum/usersum.py`, usersum templates  
Detail: canonical links used raw `/usersum/...` paths, which broke under `/weppcloud` prefixed deployments.  
Resolution: switched route URL generation to `url_for_run(...)` and added regression coverage for prefixed links.

## Final Disposition

- High findings: 0
- Medium findings: 3 (all resolved)
- Low findings: 0
- Unresolved medium/high: none

## Evidence

- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> PASS
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py tests/weppcloud/routes/test_usersum_docs_contracts.py tests/weppcloud/routes/test_usersum_docs_index.py --maxfail=1` -> PASS
