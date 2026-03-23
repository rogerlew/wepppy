# Validation Summary

## Peridot (Rust)

1. `cargo fmt` (in `/workdir/peridot`) - PASS.
2. `cargo test --test watershed_parquet_manifest -- --nocapture` - PASS (`3 passed`).
3. `cargo test --test hillslope_slope_scalar -- --nocapture` - PASS (`1 passed`).

## WEPPpy (targeted pytest)

1. `wctl run-pytest tests/topo/test_peridot_runner_wait.py` - PASS (`11 passed`).
2. `wctl run-pytest tests/tools/test_migrations_parquet_backfill.py -k watershed` - PASS (`1 passed`, `12 deselected`).

## Real-run verification (`/wc1/runs/un/unassailable-sensuousness`)

### Commands
1. Build + deploy updated Peridot binaries:
   - `cargo build --release --bin abstract_watershed --bin wbt_abstract_watershed` (in `/workdir/peridot`)
   - `cp /workdir/peridot/target/release/abstract_watershed /workdir/wepppy/wepppy/topo/peridot/bin/abstract_watershed`
   - `cp /workdir/peridot/target/release/wbt_abstract_watershed /workdir/wepppy/wepppy/topo/peridot/bin/wbt_abstract_watershed`
2. Re-run abstraction + post-process:
   - `wctl run-python` script invoking:
     - `run_peridot_abstract_watershed(wd, clip_hillslopes=False, clip_hillslope_length=300.0, bieger2015_widths=True, skip_flowpaths=True)`
     - `post_abstract_watershed(wd)`

### Results
- `watershed/hillslopes.parquet`: present
- `watershed/channels.parquet`: present
- `watershed/flowpaths.parquet`: absent (expected for `skip_flowpaths=true`)
- `watershed/README.md`: present and refreshed
- README confirms flags:
  - `clip_hillslopes=false`
  - `clip_hillslope_length=300.000`
  - `bieger2015_widths=true`
  - `skip_flowpaths=true`
  - `representative_flowpath=false`
- README schema section includes WEPPpy-derived columns:
  - `wepp_id` (hillslopes/channels)
  - `chn_enum` (channels)

### Slope sanity check
- `hillslopes.parquet` `slope_scalar` median: `0.2639849931001663`
- WEPP hillslope profile slope median (`wepp/runs/p*.slp`, excluding `pw0.slp`): `0.24995`
- Median ratio (`parquet / profile`): `1.0561512026411934`
- Interpretation: magnitudes are in a reasonable range.

## Follow-up correction verification (2026-03-22)

1. Updated `/workdir/peridot` abstraction writers to remove watershed CSV output emission in both paths:
   - `src/watershed_abstraction/watershed_abstraction.rs`
   - `src/wbt/wbt_watershed_abstraction.rs`
2. Rebuilt producer binaries:
   - `cargo test --test watershed_parquet_manifest -- --nocapture` - PASS (`3 passed`)
   - `cargo test --test hillslope_slope_scalar -- --nocapture` - PASS (`1 passed`)
   - `cargo build --release --bin abstract_watershed --bin wbt_abstract_watershed` - PASS
3. Replaced WEPPpy bundled binaries with rebuilt artifacts via atomic rename to avoid `ETXTBUSY`.
4. Verified updated runtime surface:
   - `abstract_watershed --help` and `wbt_abstract_watershed --help` now describe `--skip-flowpaths` as skipping `flowpaths.parquet` + slope files.
   - Binary string scan confirms no `watershed/hillslopes.csv`, `watershed/channels.csv`, or `watershed/flowpaths.csv` output strings.
5. Re-ran WEPPpy targeted regression:
   - `wctl run-pytest tests/topo/test_peridot_runner_wait.py` - PASS (`11 passed`).
