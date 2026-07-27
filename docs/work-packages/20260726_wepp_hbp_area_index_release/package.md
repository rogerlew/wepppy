# WEPP Direct-HBP Hillslope Area Index Repair

**Status**: Active
**Started**: 2026-07-27 UTC
**Security impact**: none; no dedicated security review is required.

## Purpose

Repair the direct-HBP watershed path that shifts every hillslope area forward
by one slot and leaves the final hillslope area at zero. Publish a new WEPP
release, prove WEPPpyo3 accepts its corrected LOSS output, vendor the release
in WEPPpy, and regenerate the Forest incident run
`mdobre-foursquare-fovea`.

## Failure and Impact

The watershed `loss_pw0.txt` reports the area from hillslope `n + 1` on row
`n`, and reports `0.000 ha` for the final hillslope. WEPPpy consequently cannot
calculate hillslope-normalized Omni summaries. The individual HBP shards
contain correct positive areas; the corruption occurs when their metadata is
copied into legacy WEPP arrays.

## Scope

Included work covers `/workdir/wepp-forest_260430_baseline`,
`/workdir/wepppyo3`, and `/workdir/wepppy`: source repair, regression tests,
release artifacts, changelogs, parser and consumer validation, vendoring,
dual review, commits and pushes, and targeted Forest regeneration.

Unrelated model equations, HBP serialization, report-level zero-area
substitution, worker deployment, and stack-wide restarts are excluded.

## Success Criteria

- The HBP reader writes metadata into one-based WEPP hillslope slots.
- A generated watershed `loss_pw0.txt` contains 587 hillslope rows and no
  non-positive `Hillslope Area` value.
- Hillslope 587 reports approximately `0.080 ha`.
- WEPPpyo3 converts the corrected LOSS and SOIL outputs without schema drift.
- WEPPpy consumes the native parquet output and compiles Omni hillslope
  summaries.
- A uniquely named WEPP release is vendored with provenance and changelogs.
- Independent code and QA reviews have dispositions for every finding.
- All three repositories are committed and pushed.

## Hardening Lifecycle

The health signal is a positive area for every generated hillslope LOSS row
with one-to-one agreement against HBP metadata. Danger signals are a shifted
area sequence, a zero/non-finite area, parser column drift, or binary
provenance mismatch. No temporary mitigation is introduced. Observe Forest
Omni runs for 30 days after deployment.

## Related Package

This corrects a defect discovered after
`20260726_wepp_soil_ofe_overflow_release`, which produced `wepp_260726`.
