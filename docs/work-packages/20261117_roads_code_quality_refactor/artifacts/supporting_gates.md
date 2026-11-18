# Supporting candidate gates

Production checkpoint: `5ef264810`; review hashes are retained in the QA and
security manifests. The only later production delta removes two trailing empty
lines from `_constants.py`, recorded below and in `final_source_disposition.md`.

- Final focused candidate run passed 413 tests, one skipped, in 38.39 seconds
  (`/tmp/roads-refactor-validation/focused-aligned-candidate-final.log`).
- Historical publication source-ledger checks passed (3 tests); accepted RUPC
  provenance drift and refactor drift are explicit, while original reports,
  results and execution provenance remain unchanged and stale.
- Four mixed-execution and sanitized-diagnostic boundary tests passed.
- Stub completeness passed via the guarded candidate container (`stub-surface.log`).
- Configured Vulture gate passed using the existing shared virtualenv executable
  `/home/workdir/wepppy/.venv/bin/vulture`, with the candidate checkout as cwd.
- Broad-exception changed-file enforcement against `origin/master` passed;
  that comparison includes 74 files from earlier accepted work. The package-only
  comparison passed over its 18 production files. Actual handler count remains
  19 before and after; added boundary annotations are not handler removal.
- Quality observability against `origin/master` completed with Radon using
  `/usr/bin/python`; reports are `/tmp/roads-quality.origin-master.json` and `.md`.
  Package-only qualified measurements are in `quality_metrics.json` and `.md`.

## Current qualification - 2026-11-18 UTC

Canonical-environment focused validation passes 413 tests, one skipped, in
38.10 seconds (`focused-canonical-fixture-20261117c.log`). The earlier focused
receipts below are historical and used a global retention-root override.
Final-source native execution matches all 6,192 raw files across 516 profiles;
all five retained full-project outcomes pass final-source admission without
changing saved state. Native and project evidence is complete.

The complete 6,853-item broad suffix diagnostic reports 6,365 passes, 208
failures, 272 runtime skips and eight setup errors, plus one collection skip.
It ran in 967.84 seconds. The run is unsuccessful. Source monitoring also found
one management JSON fixture rewritten by a test; its original and generated
bytes are retained for review and restoration. Baseline probes and bounded
module reruns are recorded separately. Neither diagnostic completion nor
baseline attribution is a claim that the broad regression gate passed.

Final stub hygiene passes on source checkpoint `5812caa02` using the canonical
`tools/check_stubs.py` command in a checkout-guarded container. The initial
invocation used a nonexistent script path and ran no checks; both command logs
are retained (`final-stub-hygiene.log`, `final-stub-hygiene-corrected.log`).

## Broad-suite fixture isolation

The initial broad run stopped after 270 passed and 27 skipped because an ordinary
archive fixture inherited vector-retention filesystem settings but its fake Redis
lacked `eval`. The same MACA test failed on immutable baseline `96555f2f9`.
Clearing the two retention identity/root environment variables in the ordinary
archive fixture preserves explicit configuration in the dedicated retention tests.
The scoped archive regression run passed 73 tests. No production archive behavior
changed. Logs: `/tmp/roads-refactor-validation/broad-final.log`,
`broad-baseline-maca.log`, and `archive-fixture-isolation.log`.

The broad rerun adds a read-only shared Git metadata mount so repository checks
can resolve the isolated worktree. Candidate checkout identity still passes the
canonical nonce guard. The exact reusable drivers and hashes are retained in
`final_gate_scripts_receipt.json`. Final broad completion is recorded separately.

The second broad run stopped after 1,769 passed and 41 skipped on the analogous
fork-route fake Redis (`sismember` absent). The unchanged baseline reproduced it
(`broad-baseline-fork.log`). The existing route autouse fixture now clears the
same two inherited settings; dedicated retention tests still declare their own
settings after setup. All 65 route tests pass (`fork-fixture-isolation.log`), and
independent QA accepted the bounded test-only change. Commit: `43cb4e78f`.
The third full broad run is `broad-final-v3.log`, with fresh basetemp
`/tmp/roads-refactor-validation/broad-candidate-20261117c`.

Final formatting checkpoint: `36ce30c1e`. During broad v3, `_constants.py` lost
only two trailing empty lines; independent AST comparison confirms unchanged
executable content. The exact pre-formatting native/project source receipts stay
immutable, with the later delta recorded in `final_source_disposition.md`.
Final-format focused checks passed 413 tests, one skipped (38.12 seconds), and
publication checks passed three tests (9.53 seconds). No other Roads source bytes
changed after the native/project runs.

The final whole-module replay passes all 391 selected tests in 55.79 seconds
(one separate collection skip). All source, runtime artifact, environment,
script and selection checks are unchanged. It reruns 17 complete modules with
read-only existing parser binaries, a short temporary path, and the two reviewed
retention-fixture corrections. This qualifies those module results; the remaining
broad failures and the original v5 source-drift rejection remain explicit.
