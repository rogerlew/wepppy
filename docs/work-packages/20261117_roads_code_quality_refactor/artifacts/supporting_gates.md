# Supporting candidate gates

Production checkpoint: `5ef264810`; review hashes are retained in the QA and
security manifests. No production changes followed that checkpoint.

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
