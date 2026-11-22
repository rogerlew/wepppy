# Incident Report: unveiled-grinder `pw0` Year-55 SIGFPE (`evappm_` -> `watbal_hourly_`)

- `incident_id`: `20260427_unveiled-grinder_pw0_watershed_sigfpe-evappm-watbal-hourly`
- `status`: `resolved_candidate_pending_broader_regression`
- `scope`: `watershed`
- `author`: `Codex`
- `date_utc`: `2026-04-28`
- `host_scope`: `mixed`

## 1) Summary

Production run `unveiled-grinder:pw0` aborts at simulation year 55 with
`SIGFPE`. The failure signature in `pw0.err` localizes to
`evappm_ -> watbal_hourly_ -> wshdrv_ -> MAIN__`.

- failing run/config:
  - `wepp1:/geodata/wc1/runs/un/unveiled-grinder/wepp/runs/pw0.run`
- failure signature:
  - `Program received signal SIGFPE` with backtrace top frames
    `evappm_`, `watbal_hourly_`, `wshdrv_`
- first observed time:
  - source file timestamp `2026-04-26 18:46 PDT` on `pw0.err`
- current impact:
  - recurrence reported on `2026-04-27` using `wepp_260426`; the rerun took
    `9784.7 s` and hit the same year-55 signature
  - guard-candidate binary
    `/geodata/wc1/runs/un/unveiled-grinder/wepp_ablation_20260427/bin/wepp_260428_unveiled_g1`
    passed two decisive full 100-year durability lanes (`G1`, `G1R`) on wepp1
    with `exit_code=0`, no SIGFPE signatures, and watershed completion markers

## 2) Impact and Blast Radius

- affected hosts:
  - production `wepp1` (source evidence)
  - dev `forest` (campaign staging)
- affected runids/configs:
  - `unveiled-grinder/pw0`
- user-facing effect:
  - long-running watershed simulation aborts before completion
- severity:
  - `high` for this run/config

## 3) Baseline Reproduction

- source error file:
  - `/geodata/wc1/runs/un/unveiled-grinder/wepp/runs/pw0.err`
- baseline command:
  - source-signature capture from production log tail:
    `tail -n 260 /geodata/wc1/runs/un/unveiled-grinder/wepp/runs/pw0.err`
- baseline result (`PASS|FAIL|ERROR`):
  - `FAIL` (`C000`, source signature)
- baseline signature (signal/backtrace/success-marker status):
  - `SIGFPE`, `evappm_ -> watbal_hourly_ -> wshdrv_`,
    watershed loop reaches `SIMULATION YEAR = 55` then aborts
- staged local baseline status:
  - full `wepp/` mirror (including outputs) completed and parity-validated
    via `rsync --dry-run --delete` (0 files changed)
  - `C100` hit wrapper timeout (`exit 124`) with no SIGFPE signature
  - `C102` and `C103` completed with no SIGFPE signature
- recurrence status:
  - user-reported `wepp_260426` rerun reproduced the year-55 `SIGFPE` after
    `9784.7 s`; immutable artifact capture is pending
  - `C205` analyzed the existing full-period crash core with `wepp_260427`
    debug symbols and confirmed the trapped operands
  - full-period guard candidate runs `G1` and `G1R` both reached
    `SIMULATION YEAR = 100` and completed successfully

## 4) Ablation Findings

- first known failing case:
  - `C000` (production source signature)
- nearest passing case:
  - `G1` and `G1R` (full 100-year guard-candidate durability lanes)
- minimal failing delta:
  - isolated to `evappm.for` crop water-stress denominator guard:
    `etksden = TAW - RAW; if (etksden.le.0.0) etks=1.0 else etks=wftrp/etksden`
- confidence level (`low|medium|high`):
  - `high` for failure signature capture
  - `high` that prior non-repro disposition should be retired

Key lane outcomes:

1. `C200` crossed years 55-60 and completed with
   `WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY`.
2. `C201`/`C202` completed with no SIGFPE signatures (debug and production
   binaries in isolated workspace).
3. `C203` produced no SIGFPE; `C203.chan.tail.txt` shows channel progression in
   year 56 (day 126), beyond the source failure year boundary.
4. `C204` was inconclusive due kernel `D`-state I/O wait at pass-file ingestion
   boundary; no SIGFPE emitted before operator termination.
5. `C205` copied the existing apport core from the full-period `wepp_260426`
   crash and analyzed it with the `wepp_260427` debug-symbol binary. It
   confirmed `year=55`, `sdate=26`, `iplane=1126`, `wftrp=-10.9115524`,
   `RAW=0`, `rawpaj=1`, `rtd(iplane)=0`, and a zero denominator in
   `etks = wftrp/(TAW - RAW)`.
6. `G1` (first full 100-year decisive guard lane) completed in `15402.57 s`
   (`2026-04-28T01:01:46Z` to `2026-04-28T05:18:28Z`) with
   `WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY`, `exit_code=0`, and no
   SIGFPE signatures.
7. `G1R` (second full 100-year decisive durability replay) completed in
   `13629.72 s` (`2026-04-28T05:23:22Z` to `2026-04-28T09:10:32Z`) with the
   same success marker and no SIGFPE signatures.

The decisive full-period gate is satisfied for this candidate. Incident status
is now candidate-resolved pending broader regression/watchlist execution.

## 5) Evidence Index

- `matrix.csv`: `./matrix.csv`
- `notes.md`: `./notes.md`
- logs root: `./artifacts/logs/`
- diffs root: `./artifacts/diffs/`
- repro root: `./artifacts/repro/`
- environment capture: `./artifacts/env/`
- artifact manifest: `./artifacts/manifest.csv`
- checksums: `./artifacts/checksums.sha256`
- fuzzy case results: `./artifacts/logs/fuzzy_case_results.csv`
- fuzzy failure ledger: `./artifacts/logs/fuzzy_failures.md`

## 6) Root Cause Hypothesis / Scientific Rationale

The recurrence makes the original one-off/non-repro hypothesis insufficient.
`C205` confirms the Penman-Monteith crop water-stress calculation in
`evappm.for` line 357 traps on a zero denominator:
`etks = wftrp/(TAW - RAW)`. Candidate contributing factors include:

1. full-period climate/state history that was removed or altered by truncated
   lanes,
2. output/pass-file state interaction in the production-style watershed replay,
3. an inactive crop/root state with `rtd(iplane)=0`, `rawpaj=1`, `RAW=0`, and
   negative `wftrp`, which sends control to the water-stress divide even though
   `kcbcon=0` makes the resulting crop transpiration term inactive.

## 7) Reopened Ablation Strategy

- decisive validation rule:
  - every decisive lane must use the full 100-year simulation period; any
    candidate pass claim must run through completion to verify durability
- diagnostic-only lanes:
  - truncated climate, 60-year, min-IO, or altered-output lanes may be used only
    to localize state and reduce code-search scope; they cannot eliminate
    climate duration, binary behavior, or output-state interaction as factors
- run-budget policy:
  1. capture one full 100-year failing baseline with immutable inputs, outputs,
     binary hash, stdout, and stderr
  2. use `C205` as the observe-only operand capture for the line-357 divide
  3. because `C205` identified the unsafe denominator/state, run one
     minimal guard candidate full 100-year lane
  4. require a second full 100-year durability replay of any candidate before
     considering vendoring or wider regression gates
- stop rule:
  - do not spend additional 100-year lanes on broad hypothesis sweeps; if the
    observe lane does not identify the failing operands, improve observability
    and rerun rather than testing speculative fixes
- execution result:
  - complete: `C205` observe capture, `G1` full-period guard lane, and `G1R`
    full-period durability replay

## 8) Remediation Decision

- selected fix:
  - minimal guard in `src/evappm.for`:
    - before: `etks = wftrp/(TAW - RAW)`
    - after:
      `etksden = TAW - RAW; if (etksden.le.0.0) etks=1.0 else etks=wftrp/etksden`
  - candidate binary:
    `/geodata/wc1/runs/un/unveiled-grinder/wepp_ablation_20260427/bin/wepp_260428_unveiled_g1`
    (`sha256=4e82800b6af040dd3fcd6ef6a89433d649e628d33972bfbb1ca3327d30cfe895`)
- why this fix:
  - directly addresses the confirmed zero/non-positive denominator at the trap
    site while preserving existing behavior for positive denominator states
- rollback plan:
  - keep candidate scoped to ablation binary until broader regression gate passes
- required validations:
  1. source signature capture (`C000`)
  2. full-period core observe operand capture (`C205`)
  3. full 100-year decisive lane `G1` (PASS)
  4. full 100-year decisive durability replay `G1R` (PASS)
- non-regression gate status (if mutation lane):
  - pending broader watershed regression/watchlist
- fuzzy-regression gate status:
  - pending broader gate execution prior to promotion

## 9) Production Safety Notes

- source production files were copied read-only from `wepp1`.
- no in-place mutation was performed in `/geodata/wc1/runs/un/unveiled-grinder`.
- campaign execution is staged under `/workdir/wepp-forest/docs/ablation/...`.

## 10) Follow-Up Work

1. Run broader watershed regression/watchlist lanes before release promotion.
2. Keep `C205` core and operand/register artifacts with this package for audit.
3. Promote candidate binary only after broader regression gate passes.
