# Incident Report: srivas42-combatant-ionosphere p24 SIGFPE in `wshpas_`

- `incident_id`: `20260421_srivas42-combatant-ionosphere_p24_sigfpe-wshpas`
- `status`: `resolved`
- `scope`: `hillslope`
- `author`: `codex`
- `date_utc`: `2026-04-21`
- `host_scope`: `mixed`

## 1) Summary

- failing run/config: `runid=srivas42-combatant-ionosphere`, hillslope `p24` (`option 1`)
- failure signature: `SIGFPE` at `SIMULATION YEAR = 1`; production backtrace top `wshpas_ -> contin_ -> MAIN__`
- first observed time: captured in production `p24.err` at `2026-04-21` triage window
- current impact: hillslope execution fails for affected events when `dur=0` and runoff is non-zero

## 2) Impact and Blast Radius

- affected hosts: `wepp1` confirmed (same binary lineage used in worker path)
- affected runids/configs: confirmed on `srivas42-combatant-ionosphere/p24`; control lane `p1` unchanged
- user-facing effect: job failure (`returncode=-8`) in RQ hillslope stage
- severity: `high` for affected hillslope jobs (hard failure)

## 3) Baseline Reproduction

- source error file: `/geodata/wc1/runs/sr/srivas42-combatant-ionosphere/wepp/runs/p24.err`
- baseline command: `cd artifacts/repro/staged/runs && ../../source_wepp1/bin/wepp_260421_hill < p24.run`
- baseline result (`PASS|FAIL|ERROR`): `FAIL`
- baseline signature: year 1, `5 jan 1980`, routing event on OFEs 1..14; `SIGFPE` with top frame `wshpas_`, no success marker

## 4) Ablation Findings

- first known failing case: `C000` (contract-equivalent staged replay)
- nearest passing case: `C003` (same staged input, patched `src/wepp_hill`)
- minimal failing delta: `dur==0` at first runoff event in `wshpas` time-of-concentration denominator path
- confidence level (`low|medium|high`): `high`

## 5) Evidence Index

- `matrix.csv`: `./matrix.csv`
- `notes.md`: `./notes.md`
- logs root: `./artifacts/logs/`
- diffs root: `./artifacts/diffs/`
- repro root: `./artifacts/repro/`
- environment capture: `./artifacts/env/`
- artifact manifest: `./artifacts/manifest.csv`
- checksums: `./artifacts/checksums.sha256`

## 6) Root Cause Hypothesis

Leading hypothesis confirmed: the first routed runoff event for p24 reaches `wshpas` with `dur=0` and non-zero runoff (`9.9484e-03`), so expression `runoff(nplane)/dur` traps before the model can continue.

Evidence chain:
- production + staged baseline trap in `wshpas_` (`C000`).
- patched observe log fires `WFR_G_WPDU y=1980 d=5 c=14 v1=0.0000E+00 v2=9.9484E-03` exactly at failure boundary (`C003`).
- alternate hypotheses (`hslop<=0`, `tcsden<=0`, `runvol==0`) were instrumented and did not fire on this run.

## 7) Remediation Decision

- selected fix: minimum-scope guards in `src/wshpas.for` around the `tcs` and `oalpha` divide/power sites, with `WFR_G_*` observability markers.
- why this fix: it resolves the concrete trap site without changing layer contracts (`ntype/ntype2`) or altering unrelated routines.
- rollback plan:
  - baseline source hash: `81dd7f952d0c5bded3cb1330b828d36e65bf3856`
  - restore command: `git -C /workdir/wepp-forest checkout 81dd7f952d0c5bded3cb1330b828d36e65bf3856 -- src/wshpas.for`
  - compact repro: `cd docs/ablation/20260421_srivas42-combatant-ionosphere_p24_sigfpe-wshpas/artifacts/repro/staged/runs && ../../source_wepp1/bin/wepp_260421_hill < p24.run`
- required validations: completed (`C003` resolved replay, smoke/provenance, comparator context, control parity, pytest suite).

### Patch-Review Checklist (Mandatory)

- `PASS` Diff restricted to offending routine(s); no unrelated source edits in incident patch (`artifacts/diffs/C002_wshpas_guard.patch` touches only `src/wshpas.for`).
- `PASS` No `ntype/ntype2` change; layer-count contract intact (no edits to `pntype*.inc` in incident patch).
- `PASS` Each new guard returns known sentinels:
  - `oalpha=tcs/24.0` fallback already present in same routine (`src/wshpas.for:209`), used by new `WFR_G_WPRV` path.
  - `1.0e-30` denominator floor aligns with same-routine existing denominator guard style (`src/wshpas.for:536`).
  - `1.0e-12` epsilon aligns with model-wide numeric guard convention (`src/saxfun.for:72`, `src/frsoil.for:77`, `src/frwatc.for:87`).
- `PASS` Each new guard emits labeled `WFR_G_*` marker (`WFR_G_WPDU`, `WFR_G_WPSL`, `WFR_G_WPTD`, `WFR_G_WPRV`).
- `PASS` Sibling division/power audit completed and recorded in `notes.md` table.
- `PASS` Parity against canonical `wepp_dcc52a6_hill` executed (`C004/C005`) with strict/raw report plus meaningful-difference assessment.
- `PASS` Rollback plan documented with hash and repro command (above).
- `PASS` Binary-provenance gate passed (`artifacts/logs/C007_binary_provenance.log`).

## 8) Production Safety Notes

- confirmed no in-place mutation under `/geodata/wc1/runs/...`; all ablation runs used copied staged directories under incident artifacts.
- containment steps used: immutable source capture, staged replay, one-change-per-lane matrix, and explicit contract-drift lane.
- operator approvals: none required beyond incident triage; no binary vendoring performed in this campaign.

## 9) Follow-Up Work

1. Run a wider screening sweep for `dur<=0` during event routing across other affected runids to estimate recurrence.
2. Evaluate whether the same guard pattern should be applied in any duplicate `wshpas`-style paths in forks/older release lines.
3. Add/extend fixture coverage for zero-duration event rows in hillslope pass generation to keep this failure mode pinned.
