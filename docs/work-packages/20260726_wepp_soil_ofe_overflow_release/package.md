# WEPP SOIL OFE Overflow and 260726 Release

**Status**: Complete (2026-07-27)
**Timezone**: UTC

## Overview

This package repairs watershed SOIL output for projects with more than 99
hillslopes. WEPP currently formats the OFE identifier with Fortran `I2`, which
emits `**` for identifiers 100 and above. WEPPpyo3 then cannot construct
`soil_pw0.parquet`. The incident run `mdobre-foursquare-fovea` contains 238
ordered OFEs per day and first fails at line 106.

## Objectives

- Widen the WEPP watershed SOIL OFE field and publish `wepp_260726`.
- Preserve compatibility with existing `**` files through strict,
  evidence-backed WEPPpyo3 reconstruction.
- Vendor both `wepp_260726` binaries and their release contract in WEPPpy.
- Validate the rebuilt model and native parser against generated output and the
  synced incident run.
- Commit and push WEPP source, WEPPpyo3, and WEPPpy repositories.

## Scope

### Included

- `/workdir/wepp-forest_260430_baseline` fixed-form SOIL output, tests,
  changelog, dated binaries, and release tag.
- `/workdir/wepppyo3` watershed SOIL parsing, regressions, py312 release
  artifact, registry, and provenance.
- `/workdir/wepppy` binary vendoring, sidecar/provenance contracts,
  integration tests, and package artifacts.

### Explicitly Out of Scope

- Production deployment or worker restart.
- Retrying the production RQ job.
- Changing soil measurements or model equations.
- Guessing identifiers from arbitrary malformed order.

## Success Criteria

- [x] New WEPP output writes numeric OFE 100 and 238 without stars.
- [x] Existing uniform overflow files reconstruct exact OFEs 1 through 238 for
  every day and reject ambiguous sequences.
- [x] The synced incident SOIL file converts successfully with correct row
  count and identifier boundaries.
- [x] `wepp_260726` and `wepp_260726_hill` pass applicable release gates and are
  vendored with provenance.
- [x] WEPPpyo3 release import and relevant WEPPpy interchange/runner tests pass.
- [x] All three repositories are clean, committed, and pushed.

## Compatibility and Regression Plan

The SOIL parquet schema is unchanged. New WEPP text output widens only the
fixed-width OFE field. WEPPpyo3 continues to accept ordinary numeric files and
adds a narrow compatibility path for the legacy overflow marker:

1. numeric identifiers must begin at 1 and increase contiguously within each
   `(year, day)` block;
2. `**` is accepted only after numeric 99 and reconstructs 100, 101, and so on;
3. each subsequent day must contain the same ordered identifier sequence and
   row count established by the first complete day;
4. a numeric identifier after overflow, a gap, early marker, duplicate,
   inconsistent day count, or malformed width fails with line context.

Generated output from `wepp_260726` proves the future format. The synced
238-OFE file proves backward recovery.

## Security Impact and Review Gate

- **Security impact**: low
- **Dedicated security review required**: no
- **Rationale**: Model text formatting, native parsing, and vendored binaries
  change without routes, authorization, secrets, queue wiring, or egress.

## Hardening Contract

- **Failure signature**: `Expected a watershed SOIL data record after the
  header` on a line beginning `**`.
- **Root cause**: fixed-form `I2` OFE output overflows at 100.
- **Health signals**: numeric widened output; exact legacy reconstruction;
  successful SOIL parquet generation.
- **Danger signals**: shifted soil measurements, duplicated/missing OFEs,
  permissive star handling, or binary provenance mismatch.
- **Observation window**: 30 days after production deployment.
- **Temporary calluses**: none.
