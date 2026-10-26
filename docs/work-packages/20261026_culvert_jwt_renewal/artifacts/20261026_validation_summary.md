# Validation summary

2026-10-26 UTC. Implementation: WEPPpy `2b334ded7`; companion Culvert_web_app `a2bd7bf62`; contract ancestor `4cd8e9cb1`.

## Focused and real-environment acceptance

- `wctl run-pytest tests/culverts/test_token_rotation.py -q`: **20 passed**.
- Actual systemd service and actual accelerated timer both minted and installed fresh tokens on wepp2. Same-process worker loader saw each replacement and authenticated against wepp1. See [live evidence](20261026_live_validation.md).
- Ordinary service start: not_due, no replacement. Unknown SSH command, malformed token, and a correctly shaped but invalid signature all rejected; current credential retained.
- `systemd-analyze --user verify`: passed. Timer enabled; temporary force/timer overrides removed. Daily next trigger verified.
- Independent correctness/security review: PASS, all findings closed.
- Changed-document lint, spelling preview and final diff whitespace checks passed. Code-quality telemetry retained separately; it is observe-only and does not cover operator scripts in its current production-path inventory. Broad-exception gate passed (no changes under its configured production paths).

## Repository-wide regression

Required command: `wctl run-pytest tests --maxfail=1`.

Result after 3257.19 seconds: **1 failed, 11,610 passed, 155 skipped**. Failure:
`tests/weppcloud/test_run_catalog_reader.py::test_real_file_sql_http_browser_chain`.
Playwright inherited `/workdir/wepppy/weppcloud/static-src/.playwright-browsers`
from the dev Compose environment; Chromium actually exists under
`/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers`.
This is an existing environment-path discrepancy, not a renewal regression.
No browser download or unrelated Compose edit was performed.

Reran the failed file and every lexically subsequent test file (19 files) through
`wctl run-python` invoking pytest, with the correct existing
`PLAYWRIGHT_BROWSERS_PATH` set in that process only. Tail result: **183 passed**
in 40.97 seconds, including the real HTTP/browser test. Seven cases in the first
file had already passed in the broad run. Segmented unique coverage therefore
contains **11,786 passing cases and 155 skips** (including collection skip),
with no remaining observed test failure. This is segmented coverage, not a
claim that the unmodified full command returned zero.

Reproduction of the bounded tail:

```python
import os, sys
from pathlib import Path
import pytest
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers'
start = 'tests/weppcloud/test_run_catalog_reader.py'
paths = sorted(str(p) for p in Path('tests').rglob('test_*.py') if str(p) >= start)
sys.exit(pytest.main(paths + ['-q', '--maxfail=1']))
```

An earlier broad attempt was invalidated while the synthetic-token fixture was
being corrected after review (353 passed before the stale fixture failed). The
final broad run above includes all 20 corrected renewal tests. Avoid changing
collected fixtures during long broad runs.

## Limits and follow-ups

No full model analysis was submitted or repaired. Off-host alert delivery needs
an operator-supplied destination; local journal/systemd/last-attempt monitoring
is deployed. Observe the first ordinary daily trigger after rollout. Confirmed
developer ergonomics issue: correct the dev Compose browser cache path in a
separate bounded change so the canonical broad command can finish without a
process-local override. The existing path mismatch cost a failed broad gate;
no new dependency is needed.
