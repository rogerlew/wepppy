# Tracker - EBE `peak_runoff` Regression Ablation and Repair

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-13 22:15 UTC  
**Current phase**: Fix candidate built and vendored (semantic recert in progress)  
**Last updated**: 2026-05-13 23:10 UTC  
**Next milestone**: Complete broader cohort recertification and finalize release disposition  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Add regression tests for all-zero `ebe_pw0.peak_runoff` failure mode.
- [ ] Re-run three-cohort semantic comparison and publish post-fix evidence.

### In Progress
- [ ] Release disposition hardening for mixed fixture compatibility (`H*.hbp` candidate vs legacy `H*.pass.dat` host-smoke defaults).

### Blocked
- [ ] None.

### Done
- [x] Regression classified as real contract defect candidate: `ebe_pw0.peak_runoff` all-zero in `wepp_260513` rerun while `chan.out` is nonzero on same keys (2026-05-13 22:15 UTC).
- [x] Work package scaffolded with `package.md`, `tracker.md`, and active ExecPlan (2026-05-13 22:15 UTC).
- [x] Baseline artifact capture completed for `off-the-rack-neoprene` and `carnivorous-adobo` at interchange layer (`artifacts/pre_fix_interchange_manifest.csv`).
- [x] Stage-by-stage ablation executed with raw text and parser-path controls (`artifacts/ablation_stage_summary.json`, `artifacts/ablation_stage_matrix.csv`, `artifacts/off_ablation_parser_path_comparison.json`).
- [x] First-loss boundary isolated to producer raw output: `off_ablation_first_loss_boundary=producer_raw_ebe_txt` (`ebe_pw0.txt` zeros while `chan.out` nonzero in same replay).
- [x] Producer-side fix candidate built in `wepp-forest` and validated on off-run ablation replay (`artifacts/post_fix_semantic_compare.json`).
- [x] Candidate binaries vendored in `wepppy` with regenerated sidecars and provenance packet (`artifacts/binary_provenance.md`).

## Timeline

- **2026-05-13 22:15 UTC** - Package created and scoped.
- **2026-05-13 22:28 UTC** - Ablation matrix complete; producer-side first-loss boundary confirmed.
- **2026-05-13 23:10 UTC** - Fix candidate built, replayed, and vendored with provenance evidence.
- **TBD** - Regression tests and three-cohort recertification complete.

## Decisions Log

### 2026-05-13 22:15 UTC: Use ablation-first approach before code changes
**Context**: The observed defect is cross-table semantic (nonzero channel peaks vs all-zero event peak field), and fault location is not yet isolated.

**Options considered**:
1. Patch suspected parser/writer path immediately.
2. Run stage-by-stage ablation to locate first-loss boundary, then patch minimally.
3. Roll back binary only and defer investigation.

**Decision**: Option 2.

**Impact**: Slower initial step, but lower risk of mis-fix and clearer evidence for release recertification.

### 2026-05-13 22:28 UTC: Treat parser/interchange path as non-causal for this defect
**Context**: Off-run ablation replay preserved `ebe_pw0.txt` and generated three parquet outputs (`pipeline`, `python`, `rust`) from the same raw source.

**Options considered**:
1. Continue investigating parser/writer paths first.
2. Promote producer-stage investigation as the next repair boundary.

**Decision**: Option 2.

**Impact**: Repair work can focus on producer-side generation of `ebe_pw0.txt` peak values; parser/interchange layers are behaving contract-faithfully on this defect signature.

### 2026-05-13 23:10 UTC: Vendor HBP-compatible fix candidate and preserve evidence split
**Context**: Producer fix candidate resolved all-zero peak signature on off-run replay and restored chan-vs-ebe alignment. Vendoring gates passed for provenance and HBP-compatible smoke fixtures, while default host-smoke fixtures in `wepppy` still point at legacy `H*.pass.dat` run files.

**Options considered**:
1. Block vendoring until legacy fixture set is migrated.
2. Vendor candidate now with explicit compatibility disclosure and follow-up recertification work.

**Decision**: Option 2.

**Impact**: Candidate is available for semantic/regression follow-up immediately; fixture-compatibility cleanup remains explicit follow-up work.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Misidentifying failing stage and patching wrong layer | High | Low | Stage-level ablation now proves first-loss boundary at producer raw `ebe_pw0.txt` | Mitigated |
| Fix resolves peak field but regresses routing metrics | High | Low | Off-run post-fix semantic evidence confirms restored chan-vs-ebe alignment; still run three-cohort recertification | Monitoring |
| Hidden dependency on pass-family-specific behavior | Medium | High | Candidate binary validated on HBP fixtures; legacy fixture incompatibility explicitly tracked in provenance artifact | Open |

## Hardening Signal Log

- **Baseline health signals**:
  - `ebe_pw0.peak_runoff` all-zero in `off-the-rack-neoprene` (`wepp_260513`).
  - `chan.out.Peak_Discharge` nonzero in same run on same keys.
- **Ablation health signals**:
  - Off ablation replay: raw `ebe_pw0.txt` peak column is all zero while raw `chan.out` peak column is nonzero.
  - Off ablation parser-path control: `pipeline/python/rust` parquet peak columns are bit-identical (all zero), proving parser/writer layers are not introducing zeros.
- **Post-change health signals**: pending implementation.
- **Post-change health signals**:
  - Off-run ablation replay with patched binary shows `ebe_pw0` peak zeros resolved (`zero_rows=0`).
  - Candidate chan-vs-ebe delta profile returns to expected small-error envelope.
- **Danger signals observed**:
  - Default `wepppy` host-smoke fixture set still references legacy `H*.pass.dat` run files; candidate HBP-focused binary expects `H*.hbp`.
- **Temporary callus register**: none.
- **Softening experiments**: none.

## Verification Checklist

### Code Quality
- [ ] Targeted tests pass for touched modules.
- [ ] Full affected kernel/serialization sweeps pass.

### Documentation
- [ ] Package docs and evidence artifacts updated.
- [ ] Comparison summary updated with post-fix verdict.

### Testing
- [ ] Pre-fix reproducer test fails on defect state.
- [ ] Post-fix test passes and prevents all-zero regression recurrence.
- [ ] Three-cohort replay manifests reviewed for drift.

### Deployment / Release
- [ ] Corrected binary rebuilt and hashed.
- [ ] Vendor-in procedure completed in `wepppy`.
- [ ] Rollback steps documented and validated.

## Progress Notes

### 2026-05-13 22:15 UTC: Package initialization
**Agent/Contributor**: Codex

**Work completed**:
- Scoped the regression as an ablation-first remediation package.
- Established objectives, constraints, and evidence requirements.
- Created active ExecPlan for milestone-driven execution.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute ablation matrix and isolate first-loss boundary.
2. Implement minimal fix in responsible layer.
3. Re-run semantic comparison and vendor corrected binary.

**Test results**:
- Existing semantic evidence file available at `/tmp/off260513_vs_ca_dcc52a6_semantic_compare.json`.

### 2026-05-13 22:28 UTC: Ablation campaign execution
**Agent/Contributor**: Codex

**Work completed**:
- Created interchange manifest evidence: `artifacts/pre_fix_interchange_manifest.csv`.
- Executed stage-ablation replays on cloned runs:
  - `/wc1/runs/of/off-the-rack-neoprene-ablation-ebepeak`
  - `/wc1/runs/ca/carnivorous-adobo-ablation-ebepeak`
- Preserved raw producer outputs (`delete_after_interchange=False`) and computed stage summaries:
  - `artifacts/ablation_stage_summary.json`
  - `artifacts/ablation_stage_matrix.csv`
  - `artifacts/off_ablation_parser_path_comparison.json`
- Isolated first-loss boundary to producer raw output (`off_ablation_first_loss_boundary=producer_raw_ebe_txt`).

**Blockers encountered**:
- Initial off-ablation watershed rerun failed due to missing `H*.hbp` files after cleanup; resolved by regenerating hillslope outputs with `wepp_260513` before watershed replay.

**Next steps**:
1. Implement minimal producer-side fix where `ebe_pw0.txt` peak values are generated.
2. Add regression guard for "ebe peak all-zero while channel peaks nonzero" signature.
3. Re-run three-cohort semantic comparison and then vendor corrected binary.

**Test results**:
- Off ablation raw stage: `ebe_raw_txt.zero_rows=60270/60270`, `chan_raw_txt.zero_rows=0/60270`.
- CA ablation raw stage: both `ebe_raw_txt` and `chan_raw_txt` nonzero.
- Parser-path control: zero deltas between `pipeline`, `python`, and `rust` outputs (`max_abs_delta=0`).

### 2026-05-13 23:10 UTC: Producer fix candidate build and vendoring
**Agent/Contributor**: Codex

**Work completed**:
- Patched `wepp-forest/src/wshrun.f90` candidate fix path and rebuilt `wepp`/`wepp_hill`.
- Replayed `/wc1/runs/of/off-the-rack-neoprene-ablation-ebepeak` with patched watershed binary and regenerated interchange.
- Published post-fix semantic evidence (`artifacts/post_fix_semantic_compare.json`).
- Vendored candidate binaries as `wepp_runner/bin/wepp_260513` and `wepp_runner/bin/wepp_260513_hill` with regenerated sidecars.
- Published validation/provenance notes (`artifacts/binary_provenance.md`).

**Blockers encountered**:
- Full `wepppy` default host smoke (legacy `H*.pass.dat` fixture set) is incompatible with HBP-only candidate behavior; HBP fixture smoke passed with `RUNS_DIR=/wc1/runs/co/countrywide-kleptomania/wepp/runs`.

**Next steps**:
1. Add targeted regression tests for the all-zero peak signature.
2. Complete three-cohort semantic recertification.
3. Decide final release promotion based on recertification plus fixture-compatibility disposition.

**Test results**:
- Candidate off-run post-fix: `ebe_raw_txt.zero_rows=0`, `ebe_parquet.zero_rows=0`, `chan_pos_ebe_zero=0`.
- `tools/check_wepp_binary_provenance.sh` PASS.
- HBP fixture host smoke PASS (`wepp` + `wepp_hill`).
- `pytest tests/wepp_runner/test_run_hillslope_retries.py tests/wepp/test_wepp_runner_outputs.py` PASS (`8 passed`).
