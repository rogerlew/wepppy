# Project RQ read-only refactor tracker

Opened 2026-11-23 UTC on local master at `9e2f2183e`. The focused gate is
`tests/rq/test_project_rq_readonly.py`. Run the repository-wide pytest gate
and record its outcome separately.

## Validation on 2026-11-24 UTC

The baseline passed all six existing read-only tests. The candidate passed
all 78 cases in the read-only and mutation-guard modules in isolated wctl run
`6ac7e0281d8e41d68ecbc7aa58d50b65`. The new round trip read the filename
and size from the real SQLite manifest, then verified its removal. Two other
cases verified rollback when manifest creation or removal failed its file check.
The worker went from 120 to 87 lines. An AST comparison found all 62 other
existing module functions identical. The changed-code broad-exception gate passed.

The broad preflight passed with matching local browser and parser runtimes.
A separate invocation in that same candidate container reproduced an existing
failure in `tests/weppcloud/routes/test_team_bp.py::test_adduser_errors_when_user_unknown`.
The route returned “WEPPcloud” and the assertion expected “WeppCloud”.
The same case failed on local master before integration (wctl receipt
`a668be4f05ef4af3a442745f1322674a`). With that failure confirmed, the
maintainer stopped the broad run after 378 passes and 28 skips (receipt
`0062e0b368634dff98d3da58564885fc`). Full-suite validation is incomplete.
