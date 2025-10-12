# Observed Model Fitting

The Observed Model Fit tool compares measured watershed responses against a completed WEPP Cloud simulation. It aggregates modelled hillslope and channel outputs via the interchange Parquet assets and computes daily and annual skill metrics for each supplied observed measure.

## Prerequisites

- A completed WEPP Cloud run for the project.
- Observed outlet data for at least one supported measure.
- A climate configuration that exposes observed years (the control remains hidden until observed climate data are available).

## Preparing Observed Data

Paste comma-delimited text into the Observed control. The first column must be `Date` in `MM/DD/YYYY` format. Include any subset of these columns you want to evaluate:

- `Streamflow (mm)`
- `Sed Del (kg)`
- `Total P (kg)`
- `Soluble Reactive P (kg)`
- `Particulate P (kg)`

Column names must match exactly, including units. Rows with blank values are ignored. Extra columns are ignored.

### Example CSV snippet

```
Date,Streamflow (mm),Sed Del (kg)
01/03/2016,0.8,12.4
01/04/2016,1.5,18.0
01/05/2016,,17.2
```

The blank entry on 01/05 is skipped during fitting.

## Running the Fit

1. Navigate to the  **Observed** Control for the active run.
2. Paste the prepared CSV text into the **Observed Timeseries** field.
3. Click **Run Model Fit**. The job is dispatched to the WEPP Cloud queue.
4. When processing completes, follow the “View Model Fit Results” link.

## Report Contents

The generated report includes:

- Daily and annual statistics (NSE, PBIAS, RMSE, etc.) for each provided measure.
- Counts of valid observations used in each comparison.
- Downloadable CSV summaries saved under the project’s `observed/` directory.

## Troubleshooting

- **Control hidden** – Ensure the climate configuration advertises observed years and that the WEPP run finished successfully.
- **Parsing failure** – Confirm the header includes the `Date` column plus supported measure names and that the file is comma-separated.
- **Empty report** – Only overlapping calendar days between the observed file and the simulated series are scored; unmatched dates are dropped.
