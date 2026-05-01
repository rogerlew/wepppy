# Climate Options

This page explains every option in **Climate Options** for WEPPcloud end users:

- what each option is best for,
- what climate data it uses,
- where that data is available,
- how station selection modes work,
- how CLIGEN uses `.par` and `.prn` files,
- when to use each spatial mode,
- what each advanced option does and when to use it.

## Where to find this in WEPPcloud

1. Open your run.
2. Open **Climate Options**.
3. Choose a climate dataset, station selection mode, and (if available) spatial mode.
4. Expand **Advanced options** only when you need to tune behavior.

## Opinionated recommendations

If you want the shortest defensible answer instead of a full option review:

- For **probability/risk assessments**, start with **Stochastic PRISM Modified**.
- For **historical modeling**, start with **Observed DAYMET (GRIDMET wind)**.

## Climate Datasets (Each Climate Option)

## Vanilla CLIGEN

**Suitable for**
- Long-term stochastic (probability/risk) analysis.
- Baseline climate generation when you do not need a specific observed historical sequence.

**Recommendation**
- Use this when you explicitly want plain CLIGEN behavior.
- If your main goal is a probability/risk assessment and **Stochastic PRISM Modified** is available, prefer that option instead.

**Data it uses**
- CLIGEN station statistics from the selected station.
- Your selected simulation length (`Number of years to simulate`).

**Where available**
- Broadly available across interfaces/locales.

**Station selection modes available**
- Auto (`-1`), Distance ranking (`0`), Multi-factor ranking (`1`).

**Spatial modes available**
- Single (`0`), Multiple (`1`).
- Interpolated multiple (`2`) is not available for this dataset.

**Notes**
- In **Multiple** mode, WEPPcloud applies a PRISM revision routine to create per-hillslope climates.

## Stochastic PRISM Modified

**Suitable for**
- Recommended default for probability/risk assessments.
- Stochastic runs where you want PRISM-adjusted climate behavior.
- BAER-style risk/probability workflows when strict historical replay is not required.

**Recommendation**
- Start here when your question is probabilistic: "What is the range of likely runoff/erosion response over many possible years?"
- Prefer this over observed historical modes when you are not trying to reproduce a specific real-world period.

**Data it uses**
- CLIGEN station source + PRISM-informed adjustment workflow.
- Stochastic simulation years you choose.

**Where available**
- Available in many U.S.-centric contexts.
- Blocked in locales configured as GHCN-only in current catalog (`au`, `alaska`, `hawaii`, `nigeria`).

**Station selection modes available**
- Auto (`-1`), Distance ranking (`0`), Multi-factor ranking (`1`).

**Spatial modes available**
- Single (`0`), Multiple (`1`).

**Notes**
- Marked RAP-compatible in the current catalog.
- In **Multiple** mode, PRISM revision generates per-hillslope climate files.

## Observed DAYMET (GRIDMET wind)

**Suitable for**
- Recommended default for historical modeling.
- Historical/observed-condition calibration.
- Streamflow and disturbance-validation work where observed weather is preferred.

**Recommendation**
- Start here when you want to model a real historical period rather than a stochastic climate sequence.
- This is the opinionated first choice for hindcasting, calibration, and other observed-period analyses.

**Data it uses**
- DAYMET observed daily climate.
- Optional GRIDMET wind fill (when `Use GRIDMET wind when applicable` is enabled).

**Where available**
- Year window in catalog metadata: **1980 to 2024**.
- Blocked in GHCN-only configured locales (`au`, `alaska`, `hawaii`, `nigeria`).

**Station selection modes available**
- Auto (`-1`), Distance ranking (`0`), Multi-factor ranking (`1`).

**Spatial modes available**
- Single (`0`), Multiple (`1`), Multiple Interpolated (`2`).

**Notes**
- In **Multiple** mode (`1`), PRISM revision is applied after base build.
- In **Multiple Interpolated** mode (`2`), build is routed to the DAYMET interpolated hillslope workflow (no PRISM revision step in that branch).
- Marked RAP-compatible in the current catalog.

## Observed GRIDMET

**Suitable for**
- Historical/observed-condition modeling using GRIDMET.
- Workflows where observed wind/radiation/dewpoint fields from GRIDMET are desired.

**Recommendation**
- Use this when you specifically want GRIDMET-native observed fields or need to compare sensitivity against DAYMET.
- If you want one default historical option, prefer **Observed DAYMET (GRIDMET wind)** first.

**Data it uses**
- GRIDMET observed daily climate fields.
- Observed year window you provide.

**Where available**
- Catalog description: **1980 to present**.
- Blocked in GHCN-only configured locales (`au`, `alaska`, `hawaii`, `nigeria`).

**Station selection modes available**
- Auto (`-1`), Distance ranking (`0`), Multi-factor ranking (`1`).

**Spatial modes available**
- Single (`0`), Multiple (`1`), Multiple Interpolated (`2`).

**Notes**
- In **Multiple** mode (`1`), PRISM revision is applied after base build.
- In **Multiple Interpolated** mode (`2`), build uses the GRIDMET interpolated hillslope workflow.
- Marked RAP-compatible in the current catalog.

## DEP NEXRAD Breakpoint

**Suitable for**
- Observed breakpoint-style climate workflows where high-resolution breakpoint data is required.
- Cases where you may want to override daily variables with PRISM/GRIDMET/DAYMET options.

**Data it uses**
- DEP Mesonet breakpoint climate retrieval by centroid/hillslope coordinates.
- Optional daily-variable overrides:
  - PRISM (`tmax`, `tmin`, `tdew`)
  - GRIDMET (`tmax`, `tmin`, `rad`, `tdew`, `w-vl`, `w-dir`)
  - DAYMET (`tmax`, `tmin`, `rad`, `tdew`)

**Where available**
- Help text indicates **2007 to present** coverage.
- Blocked in GHCN-only configured locales (`au`, `alaska`, `hawaii`, `nigeria`).

**Station selection modes available**
- Auto (`-1`), Distance ranking (`0`), Multi-factor ranking (`1`).

**Spatial modes available**
- Single (`0`), Multiple (`1`).

**Notes**
- Not marked RAP-compatible in the current catalog.

## Future CMIP5

**Suitable for**
- Climate-change impact analysis using projected (not historical observed) climate forcing.

**Data it uses**
- CMIP5/RCP8.5 timeseries retrieval.
- CLIGEN station + generated observed-style `.prn` -> `.cli` workflow.

**Where available**
- Blocked in GHCN-only configured locales (`au`, `alaska`, `hawaii`, `nigeria`).
- Future-year inputs are constrained in code to **2006 to 2099**.

**Station selection modes available**
- Auto (`-1`), Distance ranking (`0`), Multi-factor ranking (`1`).

**Spatial modes available**
- Single (`0`), Multiple (`1`).

**Notes**
- Labeled experimental in current help text.
- Not marked RAP-compatible in the current catalog.

## User-Defined Climate (.cli)

**Suitable for**
- Research and validation runs where you already have a vetted CLIGEN `.cli` file.

**Data it uses**
- Your uploaded `.cli` file.

**Where available**
- Generally available as a user-exposed dataset.

**Station selection modes available**
- User-defined (`4`) only.

**Spatial modes available**
- Single (`0`), Multiple (`1`).

**Notes**
- In this mode, **Upload .cli** is the primary action.
- Climate build button behavior differs from other modes (upload-driven flow).
- If spatial mode is **Multiple**, PRISM revision is applied after upload processing.

## E-OBS Modified (Europe)

**Suitable for**
- European observed-climate workflows.

**Data it uses**
- E-OBS-based modified climate build path for EU locales.

**Where available**
- EU-only (`allowed_locales = eu`).

**Station selection modes available**
- Auto (`-1`), Distance ranking (`0`), Multi-factor ranking (`1`), EU heuristic (`2`).

**Spatial modes available**
- Single (`0`), Multiple (`1`).

**Notes**
- Default spatial mode is Multiple in current catalog metadata.
- Not marked RAP-compatible in current catalog.

## Region/System-Managed Climate Options

These catalog options exist in code but are not normally exposed in the standard Climate Options dataset picker:

- `Observed Climate Database` (`observed_db`, mode 6)
- `Future Climate Database` (`future_db`, mode 7)
- `AGDC (Australia)` (`agdc`, mode 10)

These are `ui_exposed=False` in the current catalog and are primarily system/configuration driven.

## Station Selection Mode

Station selection mode controls how WEPPcloud chooses or ranks station candidates for the selected dataset.

## Auto (-1)

**What it does**
- Uses FindClosestAtRuntime behavior.
- The station dropdown is not actively refreshed from ranking endpoints in this mode.

**When to use**
- Default workflow when you do not need to inspect or force ranked station choices.

**Where available**
- Most non-user-defined datasets.

## Distance ranking (0)

**What it does**
- Calls the closest-stations endpoint and ranks candidates by distance to the watershed centroid.

**When to use**
- When nearest-station proximity is your primary criterion.

**Where available**
- Most standard datasets and several system-managed datasets.

## Multi-factor ranking (1)

**What it does**
- Calls heuristic station ranking.
- For `eu` locale this routes to EU heuristic logic; for `au` locale it routes to AU heuristic logic.

**When to use**
- When representativeness is more important than pure distance.

**Where available**
- Available where the selected dataset includes station mode `1`.

## EU heuristic (2)

**What it does**
- Uses the dedicated EU heuristic endpoint.

**When to use**
- European runs where explicit EU heuristic ranking is desired.

**Where available**
- In the current catalog, effectively tied to `E-OBS Modified (Europe)`.

## AU heuristic (3)

**What it does**
- Dedicated AU heuristic endpoint exists in backend.

**When to use**
- Australia-specific heuristic ranking (advanced/specialized contexts).

**Where available**
- Backend supports it, but current shipped dataset metadata does not generally expose mode `3` directly.
- In `au` locale, multi-factor mode (`1`) already routes to AU heuristic search logic.

## User-defined (4)

**What it does**
- Used with uploaded user-defined `.cli` workflows.
- Station list refresh is skipped and station select options are cleared in that flow.

**When to use**
- When supplying your own climate file.

**Where available**
- `User-Defined Climate (.cli)` dataset.

## Tenerife-specific station mode constraints

When a run uses the Tenerife station catalog (`tenerife_stations.db`), runtime constraints intentionally narrow options:

- Supported dataset options are reduced to `vanilla_cligen` and `user_defined_cli`.
- Station modes are reduced to:
  - `(-1, 0)` for `vanilla_cligen`
  - `(4)` for `user_defined_cli`
- Unsupported climate/spatial/station combinations are rejected by backend validation.

## How CLIGEN Uses `.par` and `.prn` Files

CLIGEN is the weather engine that produces the `.cli` file WEPP uses.

## `.par` files

A station `.par` file stores long-term monthly climate statistics (for example mean precipitation, wet/dry transition probabilities, and monthly temperature arrays). In WEPPcloud:

- Your station selection resolves to station metadata that includes the `.par` path.
- The **Station PAR preview** panel in Climate Options shows the active station `.par` contents.

## `.prn` files in observed workflows

In observed modes, WEPPcloud typically:

1. Builds daily observed series from a source dataset.
2. Writes those daily values into CLIGEN `.prn` format.
3. Calls CLIGEN `run_observed(...)` to generate the final `.cli`.

This pattern is used across observed DAYMET, observed GRIDMET, PRISM-observed style paths, SNOTEL-support paths, and interpolated observed workflows.

## Input file specifications

- [CLIGEN station statistics format (`.par`)](../input-file-specifications/cligenparms.md)
- [Climate file specification (`.cli` and breakpoint structure)](../input-file-specifications/climate-file.spec.md)

## Spatial Climate Modes

## Single climate (0)

**What it does**
- Builds one climate for the watershed.

**When to use**
- Fastest option.
- Good default for many small-to-medium watersheds.

## Multiple climates (1)

**What it does**
- Produces per-hillslope climate outputs.
- For many modes, this applies the PRISM revision routine after base climate build.

**What PRISM revision does (plain language)**
- Retrieves PRISM `ppt`, `tmin`, and `tmax` rasters for the watershed extent.
- Computes watershed-level monthly values and hillslope-level monthly values.
- Revises the base climate to hillslope-specific climates using monthly precipitation scaling plus monthly temperature offsets.

## Multiple climates (Interpolated) (2)

**What it does**
- Uses dedicated interpolated observed-climate build paths.
- Supported only for observed DAYMET / observed GRIDMET mode families (`ObservedPRISM` / `GridMetPRISM`).

**When to use**
- When spatial heterogeneity is important and you are on supported observed modes.

**Performance and practical guidance**
- Slower than Single.
- In operator experience, this mode has produced some of the best calibrated results for certain Pacific Northwest watersheds.
- It is often a strong candidate for larger watersheds or watersheds with micro-climate variation.

## Recommended spatial-mode decision path

1. Start with **Single** for speed and first-pass calibration.
2. Move to **Multiple** when hillslope-scale variation appears important.
3. Try **Multiple Interpolated** on supported observed modes when you need higher spatial climate fidelity and can afford extra runtime.

## Advanced Options

Advanced options are visible for non-Tenerife station-catalog workflows.

## Use GRIDMET wind when applicable

**Function**
- Toggles the run-level `use_gridmet_wind_when_applicable` behavior.

**Purpose**
- Injects GRIDMET wind fields for observed workflows that require wind support.

**Recommended use cases**
- Enable when observed mode requires wind forcing and GRIDMET wind is appropriate.

## Adjust MX .5 P Values

**Function**
- Toggles `adjust_mx_pt5` behavior during CLIGEN observed processing.

**Purpose**
- Scales monthly `MX .5 P` intensity values based on observed/localized monthly precipitation ratio logic.

**Recommended use cases**
- When station-normal intensity assumptions appear mismatched with your local observed precipitation behavior.

**Important behavior details**
- Scaling is constrained in code (clamped to a bounded factor range).
- Very low-precipitation months can be skipped by adjustment logic.
- If CLIGEN still fails to converge, the run surfaces: `CLIGEN failed to converge, try selecting different station or setting Adjust MX .5 P Values`.

## Silent-pass observed quality guard

**Function**
- Toggles `silent_pass_observed_quality_guard` for observed CLIGEN build paths.

**Purpose**
- When enabled, WEPPcloud keeps the generated `.cli` even if CLIGEN logs quality-guard convergence markers.

**Recommended use cases**
- Advanced troubleshooting when you need a run to continue and can review warning context in the climate report summary and status panel.

**Important behavior details**
- Default is enabled (`true`), so climate build continues when CLIGEN quality-guard markers are detected.
- When this bypass occurs, WEPPcloud shows a warning in the climate report summary and publishes the same warning to the climate status stream.
- Disable this option if you want quality-guard failures to stop the build with a user-facing convergence message.

## Post-CLIGEN precipitation scaling modes

## No scaling (0)

**Function/Purpose**
- No precipitation scaling is applied after build.

**Recommended use case**
- Baseline control runs.

## Scalar scaling (1)

**Function/Purpose**
- Applies one scalar multiplier (`precip_scale_factor`) to precipitation.

**Recommended use case**
- Fast sensitivity analysis (for example +/- 10%).

## Monthly scaling (2)

**Function/Purpose**
- Applies 12 month-specific multipliers.

**Recommended use case**
- Seasonal bias correction.

## Reference scaling (3)

**Function/Purpose**
- Derives monthly scaling from a selected reference dataset (`prism`, `daymet`, or `gridmet`) over your observed year window.

**Recommended use case**
- Aligning generated precipitation totals with an external gridded climate reference.

**Important constraints**
- For PRISM reference scaling, start year must satisfy PRISM availability constraints in validation.

## Spatial scaling from map (4)

**Function/Purpose**
- Uses a scale-factor raster map path to apply spatially varying precipitation scaling.

**Recommended use case**
- Advanced workflows with vetted external scale-factor maps.

**Important constraints**
- Map path must exist.
- Out-of-range scale factors are skipped.
- In current UI this option is present but disabled/read-only for most users.

## Practical tuning guidance

1. Change one advanced setting at a time.
2. Rebuild climate and rerun WEPP.
3. Compare calibration metrics after each change.
4. Record the setting change and rationale for reproducibility.
