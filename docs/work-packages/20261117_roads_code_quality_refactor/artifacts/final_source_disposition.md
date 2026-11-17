# Final formatting disposition

After native/project acceptance, `_constants.py` lost two trailing empty lines to
satisfy `git diff --check`. No executable token changed; AST comparison is exact.

- Tested SHA-256: `a44595427152e3ab93d80f4d9cefe940430d7f7b732ab596ace9fd2c53f10561`.
- Final SHA-256: `545dc010950acea4dda274fc7cf2f81e78c3fb43f84c34dafda2da9eb7b2ecde`.

All other Roads production and harness files retain their tested bytes. Original
native/project receipts remain unchanged and identify the source actually tested;
they are not rewritten to claim this formatting occurred before execution. The
staleness ledger explicitly records this subsequent formatting-only review.
Final focused checks passed 413 tests, one skipped, in 38.12 seconds
(`focused-aligned-candidate-format-final.log`). No scientific rerun is needed for an
AST-identical removal of empty trailing lines.

Retained console log copies strip trailing whitespace only; their receipt records
both original and normalized digests. Original runtime logs remain available.

The final-format historical publication gate also passed all three tests
(`publication-format-final.log`, 9.53 seconds), preserving original stale artifacts.
