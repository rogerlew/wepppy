# WEPP Advanced Options

This page describes the controls under **WEPP → WEPP Advanced Options** in WEPPcloud.

Most projects should run with defaults. Use advanced options when you have a specific calibration or workflow requirement.

## Location in the UI

1. Open a run.
2. Open the **WEPP** control panel.
3. Expand **WEPP Advanced Options**.

## Recommended workflow

1. Change one section at a time.
2. Re-run WEPP.
3. Compare outputs (loss summary, hydrographs, event metrics) before making additional changes.
4. Record why each override was applied.

## Section reference

| Section | What it controls | Typical use |
|---|---|---|
| WEPP UI - Hourly Seepage | Writes and enables `wepp_ui.txt` hourly seepage behavior. | Projects using 7778 soils where hourly seepage handling is needed. |
| Potential ET (PMET) | Penman-Monteith ET inputs (`pmetpara.txt`) and PMET toggle. | ET calibration or explicit PMET workflow. |
| Frost | Winter/frozen-soil parameters in `frost.txt`. | Cold-region calibration where frost response needs tuning. |
| Snow | Snow process parameters in `snow.txt` (including rain/snow threshold temperature). | Snow-dominated watersheds. |
| Baseflow Processing | Groundwater storage and baseflow/deep seepage coefficients. | Recession-shape calibration for watershed hydrograph behavior. |
| Channel Inputs (chan.inp) | Channel hydrograph output interval/type and channel IDs of interest. | Reduce/expand channel hydrograph output detail for diagnostics. |
| Channel Parameters | Channel erodibility, roughness, critical shear, optional variable critical shear. | Channel sediment and routing calibration. |
| Bedrock | Restrictive-layer hydraulic conductivity (`kslast`). | Sites where subsurface restriction assumptions must be overridden. |
| Clip Hillslopes | Optional hillslope length clipping with area preservation. | Prevent excessive erosion on very long hillslopes. |
| Soil Options | Soil depth clipping and initial saturation overrides. | Sensitivity testing around storage depth and initial moisture. |
| Phosphorus | Optional phosphorus concentration inputs (`phosphorus.txt`). | Pollutant export analysis workflows. |
| Export Configuration | Auto-generate prep details and GIS export artifacts on run completion. | Standardize post-run artifacts for reporting or delivery. |
| Interchange | Delete raw WEPP text outputs after successful interchange conversion. | Storage reduction when parquet interchange products are the primary deliverable. |
| WEPP Exec | WEPP binary version and watershed-run execution toggles. | Reproducibility, compatibility, or troubleshooting with specific binaries. |
| Revegetation Scenarios | Cover transform scenario selection and optional CSV upload. | Disturbance/recovery scenario testing with custom cover trajectories. |

## Related references

- [Disturbed Land Soil Lookup Table](./disturbed-land-soil-lookup.md)
- [WEPPcloud User Guide](./user-guide.md)
