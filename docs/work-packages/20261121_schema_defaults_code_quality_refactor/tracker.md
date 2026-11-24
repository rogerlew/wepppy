# Schema defaults refactor tracker

## Verified

Production commit 254ed7b78 contains the refactor. Commit dad9a99a1 deduplicates test fixture setup. The production router now has 540 source lines, a longest function of 37 lines and maximum cyclomatic complexity of six. Across all 17 production files, the respective maxima are 540, 130 and 22. All three route metrics improved. The final analyzer reported zero worsened metrics across 19 changed files. The existing 1,691-line schema-defaults test module remains above the red size threshold and shrank by ten source lines.

All ten published OpenAPI paths and 435 registered-app responses matched the baseline for a legacy run, stored US capabilities and projected European capabilities. All 132 focused tests passed on the frozen production commit. The independent source review accepted the shared admission helper, operation assembly and artifact discovery. The endpoint inventory, route checklist, changed-file broad-exception gate and scoped Vulture check passed.

[Execution plan](prompts/completed/implementation_execplan.md) · [Quality metrics](artifacts/quality_metrics.json) · [HTTP parity receipt](artifacts/discovery_parity.json) · [Correctness review](artifacts/correctness_review.md)

## Full-suite validation

On the first attempt the validation image's native PRISM library lacked the raw_tdmean_c keyword. A read-only mount supplied the paired py312 cli_revision_rust.so from native commit c42f58f7d1e3b62b9d2e97da9d9509dd80e31bb5. The validation image and parser binaries stayed local to the disposable runner.

The final frozen candidate dad9a99a1f246eea02a19980652016a344599837 passed all 132 focused tests and stub hygiene. Full pytest reported 14,869 passed, 533 skipped, 99 deselected and 5,968 warnings in 3,670 seconds. The wctl receipts report passed with stable source and runtime. See the [validation record](artifacts/validation.md) for invocation and runtime details. Closed locally on 2026-11-21 (Pacific).
