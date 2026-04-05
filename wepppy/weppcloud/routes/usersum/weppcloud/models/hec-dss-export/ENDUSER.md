# HEC-DSS Export

The `Partitioned DSS Export for HEC` workflow packages existing routed WEPP outputs into HEC-DSS files and supporting sidecar files for downstream HEC workflows. It is an export step, not a new model run.

## What You Actually See In The UI

The DSS export control is titled `Partitioned DSS Export for HEC`. The user-facing inputs are:

- `Start date (optional)`
- `End date (optional)`
- `Export mode`
  - `Export select channels`
  - `Export based on channel order`
- when `Export select channels` is chosen:
  - `Channel Topaz IDs to export`
- when `Export based on channel order` is chosen:
  - `Exclude channel orders` with checkboxes `1` through `5`
- `Export DSS`

The download link appears only after the job completes:

- `Download DSS Export Results (.zip)`

## What Each Export Option Means

| UI control | What it means | When to use it |
| --- | --- | --- |
| `Start date (optional)` | Lower date bound for the exported series | Use when you only need part of the modeled record |
| `End date (optional)` | Upper date bound for the exported series | Use when your HEC study window is shorter than the full WEPP run |
| `Export select channels` | Export only the channels you name explicitly | Use when you already know the exact Topaz channel IDs you need |
| `Channel Topaz IDs to export` | Comma-separated list of channel IDs | Use for tightly targeted exports |
| `Export based on channel order` | Export every eligible channel except the orders you exclude | Use when you want a broad export filtered by network size/order |
| `Exclude channel orders` | Removes selected Strahler orders from the export set | Use to omit small headwater channels or other orders you do not want in the package |

For stochastic climates, the help text matters: use simulation year numbering in the DSS date fields rather than real calendar years.

## What The Export Button Triggers

Clicking `Export DSS` posts the current export settings to:

`/rq-engine/api/runs/<runid>/<config>/post-dss-export-rq`

The controller normalizes the form before submitting:

- channel lists are parsed into positive integer channel IDs,
- excluded orders are collected into an order list,
- dates are passed as optional strings,
- mode `2` derives the actual channel list from watershed channel order rather than using a manual list.

The route validates:

- dates must be `MM/DD/YYYY`,
- start date must be on or before end date,
- channel IDs must be positive integers.

If validation passes, WEPPcloud stores the DSS export settings on the run, queues the DSS export job, and publishes the finished zip under `browse/export/dss.zip`.

## What You Get In The Zip Package

The package is centered on `export/dss.zip`. The export directory typically contains:

- `totalwatsed3_chan_<id>.dss`
  daily DSS series for each exported channel
- `peak_chan_<id>.dss`
  irregular peak-flow DSS series derived from channel output
- `sed_vol_conc_by_event_and_chn_id.csv`
  per-channel tabular sidecar with sediment and ash concentration fields when available
- `dss_channels.geojson`
  exported channel geometries plus DSS/HEC metadata
- `boundaries/bc_<id>.gml` and boundary shapefile sidecars
  boundary-condition helper files for downstream HEC work
- `README.dss_export.md`
  export-specific technical notes copied into the package

Some runs may also include channel-buffer products when that generation step succeeds.

## What You Are Not Getting

This package does **not** give you a complete HEC-RAS or HEC-HMS project. In particular, the export is not:

- a rerun of WEPP,
- observed gage data,
- surveyed geometry,
- cross sections, terrain, or a finished hydraulic model,
- a guarantee that channel names match your local naming convention.

It is a WEPP-derived time-series package plus helper geometry and boundary sidecars.

## How To Choose An Export Mode

Use `Export select channels` when:

- you already know the exact Topaz IDs you need,
- you are handing off only a few locations,
- you do not want small upstream channels included accidentally.

Use `Export based on channel order` when:

- you want a systematic export for many channels,
- order is a better filter than hand-entering IDs,
- you want to exclude the smallest or least relevant channels quickly.

## How To Interpret The Results

The DSS files contain modeled WEPP outputs. Treat them as scenario-based hydrologic inputs, not measurements.

Two series types matter:

- `totalwatsed3_chan_<id>.dss`
  daily channel series suitable for continuous-style review
- `peak_chan_<id>.dss`
  irregular peak-flow series derived from channel routing output

Before using the package downstream, verify:

- the channel set is the one you intended,
- the date range matches the study window,
- your HEC workflow is using daily versus peak series for the right purpose.

## Core Assumptions And Limits

- The export is only as good as the underlying WEPP run.
- Channel IDs follow the modeled watershed structure in WEPPcloud.
- Filtering by channel order is based on modeled network order, not on local naming or management importance.
- Missing or weak WEPP channel outputs will carry directly into the DSS package.
- The package helps with HEC handoff, but it does not remove the need for downstream hydraulic setup and review.

## Related Docs

- [WEPP](../wepp/ENDUSER.md)
- [Mods Overview](../../mods-overview.md)
- [WEPP Interchange Outputs](../../wepp-interchange.md)
