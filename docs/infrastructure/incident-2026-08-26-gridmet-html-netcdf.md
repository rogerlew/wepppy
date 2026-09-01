# Incident: GridMET HTTP Error Pages Published as NetCDF

**Incident date**: 2026-08-26
**Environment**: wepp1 production
**Status**: remediation in progress

## Impact

Observed GridMET climate construction failed twice for run
`mdobre-massive-delusion`. Users received a failed RQ job rather than a climate
product. Repeating the unchanged build did not provide reliable recovery.

## Failure Signatures

The first job, `15c8780c-c028-4dbc-aaa5-f8260a0c41a9`, failed while opening
`GridMetVariable.MinimumRelativeHumidity_2022.nc`. Retry job
`1fadbb0c-e77d-4644-bda2-f04513154dbc` later failed on
`GridMetVariable.Precipitation_1982.nc`. Both raised:

    OSError: [Errno -51] NetCDF: Unknown file format

## Evidence

The run requested eight variables for 47 years, producing 376 annual download
targets. Direct validation on wepp1 found 340 valid NetCDF files and 36 invalid
files. The invalid bodies were HTML:

- 11 `502 Proxy Error` responses;
- 25 `503 Service Unavailable` responses.

The files were 299-447 bytes but had final `.nc` names. All WEPPcloud/RQ
services remained running, so this was not a worker-loss or filesystem-outage
failure.

## Root Cause

`wepppy.climates.gridmet.client.retrieve_nc` streamed any HTTP response directly
to the final path without an HTTP status check, timeout, retry, or NetCDF
validation. The multiple-grid build issued up to 12 requests concurrently.
The invalid payload was detected only later when `netCDF4.Dataset` consumed the
published file. The single-location JSON client had retry code but used broad
exceptions, no timeout, no response-schema validation, and could include an
upstream response body in an error.

## Remediation Contract

The associated work package is
`docs/work-packages/20260831_gridmet_download_hardening/`. It preserves the two
existing acquisition strategies while adding bounded transient retry,
timeouts, response validation, redacted errors, same-directory staging,
atomic gridded publication, and a four-worker grid acquisition ceiling.

The package does not mutate this run. After deployment, recovery consists of
rerunning climate construction so every annual artifact is reacquired through
the validated boundary.

## Recurrence Trigger

Any final `.nc` artifact that cannot be opened, any HTML/proxy response found
under a climate data filename, or repeated unknown-format failure opens a new
incident/work package citing this record. Do not append later remediation to a
closed package.
