# EDDE v2 source reconnaissance

Recorded 2026-10-13 21:15 UTC. These findings motivate the feasibility study; they are not scientific or production acceptance.

The [AWS registry](https://registry.opendata.aws/epa-edde-v2/) advertises 12 km WRF downscaling of MPI-ESM1-2-HR and NorESM2-MM, SSP2-4.5 and SSP3-7.0, historical 1985–2014 and future 2025–2100. The [2025 technical paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12505687/) explicitly includes parts of Canada and describes future 2025–2099. Resolve endpoint and availability differences by reading current objects. The [methodology article](https://doi.org/10.1175/BAMS-D-24-0251.1) states that EDDE is deliberately not bias corrected.

Anonymous S3 listings inspected during this conversation contained `EDDE_V2/6hourly/`, `AnnualMaxSeries/`, `daily/`, `hifr/`, `hourly/`, `monthly/`, and `static/`. Static files existed for both `WRF-MPI` and `WRF-Nor`. Directory presence does not prove every requested variable/model/scenario/period is available.

The downloaded [MPI land-mask NetCDF](https://epa-edde-v2.s3.amazonaws.com/EDDE_V2/static/WRF-MPI/lmask.hist.MPI.EDDE-WRF.fixed.NA12.raw.nc) had dimensions `y=432`, `x=576` and variables `lon`, `lat`, `y`, `x`, `LANDMASK`. Approximate nearest-cell distances, computed from coordinate differences, were Vancouver 3.7 km, Calgary 4.5 km, Edmonton 6.6 km, Winnipeg 5.8 km, Toronto 7.0 km, Montreal 2.5 km, Quebec City 7.5 km, and Halifax 6.3 km. All selected indices were interior to the array. This confirms Canadian geographic coverage; it does not establish usable weather records, identical grids across models, nationwide coverage, or suitability of a particular watershed.

The temporary downloaded file and command output were not retained as package artifacts. M1 must reacquire and preserve provenance; M2 must check actual data and footprint eligibility. Do not reuse these approximate distances as acceptance thresholds.
