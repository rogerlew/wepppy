# Port the SOIL OFE fix through the canonical WEPP default branch

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Restore release-lineage correctness after the watershed SOIL OFE-width fix was
made and released from the non-default HBP modernization branch. The canonical
`wepp_260430_negmeltfix_comparator` branch will gain the bounded `I2` to `I5`
format correction, release guidance will require resolving `origin/HEAD` before
source or build work, and WEPPpy will vendor and select the resulting legacy
ASCII pass release.

## Progress

- [x] (2026-08-03 04:36Z) Confirmed `origin/HEAD` resolves to
  `wepp_260430_negmeltfix_comparator` and identified `b517d0ab` as the missing
  bounded source fix.
- [x] (2026-08-03 04:40Z) Ported the source correction, regression, sidecar
  tooling, and agent release guardrail on the default branch in `f24c957e`.
- [x] (2026-08-03 04:48Z) Built and validated legacy-pass `wepp_260803`; source
  and release binaries are byte-identical and release commit `2444b521` is
  pushed to the remote-default branch.
- [x] (2026-08-03 04:50Z) Vendored the exact binaries, paired branch-bearing
  sidecars, release notes, and change log into WEPPpy.
- [x] (2026-08-03 05:02Z) Selected `wepp_260803` in
  `disturbed9002_wbt.cfg`; verified sidecar-driven `legacy_ascii` inference,
  provenance, host smoke, and 65 focused WATAR/ash/culvert/runner tests.
- [x] (2026-08-03 05:27Z) Completed the final full WEPPpy gate: 5,803 passed
  and 61 skipped. Commit and push follow this plan closeout.

## Surprises & Discoveries

- Observation: The checkout named `wepp-forest_260430_baseline` has `master`
  checked out, while the Git remote default is a different branch.
  Evidence: `git symbolic-ref refs/remotes/origin/HEAD` returns
  `refs/remotes/origin/wepp_260430_negmeltfix_comparator`.
- Observation: The refreshed default-branch `wepp_260725` already contains the
  other selected July fixes but retains `I2` for watershed SOIL OFE identifiers.
  Evidence: both `src/watbal.for` and `src/watbal_hourly.for` contain format
  `1100 format (1x,i2,...)` at default-branch revision `8af9b967`.
- Observation: Replacing the vendored source change log discarded historical
  WEPPpy release links and failed the usersum route contract.
  Evidence: the first full WEPPpy gate stopped at 94% with 5,475 passing tests;
  preserving the prior log and prepending the new entry fixed the focused test.

## Decision Log

- Decision: Port only the SOIL OFE format widening from `b517d0ab`; do not merge
  or cherry-pick the HBP modernization history.
  Rationale: The defect is a two-token output-contract correction and the
  operator explicitly requires the negative-melt default lineage.
  Date/Author: 2026-08-03 / Codex, per Roger Lew.
- Decision: Cut a new release tag rather than overwrite `wepp_260725`.
  Rationale: Binary names must identify immutable source/build provenance and
  avoid repeating the ambiguous release lineage that caused this incident.
  Date/Author: 2026-08-03 / Codex.

## Outcomes & Retrospective

The source fix and immutable legacy-pass release are complete and pushed. The
new paired sidecars state the default source branch and exact source commit,
and WEPPpy selects the release without an HBP override. WEPPpy provenance and
host smoke passed, 65 focused runner/WATAR/ash/culvert tests passed, and the
full suite passed with 5,803 tests and 61 skips.

## Context and Orientation

The WEPP source repository is available through the clean linked worktree
`/tmp/wepp-default-port`, checked out on the remote-default branch
`wepp_260430_negmeltfix_comparator`. The affected output formats are in
`src/watbal.for` and `src/watbal_hourly.for`. `AGENTS.md` defines release gates.
WEPPpy vendors binaries under `wepp_runner/bin/` and selects the disturbed WBT
binary in `wepppy/nodb/configs/disturbed9002_wbt.cfg`.

## Plan of Work

In the WEPP default-branch worktree, widen only the first field in SOIL format
1100 from `I2` to `I5`, add the existing source-contract regression, and amend
`AGENTS.md` so every release begins by resolving and checking out the branch
named by `refs/remotes/origin/HEAD`; a non-default release requires explicit
operator authorization and must be labeled as such. Build a new dated release
from the clean default branch and execute the repository's required source and
release validations. Then copy the exact release pair into WEPPpy, update
vendored release notes/change log, select the new binary without HBP metadata,
and run provenance, smoke, focused runner, and broader repository gates.

## Concrete Steps

Work in `/tmp/wepp-default-port` for source edits and builds. Verify branch and
cleanliness, apply the bounded patch with `apply_patch`, run focused pytest and
the full release gates from `AGENTS.md`, then use the dated release build helper
with a unique tag. Work in `/home/workdir/wepppy` to vendor with `install`, update
documentation/configuration, and validate using `tools/check_wepp_binary_provenance.sh`,
the host smoke scripts, and `wctl run-pytest`.

## Validation and Acceptance

The source contract test must prove both fixed-form sources use `I5` and reject
the old `I2` token. Both new binaries must pass host smoke, the hillslope
watchlist, the WEPP test suite, artifact policy, ELF provenance, and a same-build
watershed replay using legacy `H*.pass.dat`. WEPPpy must infer
`legacy_ascii` for the new binary, generate legacy pass prompts, pass provenance
and smoke checks, and pass focused plus full pytest gates.

## Idempotence and Recovery

All source edits are small and reviewable. Build outputs use a new tag and do
not overwrite historical releases. If any release gate fails, do not vendor;
retain logs, repair on the default branch, rebuild the same unreleased tag, and
repeat all gates before committing.

## Artifacts and Notes

Record final commit hashes, binary SHA-256 values, test totals, and any skipped
gate here as work proceeds.

- WEPP source fix/guardrail commit: `f24c957e3633898e0fd4cbbea5ae08c781f29dba`.
- WEPP release commit: `2444b521`.
- Watershed SHA-256: `4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5`.
- Hillslope SHA-256: `86ef065c8d8c6c1e644db40c022c7c850701c0c174d3c622dfa28f1d6da122e7`.

Revision note (2026-08-03): Closed implementation and validation; the WEPPpy
commit identifier is recorded in the repository history containing this plan.

## Interfaces and Dependencies

No runtime interface or dependency changes are planned. The legacy ASCII pass
contract remains `H*.pass.dat`; only the printable width of the watershed SOIL
OFE identifier changes from two to five digits.
