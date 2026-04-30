# Ablation Notes: 20260430_uncapped-spectacular_h2637_hillslope_closure-spike

## Context

- `incident_id`: `20260430_uncapped-spectacular_h2637_hillslope_closure-spike`
- `runid`: `uncapped-spectacular`
- `config`: `H2637` hillslope (`p2637.run`)
- `error_file`: `/geodata/wc1/runs/un/uncapped-spectacular/wepp/runs/p2637.err`
- `host_role`: `mixed`
- `host_name`: `wepp1 + forest + blarhg`
- `container_service`: `none`
- `binary_path`: `wepp_260429_hill`, `wepp_dcc52a6_hill`, `wepppy-win-bootstrap.exe`
- `shared_context_files_staged`: `yes`
- `shared_context_inventory`: `wepp_ui.txt,pmetpara.txt,snow.txt,gwcoeff.txt,chan.inp,chntyp.txt,tc.txt`
- `fuzzy_case_set_source`: `not-run (no patch promotion in this attribution package)`

## Operator Log (Chronological)

```text
[2026-04-30 19:26:09 UTC] Production preflight and source verification.
Command:
ssh wepp1 'hostname; pwd; date -u'
ssh wepp1 'ls -la /geodata/wc1/runs/un/uncapped-spectacular/wepp/runs/p2637.* /geodata/wc1/runs/un/uncapped-spectacular/wepp/output/H2637.*.dat'
ssh wepp1 'for f in wepp_ui.txt pmetpara.txt snow.txt gwcoeff.txt chan.inp chntyp.txt tc.txt; do ...; done'
Observation:
Source paths exist; full shared runtime context files present.
Artifacts:
artifacts/repro/source_wepp1/{runs,output}/

[2026-04-30 19:27:xx UTC] Confirm production binary identity from source run log.
Command:
rg -n "run_hillslope|binary_identity|VERSION" artifacts/repro/source_wepp1/runs/p2637.err
ssh wepp1 'sha256sum /workdir/wepppy/wepp_runner/bin/wepp_260429_hill /workdir/wepppy/wepp_runner/bin/wepp_260429'
Observation:
Source run executed with `/workdir/wepppy/wepp_runner/bin/wepp_260429_hill` (`sha256=0a7a5ced...`).
Artifacts:
artifacts/repro/source_wepp1/runs/p2637.err

[2026-04-30 19:28:xx UTC] Stage incident package and replay inputs.
Command:
python tools/ablation_protocol.py init --incident-id 20260430_uncapped-spectacular_h2637_hillslope_closure-spike
rsync source snapshot from wepppy package into incident `artifacts/repro/source_wepp1/`
rsync shared context files from wepp1 into `artifacts/repro/source_wepp1/runs/`
rsync wepp binaries (`wepp_260429_hill`, `wepp_dcc52a6_hill`) into `artifacts/repro/source_wepp1/bin/`
Observation:
Incident-local repro tree prepared with immutable source + staged replay copy.
Artifacts:
artifacts/repro/source_wepp1/
artifacts/repro/staged/

[2026-04-30 19:29:07 UTC] Lane C000 baseline Linux replay.
Command:
cd artifacts/repro/staged/runs && ../../source_wepp1/bin/wepp_260429_hill < p2637.run > ../../../logs/C000_baseline_stdout.txt 2> ../../../logs/C000_baseline_stderr.txt
Observation:
Run completes through simulation year 34; success marker present.
Artifacts:
artifacts/logs/C000_baseline_{stdout,stderr,exit_code}.txt
artifacts/repro/C000_baseline_output/H2637.*.dat

[2026-04-30 19:29:27 UTC] Lane C010 comparator Linux replay (historical binary).
Command:
cd artifacts/repro/staged/runs && ../../source_wepp1/bin/wepp_dcc52a6_hill < p2637.run > ../../../logs/C010_dcc52a6_stdout.txt 2> ../../../logs/C010_dcc52a6_stderr.txt
Observation:
Run completes through simulation year 34; success marker present.
Artifacts:
artifacts/logs/C010_dcc52a6_{stdout,stderr,exit_code}.txt
artifacts/repro/C010_dcc52a6_output/H2637.*.dat

[2026-04-30 19:30:xx UTC] Stage Windows comparator lane inputs on blarhg.
Command:
tar -C artifacts/repro/staged/runs -cf - . | ssh blarhg "wsl bash -s" (extract to /mnt/c/src/wepppy-win-bootstrap/tmp/h2637_ablation/C020_win_baseline/runs)
Observation:
Windows lane runs directory mirrors Linux staged inputs.
Artifacts:
artifacts/repro/C020_winbootstrap_output/runs/*

[2026-04-30 19:31:28 UTC] Lane C020 comparator Windows replay.
Command:
ssh blarhg "wsl bash -s" <<script
  /mnt/c/src/wepppy-win-bootstrap/bin/wepppy-win-bootstrap.exe < p2637.run
script
Observation:
Run completes through simulation year 34; success marker present.
Artifacts:
artifacts/logs/C020_winbootstrap_{stdout,stderr,exit_code}.txt
artifacts/repro/C020_winbootstrap_output/H2637.*.dat
artifacts/env/C020_blarhg_winbootstrap_env.txt

[2026-04-30 19:32-19:40 UTC] Interchange conversion + closure diagnostics.
Command:
.venv/bin/python -c "run_wepp_hillslope_wat_interchange / run_wepp_hillslope_pass_interchange for each lane"
.venv/bin/python analysis scripts producing lane_closure_summary/day44 breakdown/hash and chain residual tables
Observation:
Day-44 closure spike reproduces only in source + C000 baseline; absent in C010 and C020 lanes.
Artifacts:
artifacts/logs/lane_closure_summary.csv
artifacts/logs/lane_day44_legacy_closure.csv
artifacts/logs/day44_ofe_errors_by_lane.csv
artifacts/logs/day44_ofe_errors_legacy_by_lane.csv
artifacts/logs/first_gt1_from_j40_by_lane.csv
artifacts/logs/lane_output_hashes.csv
artifacts/logs/lane_chain_residuals.csv
```

## Assumptions and Corrections

- assumption: relative path `../../logs` from `artifacts/repro/staged/runs` would resolve to incident logs.
- correction: corrected to `../../../logs` and reran lanes.
- evidence: initial no-file error followed by successful C000/C010 lane outputs.

- assumption: first pull of C020 artifacts failed.
- correction: pull had succeeded; the follow-on copy ran before transfer completion. Re-verified and promoted files.
- evidence: `artifacts/repro/C020_winbootstrap_output/` contains expected logs + `H2637.*.dat` outputs.

## Lane Notes

### Lane A: L00/C000 baseline production-binary replay

- goal: verify source anomaly reproducibility under incident-local replay.
- cases executed: `C000`.
- conclusion: reproduced day-44 spike (`OFE19=-180.459 mm`, `hillslope=-180.31779 mm`).

### Lane B: L10/C010 historical binary comparator

- goal: isolate binary-lineage effect with same staged inputs.
- cases executed: `C010`.
- conclusion: day-44 spike not reproduced (`hillslope=+0.1213 mm`).

### Lane C: L20/C020 windows bootstrap comparator

- goal: test comparator behavior on `blarhg` with required `wepppy-win-bootstrap.exe`.
- cases executed: `C020`.
- conclusion: day-44 spike not reproduced (`hillslope=+0.13619 mm`).

## End-of-Session Summary

- best current hypothesis: day-44 anomaly is linked to current production binary lineage (`wepp_260429_hill`) for this hillslope, not a universal input artifact and not a Windows-only effect.
- unresolved blockers: routine/state-level cause inside the `wepp_260429_hill` lineage remains unresolved.
- next first command: begin source-level routine ablation in `wepp-forest` against the smallest day-44/OFE19 causal boundary.
- fuzzy regression status: not run (no mutation candidate selected).
- fuzzy failure ledger path: `artifacts/logs/fuzzy_failures.md`.
