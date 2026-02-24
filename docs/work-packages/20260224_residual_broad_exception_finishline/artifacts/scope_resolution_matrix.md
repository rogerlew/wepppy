# Scope Resolution Matrix — Residual Broad-Exception Finish Line

Date: 2026-02-24

## Baseline to Postfix Mapping

| Baseline finding | Final disposition | Evidence |
|---|---|---|
| `wepppy/query_engine/app/mcp/router.py:177` (`except Exception`) | Narrowed to `except (OSError, ValueError)` in `_load_catalog_metadata` | [wepppy/query_engine/app/mcp/router.py](/workdir/wepppy/wepppy/query_engine/app/mcp/router.py:177) |
| `wepppy/query_engine/app/mcp/router.py:298` (`except Exception`) | Narrowed to `except (OSError, ValueError)` in `_prepare_query_request` | [wepppy/query_engine/app/mcp/router.py](/workdir/wepppy/wepppy/query_engine/app/mcp/router.py:298) |
| `wepppy/query_engine/app/mcp/router.py:700` (`except Exception`) | Narrowed to `except (OSError, ValueError)` in `get_catalog` | [wepppy/query_engine/app/mcp/router.py](/workdir/wepppy/wepppy/query_engine/app/mcp/router.py:700) |
| `wepppy/query_engine/app/mcp/router.py:918` (`except Exception`) | Retained as true boundary (`context_unavailable`) and allowlist-synced | `BEA-20260224-TM-0173` -> line `920` in [allowlist](/workdir/wepppy/docs/standards/broad-exception-boundary-allowlist.md:759) |
| `wepppy/query_engine/app/mcp/router.py:930` (`except Exception`) | Retained as true boundary (`execution_failed`) and allowlist-synced | `BEA-20260224-TM-0174` -> line `932` in [allowlist](/workdir/wepppy/docs/standards/broad-exception-boundary-allowlist.md:760) |
| `wepppy/query_engine/app/mcp/router.py:996` (`except Exception`) | Retained as true boundary (`activation_failed`) and allowlist-synced | `BEA-20260224-TM-0175` -> line `998` in [allowlist](/workdir/wepppy/docs/standards/broad-exception-boundary-allowlist.md:761) |
| `wepppy/query_engine/app/mcp/router.py:1084` (`except Exception`) | Narrowed to `except (OSError, ValueError)` in `get_prompt_template` fallback | [wepppy/query_engine/app/mcp/router.py](/workdir/wepppy/wepppy/query_engine/app/mcp/router.py:1084) |
| `wepppy/weppcloud/app.py:197` (`except Exception`) | Retained as true boundary in `Run.meta` and allowlist-synced | `BEA-20260224-TM-0326` -> line `197` in [allowlist](/workdir/wepppy/docs/standards/broad-exception-boundary-allowlist.md:911) |

## Result

- Baseline in-scope unresolved findings: `8`
- Postfix in-scope unresolved findings: `0`
- Net in-scope reduction: `-8`
