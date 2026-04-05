# WEPP Interchange Outputs

WEPP interchange is the machine-friendly export of WEPP results. WEPPcloud converts WEPP text reports into Parquet tables so dashboards, reports, and analysis tools can open the results quickly without reparsing the raw text files each time.

## What This Page Helps You Do

Use this page when you want to find the main model-result tables in a run and understand which interchange files are most useful for hillslope, watershed, event, and channel questions.

## Where To Look

The main interchange folder is usually:

- `wepp/output/interchange/`

Some workflows also produce parallel outputs in other model scopes. For example, roads workflows commonly use:

- `wepp/roads/output/interchange/`

The files in these folders are usually Parquet tables. Parquet is a columnar table format that opens efficiently in dashboards, analysis notebooks, and query tools.

## What Parquet Tables Are

Parquet tables are binary data files that store results in a structured table format, similar to a spreadsheet or database table. Instead of saving WEPP results as large text reports that must be reread line by line, WEPPcloud stores many outputs as Parquet so software can jump directly to the columns and rows it needs.

## Why They Are Useful For WEPP Outputs

Parquet is a good fit for WEPP outputs because it makes repeated analysis much easier.

- smaller file size: binary storage and compression usually make Parquet files much smaller than the original text outputs
- faster reading: tools can read only the columns they need instead of loading an entire report
- faster queries: dashboards and query tools can scan Parquet tables quickly for summaries, filters, joins, and time-series analysis
- better interoperability: Parquet is widely supported in Python, R, DuckDB, GIS workflows, and other analytics tools
- one conversion, many uses: WEPPcloud can convert the raw model reports once, then reuse the same Parquet tables for reports, dashboards, downloads, and advanced analysis

For most users, the practical result is that WEPP outputs open faster, compare more easily, and are more convenient to analyze than the original WEPP text files.

## Common Interchange Files

| File | What it usually represents | Common use |
| --- | --- | --- |
| `H.wat.parquet` | Hillslope water-balance results | Review runoff, infiltration, and water-balance behavior by hillslope |
| `H.soil.parquet` | Hillslope soil-state results | Review modeled soil-water and soil-condition variables |
| `H.pass.parquet` | Hillslope daily runoff and sediment-pass results | Compare daily hillslope response across hillslopes |
| `H.ebe.parquet` | Hillslope event-by-event results | Review hillslope response for runoff-producing events |
| `H.loss.parquet` | Hillslope sediment-loss summary output | Check hillslope sediment behavior |
| `loss_pw0.hill.parquet` | Watershed hillslope loss summary | Compare long-term modeled hillslope losses across the watershed |
| `loss_pw0.chn.parquet` | Channel loss summary | Review channel contributions and routing effects |
| `loss_pw0.out.parquet` | Watershed outlet summary | Check modeled outlet runoff and sediment delivery |
| `pass_pw0.events.parquet` | Watershed event list | Find runoff-producing or sediment-producing events |
| `pass_pw0.metadata.parquet` | Watershed event metadata | Review event descriptors and supporting event information |
| `ebe_pw0.parquet` | Watershed event-by-event output | Review detailed event-scale watershed response |
| `chan.out.parquet` | Channel peak-flow output | Review channel peak timing and magnitude |
| `chanwb.parquet` or `chnwb.parquet` | Channel water-balance output | Review routed flow and channel-balance behavior |
| `totalwatsed3.parquet` | Watershed-wide daily water and sediment budget table | Support summary analysis, exports, and downstream tools |

## Where To Start For Common Questions

| If you want to find... | Start here |
| --- | --- |
| Hillslope daily water-balance results | `H.wat.parquet` |
| Hillslope event response | `H.ebe.parquet` |
| Watershed outlet sediment and runoff summary | `loss_pw0.out.parquet` |
| Event-scale watershed output | `ebe_pw0.parquet` |
| Channel peak flow | `chan.out.parquet` |
| Watershed-wide daily budget table | `totalwatsed3.parquet` |

## Limits and Common Mistakes

- Not every run has every interchange file. The available files depend on the workflow, model scope, and completed post-processing steps.
- Interchange files are modeled outputs, not observed measurements.
- Hillslope tables and watershed tables answer different questions. Do not treat a hillslope file as if it were a watershed outlet file.
- Some workflows write similar outputs in a parallel folder such as `wepp/roads/output/interchange/`, so check the model scope before comparing files.
- These files are intended for reading, browsing, and analysis. Editing them by hand can break downstream tools.

## Related Docs

- [WEPPcloud Runs Directory Structure](weppcloud-runs-directory-structure.md)
- [Profile JWT Dataset Access (Python/R)](profile-jwt-dataset-access-python-r.md)
- [WEPP Model](wepp-model.md)
