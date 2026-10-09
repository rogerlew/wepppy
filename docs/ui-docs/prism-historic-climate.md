# Historic PRISM climate

For eligible continental-US projects, select **Observed PRISM 800 m (GRIDMET
wind)** in Climate. Enter complete calendar years from 1981 through the previous
year, choose a spatial method, then build climate and run WEPP normally.

| Spatial method | Forcing used by WEPP |
| --- | --- |
| Single climate | Daily data from the PRISM cell nearest the watershed centroid. |
| Multiple climates (PRISM revision) | Centroid daily data, adjusted to each hillslope using the existing monthly PRISM precipitation ratios and temperature offsets. |
| Multiple climates (nearest PRISM cell) | Daily data from the native PRISM cell nearest each hillslope centroid, preserving differences in daily rainfall across cells. No monthly revision or neighboring-cell averaging. |

Hillslopes in one cell receive identical unscaled weather. Existing precipitation
scaling options still apply afterward. GRIDMET supplies shared watershed wind;
the selected CLIGEN station supplies storm duration and within-day intensity.
PRISM daily rainfall does not provide observed within-day storm timing. The
existing quality-guard setting applies and may report CLIGEN convergence warnings.

The established observed-climate dewpoint floor remains enabled, including after
monthly temperature revision. Raw PRISM dewpoint is retained unchanged. The
existing PRN format rounds precipitation to 0.254 mm and temperature to whole
degrees Fahrenheit; very small rainfall can round to zero.

Use the project file browser's `climate/` directory to inspect source parquet,
`provenance.json`, conversion/dewpoint CSVs and retained `prism800m-build-*`
attempts. Project archives retain these records independently of the shared cache.
Failed or interrupted attempts remain visible for diagnosis. A failed monthly
revision must be rebuilt successfully before running WEPP.

Older stored Project Config graphs may require an explicit capability refresh
before the new dataset becomes available. Existing Daymet and stochastic PRISM
selections retain their behavior. OpenET and AgFields accept this climate mode with all three spatial choices.
OpenET compares monthly ET by hillslope and calendar month, subject to satellite
coverage and the existing feature access restrictions. Missing satellite data is
not zero ET. WEPPcloud acquisition requires a valid Climate Engine credential;
a direct OpenET API key is a separate credential.

AgFields requires crop schedule columns for every observed year and prepared
parent hillslope soil/climate files. Subfields inherit their parent's climate,
including monthly PRISM revision or nearest-cell selection; they do not sample
PRISM again at their own centroids.

Developer/operator details: [client and cache design](../dev-notes/prism-800m-client-design.md)
and [integration contract](../schemas/prism-historic-climate-contract.md).
