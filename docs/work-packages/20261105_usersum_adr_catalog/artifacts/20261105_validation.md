# ADR catalog validation

Date: 2026-11-05 UTC. Contract ancestor: `0b804f1ff`.

## Focused acceptance

`wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1`

Result: **100 passed**, 4 existing dependency warnings, 16.90 seconds.
The initial new test failed before implementation (catalog absent). An intermediate
fixture used a boolean where the existing strict-manifest configuration expects
a string; correcting the fixture preserved the existing route contract.

Generated Flask response HTML was read back for all **138 repository ADRs**.
The test compares the complete rendered Markdown body, checks every catalog link
exactly once, and verifies the real ADR-0028/ADR-0029 date inversion. Temporary
source-tree tests cover additions, edits, removals, duplicate IDs, invalid/missing
dates, metadata variants, empty/missing directories, read failures, invalid UTF-8,
symlinks, traversal, escaped titles, anonymous/elevated readers, site prefixes,
strict source-manifest configuration, cross-ADR anchors/query strings, raw/GitHub
links and manifest precedence. No generated index rebuild is used.

Independent correctness and security reviews passed after the inline Review Date
finding was closed. See `20261105_implementation_review.md`.

## Additional gates

- `wctl run-npm lint`: passed.
- `wctl run-npm test`: 122 suites, 1,047 tests passed.
- `wctl doc-lint --path <changed doc>`: passed for ADR README, Usersum instructions,
  specification and work-package docs.
- `git diff --check`: passed.
- Broad-exception changed-file enforcement: passed, no broad handlers added.
- Observe-only code quality tool completed; radon unavailable and tool did not
  report an unstaged changed-file comparison. No complexity claim is inferred.

## Broad Python coverage

`wctl run-pytest tests --maxfail=1` was interrupted intentionally after **405
passed, 27 skipped**, 176.75 seconds, while running the unrelated slow native
100-year disturbed-model matrix. This is **not a complete full-suite pass**.
The nearest WEPPcloud instructions permit documenting a skipped full gate; the
bounded Help change uses the broad suite excluding explicitly slow tests instead.

`wctl run-pytest tests -m 'not slow' --maxfail=1`: interrupted after **3,886
passed, 31 skipped, 1,073 deselected**, 417.31 seconds. This broader attempt also
spent substantial time in unrelated model runtime tests despite the slow-test
exclusion. No failures were observed, but both broad runs are incomplete. The
focused workflow gates and live readback below are complete.

## Operational scope

No production deployment, migrations, role changes or project data mutations.
The operator reported a forest Help HTTP 500 during implementation. Logs showed
`BuildError` for `usersum.adr_catalog`: bind-mounted templates were fresh while
Gunicorn workers still used the old Python route table. At 19:17:32 UTC, sent HUP
to the verified forest Gunicorn master PID 7 via `wctl exec`; four replacement
workers loaded the new routes. This preserved the container and test sessions.

External HTTPS readback through `https://forest.tail305ec9.ts.net/weppcloud`:
Help index, ADR catalog, all **138 linked ADR documents**, and existing Getting
Started document returned HTTP 200. Catalog links were unique; every ADR detail
response contained rendered headings and GitHub/raw-source links. Local live
readback artifacts: `/tmp/usersum-adr-live-help.html`,
`/tmp/usersum-adr-live-index.html`, `/tmp/usersum-adr-live-results.json`.

Failure-class assessment: all Help pages share the new sidebar link and were
exposed to the stale endpoint table; the index also had its own link. Reloading
all web workers repaired both consumers. Durable rollout guidance is in Usersum
`AGENTS.md` **Development rollout** and specification **Automatic ADR catalog**.
Subsequent ADR source changes require no index generation or worker reload.
