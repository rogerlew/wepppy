# Feasibility evidence and acceptance criteria

Recorded before multidecade assessment and final disposition on 2026-10-13.

## Data validity and scientific interpretation

Require complete requested Gregorian daily dates, exactly one point/date/variable, finite unmasked values, nonnegative precipitation, and daily maximum temperature no lower than minimum. Independently verify the selected projected cell and metadata; no automatic nearest-land replacement. Check actual endpoint timestamps. Historical quality uses 1995–2014 Daymet reference climatology and intersecting calendar days; Daymet is an observation-derived gridded reference, not independent raw station measurements. Do not interpret simulated daily sequence correlation as forecast skill.

Report annual and monthly precipitation/temperature bias, wet-day frequency (>=1 mm, a diagnostic definition), dry/wet spell lengths, wet-day 95th percentile, daily 99th percentile, and annual maxima. There is no invented universal bias cutoff for scientific acceptance. Large or spatially inconsistent biases and missing projected auxiliary weather preclude an unconditional production recommendation. Assess model comparisons on common 2060–2079 SSP2-4.5 windows; late-century MPI-only comparisons are labeled separately.

## Generated artifact fidelity

Parse exact CLIGEN PRN and CLI inputs/outputs. Source-to-CLI differences may not exceed 0.1771 mm precipitation or 0.3279 C temperature (existing PRN plus CLI rounding). Require identical full dates, finite fields, positive duration and peak factor >=1 on generated wet days. Record wet-day loss due to PRN quantization, station distances, auxiliary field attribution, dewpoint ordering, and station-header metadata. Do not fix unexpected science by bypassing a guard.

For PRISM, require finite, same-period, same-unit normals and positive reference precipitation. Parse output and require the existing ratio/offset equations within 0.05001 per daily field (CLI rounding). Reject daily temperature inversion; quantify seasonal future/historical signal changes and rounding rather than expecting bit-identical ratios. Reference and target normals are held fixed across periods.

For WEPP, use frozen actual hillslope inputs, verify their original hashes, change only requested climate and simulation-year count, and read exact consumed files. Require successful executable completion, continuous dates matching CLI, finite daily water output, and precipitation agreement within 0.011 mm (water-output formatting). Report runoff/ET/drainage/lateral fluxes and storage; these are plausibility diagnostics, not calibrated hydrologic validation. Canadian climate uses the same frozen U.S. hillslope for consumer smoke tests; no actual Canadian watershed is claimed.

## Performance and completion boundary

Measure actual cold/warm one-year and 20-year acquisition bytes, elapsed time, disk footprint, and peak resident memory. The hard acquisition constraint is the caller's 4 GB per-year query budget; there is no fabricated interactive-latency requirement. Record whether measured multidecade acquisition is practical for existing asynchronous build orchestration before recommending integration; do not add a new service based on theoretical costs.

A go for experimental extraction does not imply a go for production future-climate impact modeling. Disposition each source/mode explicitly; source availability, CLIGEN auxiliary assumptions, bias treatment, PRISM inversion, actual-project/environment evidence, and independent review remain separate gates. A rejected case stays rejected unless a separately documented scientific decision resolves its cause.
