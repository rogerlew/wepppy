# Debris Flow

Use **Debris Flow Analysis** when you need a fast post-fire hazard screen for whether a burned watershed is likely to produce a debris flow, and how large that event could be under different storm frequencies and storm durations. In WEPPcloud this is an empirical screening workflow built around the Cannon et al. (2010) probability and volume equations, not a physics-based runout or inundation model.

## What This Is For

Use this workflow to answer questions such as:

- Is this burned basin likely to produce a debris flow under short, intense rainfall?
- How does the answer change if I use NOAA precipitation-frequency data instead of the Holden WRF Atlas?
- Does the result change materially if I override the default soil clay content or liquid limit?

This tool is best for screening and prioritization. It helps decide where field review, warning planning, or more detailed hazard analysis is warranted.

## What You See In The UI

The control card is titled **Debris Flow Analysis**. The user-facing controls are:

| UI control | What the user sees | Why it matters |
| --- | --- | --- |
| `Clay Content Override (%)` | Optional numeric field | Replaces the clay percentage derived from the Soils workflow. Higher clay content increases the probability term in the current empirical equation. Leave blank to use the soil-derived value. |
| `Liquid Limit Override (%)` | Optional numeric field | Replaces the soil-derived liquid limit. Higher liquid limit lowers the probability term in the current equation. Leave blank to use the soil-derived value. |
| `Precipitation Datasource` | `Automatic (use available precipitation sources)`, `NOAA Precipitation Frequency Data Server`, or `Holden WRF Atlas` | Controls which precipitation-frequency table drives the storm totals and intensities used in the screening equations. |
| `Run Model` | Main action button | Starts the debris-flow job for the current watershed. |

If you leave **Precipitation Datasource** on `Automatic (use available precipitation sources)`, WEPPcloud fetches available precipitation-frequency data and chooses the default active source automatically. In the current implementation, NOAA is preferred when available; otherwise Holden becomes the active source.

## Before You Run It

Review these prerequisites first:

- The watershed geometry must already exist for the run.
- Burn severity must be available. The model uses moderate and high severity burned area from BAER or from the Disturbed workflow.
- Soils should already be built if you want the default clay-content and liquid-limit values to be meaningful.
- This workflow uses precipitation-frequency data at the watershed centroid, so very large or topographically complex basins may need extra judgment when comparing datasources.

## What The Button Actually Does

When you click **Run Model**, the UI submits a background request to the debris-flow rq-engine endpoint:

- `POST /rq-engine/api/runs/{runid}/{config}/run-debris-flow`

The submitted payload can include:

- `clay_pct`
- `liquid_limit`
- `datasource`

Blank override fields are omitted from the request. The route validates `clay_pct` and `liquid_limit` as numeric values, trims the datasource string, and then queues the debris-flow run. The job calculates watershed inputs, fetches precipitation-frequency tables, and computes debris-flow **probability of occurrence** and **volume** matrices for each available datasource.

## Choosing A Precipitation Datasource

The datasource choice is often the most important user decision in this workflow.

### `Automatic (use available precipitation sources)`

Use this when you want WEPPcloud to pick the first usable precipitation-frequency source for the basin. This is the least opinionated starting point and is appropriate for quick screening.

### `NOAA Precipitation Frequency Data Server`

Use this when you want the screening tied to NOAA precipitation-frequency values at the watershed centroid. In the current workflow, NOAA precipitation totals are converted to millimeters and then to rainfall intensity in `mm/hr` for each duration.

### `Holden WRF Atlas`

Use this when Holden WRF Atlas coverage is available and better matches your planning context. WEPPcloud reshapes Holden precipitation totals into duration-by-recurrence tables and then converts them to intensity in `mm/hr`.

### Practical guidance

- If both NOAA and Holden are available, compare both before making a management decision.
- If one datasource produces much higher short-duration intensity, it can materially raise the modeled probability.
- A datasource difference does not mean one answer is "correct" and the other is "wrong." It means the rainfall-frequency input assumption changed.

## Interpreting Probability And Volume

The report separates the two outputs because they answer different questions.

### Probability of occurrence

This is the modeled chance that a debris-flow-triggering event occurs for the listed storm duration and recurrence interval. Read it as a conditional screening probability for that storm scenario.

Do not read it as:

- the probability that debris flow happens this year,
- the probability that debris flow occurs somewhere on the map regardless of storm type,
- a guarantee that a debris flow will or will not happen.

### Predicted volume

This is the modeled debris-flow volume, shown in `m^3`, for the same storm scenario. It is an estimate of event magnitude from the empirical equation. It is not a mapped runout volume, deposition thickness, or channel-bulking simulation.

### Read them together

- High probability and high volume is a stronger screening concern than either metric alone.
- High probability with modest volume can still matter for infrastructure or channel blockage.
- Lower probability with very large volume can still justify field review where consequences are high.

## What You See In Results

After a successful run, the debris-flow report shows:

- **Debris Flow Summary** with `Watershed Area`, `Area >= 30% Slope (A)`, `Moderate & High Burn (B)`, `Ruggedness (R)`, `Clay Content (C)`, and `Liquid Limit (LL)`.
- **Probability and Volume Estimates**, organized by storm duration and recurrence interval.
- **Storm Intensity and Total Precipitation**, showing intensity in `mm/hr` and total storm depth in `mm`.

The report highlights cells when probability is at least 50 percent. Treat that as a visual cue, not as a formal hazard threshold.

The summary terms matter because they are the actual equation inputs:

- `A` is the basin area with slopes greater than or equal to 30 percent.
- `B` is the basin area burned at moderate and high severity.
- `R` is basin ruggedness.
- `C` is clay content.
- `LL` is liquid limit.

## Assumptions And Limits

- This is an empirical screening model based on watershed summary variables and precipitation-frequency inputs.
- It does not simulate debris-flow routing, travel path, deposition pattern, or inundation area.
- It does not replace a runout model, field reconnaissance, or consequence analysis.
- It relies on the quality of the burn severity map, watershed geometry, and soil properties already present in the run.
- If soil properties are missing or unusable, the controller falls back to default values for clay content and liquid limit. That makes the run possible, but confidence is lower than when real soil properties are available.
- Results are storm-scenario based. A 10-year recurrence row and a 100-year recurrence row are different conditional scenarios, not forecasts of exactly when a debris flow will occur.
- The UI itself notes that results may differ from newer formulations such as Staley (2016, 2017). Use that warning seriously if you are comparing methods across studies or agencies.

## When Not To Use This Alone

Do not use this workflow by itself when you need:

- a debris-flow path or runout map,
- a design-level estimate for infrastructure sizing,
- a regulatory or public-warning decision with no supporting field evidence,
- an event-by-event simulation tied to observed storm hyetographs at a specific site.

## Related Docs

- [WEPP](../wepp/ENDUSER.md)
- [Ash Transport](../ash-transport/ENDUSER.md)
- [Getting Started](../../getting-started.md)
