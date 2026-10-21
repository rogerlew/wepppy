# Reproduction and validation

Run from `/workdir/wepppy`. Python is `/workdir/wepppy/.venv/bin/python`;
set `PYTHONPATH=/workdir/wepppy` for input-generation scripts. All scripts live
in this package’s `artifacts/` directory. Sources are pinned in provenance;
the donor `/wc1/runs/wb/wb34-impoundment-cohort/wepp/runs` is read-only.
Scripts intentionally reject existing attempt directories instead of overwriting.
The recorded root is `/workdir/watershed-physical-water-audit-20261021`.

## Sequence executed

1. `replay_cases.py --root /workdir/watershed-physical-water-audit-20261021/release-matrix`
   generates and executes ten paired 44-year cases with the frozen release pair.
2. `audit_cases.py --root /workdir/watershed-physical-water-audit-20261021/release-matrix`
   reads raw WAT, PASS and channel outputs into independent volume ledgers.
3. `prepare_observer.py` extracts committed native `src/` and `fpm-src/` into
   `observer-source-v2`, adding only channel observation writes.
   Build using `make -C /workdir/watershed-physical-water-audit-20261021/observer-source-v2/src -B FC=/usr/bin/gfortran LINKER=/usr/bin/gfortran wepp`.
4. `replay_observer.py` runs baseline-equivalent off/on watershed replays.
   `audit_observer.py` integrates all native rates including time-zero state.
5. `replay_networks.py` executes daily/hourly short-channel, tributary and cascade
   cases. Run `replay_observer.py --source-group networks --dest-group network-observer --cases daily-short hourly-short daily-tributaries hourly-tributaries daily-cascade hourly-cascade`.
   After all runs finish, run `audit_observer.py --group network-observer --source-group networks --cases daily-short hourly-short daily-tributaries hourly-tributaries daily-cascade hourly-cascade`.
6. `replay_side_control.py` changes only hillslope placement relative to its
   receiving channel, retaining paired PASS. Observe with
   `replay_observer.py --source-group networks --dest-group side-observer --cases daily-side hourly-side`;
   audit with `audit_observer.py --group side-observer --source-group networks --cases daily-side hourly-side`.
7. `prepare_hourly_observer.py` creates an isolated hill probe build.
   Build using `make -C /workdir/watershed-physical-water-audit-20261021/hourly-observer-source/src -B FC=/usr/bin/gfortran LINKER=/usr/bin/gfortran wepp_hill`.
   Run `replay_hourly_observer.py`, then `audit_hourly.py`.
8. `check_initial_groundwater.py` executes three full-period hillslope variants
   changing only initial groundwater; WAT bytes remain unchanged.
9. `check_flat_hydrograph.py` compiles and calls the actual release CHRQIN via
   its committed test harness. Aligned-volume control passes; both defect
   controls and two observed-case operands reproduce the missing volume.
10. `diagnostic_controls.py` verifies five corruption controls and all ten
    cases’ OFE/PASS comparisons against explicit serialization bounds.
11. `retain_evidence.py` copies compact receipts and hashes external evidence.

## Artifact interpretation

`water-ledger.csv` contains hillslope daily local volumes, terminal exports,
selected PASS deliveries and channel publication terms. `channel-ledger.csv`
contains full-precision independently integrated inputs/outputs and observed
state values. `hourly-water-ledger.csv` compares soil screens to independently
observed per-hour unallocated infiltration. Unknown initial/interception stores
remain unknown; soil screens are not complete domain-closure certificates.

The rate-array lateral term is per channel length after the native division;
restore total m³/s with the observed channel length before integration. Daily
volume bookkeeping and independently integrated transport are separate checks.
For cascade accounting, only the first channel receives hillslope PASS; the next
receives its predecessor’s published volume and separately its rate series.

## Retained development failures and corrections

The initial observer insertion asserted because its anchor also matched an
initialization assignment. A subsequent shell build produced an uninstrumented
copy and off/on parity alone passed. That attempt under `observer-source` and
`observer` is excluded from observational evidence. Version 2 uses an exact
anchor and requires nonempty observation artifacts in addition to parity.

An early network audit was launched before the final replay receipt existed and
failed explicitly. The final audit was rerun after all replays completed, with
multi-hill and cascade-aware transfer joins. The initial WAT parser column count
was corrected from 26 to its actual 25 fields. Initial decimal precision bounds
were corrected against Fortran’s `0.xxxxx` representation: WAT E15.7 has seven
significant digits and PASS E11.5 has five. These were audit-tool corrections;
no model outputs or tolerance rationale were changed to hide a physical failure.

## Scope of validation

Native observer builds compile with the release compiler/flags. Baseline/off/on
comparisons cover every baseline file in `runs/` and `output/` for ten watershed
configurations, excluding added observation files; all match. Hill probes compare
generated H1 scientific outputs for three OFE layouts; all match. Diagnostics
read actual outputs, not mocked orchestration. No application production code
changed, so broad WEPPpy/frontend tests were not rerun for this audit.

Final CHRQIN harness evidence uses `/usr/bin/gfortran` with an explicit system
PATH (`flat-hydrograph-system`). An earlier Homebrew-compiler run remains outside
the repository under `flat-hydrograph` and is not the final compiler receipt.
