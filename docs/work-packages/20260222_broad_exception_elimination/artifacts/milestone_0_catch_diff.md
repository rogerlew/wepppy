# Milestone 0 Catch Diff

## Scope

Milestone 0 introduced tooling and documentation only:
- `tools/check_broad_exceptions.py`
- `tests/tools/test_check_broad_exceptions.py`
- baseline + allowlist artifacts

No production modules under `wepppy/` or `services/` were modified in this milestone.

## Before/After Broad-Catch Counts

Checker source: `python3 tools/check_broad_exceptions.py --json`

- Before (baseline snapshot):
  - scanned files: `705`
  - unsuppressed broad catches: `1120`
  - bare catches: `96`
  - `except Exception`: `1024`
  - `except BaseException`: `0`
  - suppressed broad catches: `6`
- After Milestone 0:
  - scanned files: `705`
  - unsuppressed broad catches: `1120`
  - bare catches: `96`
  - `except Exception`: `1024`
  - `except BaseException`: `0`
  - suppressed broad catches: `6`

Delta: `0` (expected; no production catch edits in Milestone 0).

## Commands Run

- `python3 tools/check_broad_exceptions.py --json` -> pass (report generated; non-zero exit expected while findings exist).
- `python3 -m pytest tests/tools/test_check_broad_exceptions.py --maxfail=1` -> pass (`3 passed`).
- `wctl run-pytest tests/tools/test_check_broad_exceptions.py --maxfail=1` -> blocked (Docker socket unavailable in this execution environment).

## Residual Risks / Deferred Items

- Checker is report-mode only in Milestone 0; changed-file enforcement is deferred to Milestone 7.
- Boundary allowlist has template entries only; concrete approved boundaries are deferred to later milestones.
