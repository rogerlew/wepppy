# Disturbed lookup runbook tracker

## Local validation on 2026-11-23 UTC

| Measure | Original | Refactored |
| --- | ---: | ---: |
| Lines in runbook.py | 1,242 | 589 |
| Lines in execute_live_runbook | 768 | 77 |
| Longest function in affected runbook modules | 768 | 122 |
| Assertions passing in a successful replay | 19 | 19 |

Four cases exercised the public entry point using an autospecced client and the repository's hillslope management fixture. The success case exercised both lookup variants. A failed prep request and a truncated patch readback exercised failure attribution. An incorrect generated soil value exercised the distinction between a completed job and a passing scientific assertion.

For each case the baseline and candidate had identical SHA-256 digests for the ordered client calls with sorted keyword arguments, the generated JSON, and the generated Markdown. The replay fixed timestamps and the fork ID. The successful JSON digest was `c51939966285c5dcff410d6da323c45dd02b4fd2d7a447335052baeb859d35ba`. The comparison used baseline checkout `d44ddfbbd` and isolated wctl receipts `0cb49b2e5b4341cdb0e2f3b8a9706cc0` and `f880a7b4b8e844f4891984ed1211a37d`.

## Reproduce the scoped tests

```bash
wctl run-pytest --profile python -- \
  tests/nodb/mods/disturbed/test_disturbed_lookup_runbook_replay.py \
  tests/nodb/mods/disturbed/test_disturbed_lookup_live_e2e.py -q -rs
```

Final scoped validation passed four replay tests. The live determinism test skipped under its opt-in gate. The configured service returned HTTP 503 on two login-page probes. Validation establishes local orchestration and artifact parity. Real fork and queue execution remain unverified for this change.

See the [completed ExecPlan](prompts/completed/implementation_execplan.md).
