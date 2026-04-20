# WEPP Binary Release Checklist

## Pre-Vendor Build

1. Build in `wepp-forest` with pinned compiler `/usr/bin/gfortran`.
2. Run smoke and regression gates in `wepp-forest`.
3. Confirm watershed replay completion marker on staged reference run.

## Provenance Verification (Required)

1. Run:
   - `tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_<tag> wepp_runner/bin/wepp_<tag>_hill`
2. Confirm gate output shows:
   - interpreter `/lib64/ld-linux-x86-64.so.2`
   - no unexpected `RPATH/RUNPATH`
   - `ldd` resolves only system library paths
3. Record evidence log path in release notes/work package.

Signed step:

- [ ] Provenance verified (`tools/check_wepp_binary_provenance.sh`) by: __________ on: __________

## Post-Vendor Validation

1. Run host smoke checks for both binaries.
2. Run targeted `wepp_runner` regression tests.
3. Record binary hashes and validation command logs.
