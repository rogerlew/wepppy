# Batch Runner WATAR-Only Retry Correctness Review

**Date**: 2026-08-06 UTC

**Reviewer**: Codex primary agent, fresh diff-level review after implementation

**Scope**: WATAR-only reuse tests, durable failure reporting test, generated
evidence script, and Batch Runner documentation

## Disposition

No unresolved correctness findings remain. This execution context did not use a
separate reviewer agent; the disposition combines a fresh patch inspection,
isolated test-process evidence, real-artifact execution, the complete NoDb
suite, and the full repository test suite.

## Review Checks

- The incident regression exercises `BatchRunner.run_batch_project`, not only
  the station comparison helper.
- Every non-WATAR directive is disabled. The inert controller doubles have no
  build methods, so an accidental climate or WEPP rebuild fails the test.
- The test records SHA-256 values for persisted climate and representative WEPP
  artifacts before execution and asserts the complete mapping is unchanged.
- The test asserts the climate and WEPP prerequisite timestamps are preserved
  and only the WATAR timestamp is added.
- Existing negative coverage still rejects explicit station changes, foreign
  enum constructors, malformed station modes, and material climate drift.
- The failure regression proves the exact WATAR prerequisite exception is
  written to failed `run_metadata.json`, returned as `(False, elapsed)`, and
  followed by the normal leaf-completion trigger.
- Existing finalizer coverage proves failed durable state produces
  `BATCH_RUN_COMPLETED_WITH_FAILURES` while the compatibility completion event
  remains present.
- The generated evidence script uses a disposable copy, forces burn class only
  in that process, invokes real Ash/AshPost through Batch Runner, and verifies
  real output parquets plus immutable climate/WEPP inputs.
- No queue dependency or production implementation changed, so the RQ graph
  and security-review gates are not activated.

## Validation Reviewed

- Focused modules: 42 passed, 8 warnings in 19.56 seconds.
- NoDb suite: 1,560 passed, 26 skipped, 28 warnings in 163.81 seconds.
- Full suite: 5,897 passed, 61 skipped, 1,048 warnings in 677.54 seconds.
- Broad exception delta: +0, pass.
- Documentation lint and `git diff --check`: pass.
- Generated evidence: 3 WATAR hillslope parquets, 5 AshPost parquets, unchanged
  climate/WEPP hashes and prerequisite timestamps.
