# Revegetation

Revegetation lets you replace the default "use observed post-fire cover as-is" assumption with an explicit cover-recovery scenario before running WEPP. It is for users who want to test how different vegetation recovery paths change modeled runoff and erosion after disturbance.

## What You Actually See In The UI

When the workflow is enabled, the control appears under `WEPP Advanced Options` as `Revegetation Scenarios`. The user-facing controls are:

- `Cover transformation scenario`
  - `Observed`
  - `20-Year Recovery`
  - `20-Year Partial Recovery`
  - `User-Defined Transform`
- `Upload cover transform file (.csv)` which only appears after `User-Defined Transform` is selected

These are the labels the user sees. The run is still executed from the normal WEPP controls.

## When To Use Each Scenario Option

| UI option | What it means | Best use |
| --- | --- | --- |
| `Observed` | Uses the available RAP-derived cover time series without applying a transform; the underlying API value is an empty `reveg_scenario` | Use when you want the project to follow the observed cover record directly |
| `20-Year Recovery` | Applies the built-in full-recovery style transform curve; the underlying built-in file is `20-yr_Recovery.csv` | Use when you want a stronger assumed recovery trajectory than the observed record |
| `20-Year Partial Recovery` | Applies the built-in partial-recovery curve; the underlying built-in file is `20-yr_PartialRecovery.csv` | Use when you expect slower or incomplete recovery |
| `User-Defined Transform` | Lets you upload your own transform CSV; the selector uses the `user_cover_transform` mode until a file is uploaded | Use when local expertise, field evidence, or planning assumptions justify a custom recovery curve |

## What The UI Actions Trigger

There are two separate user actions:

1. Choosing a built-in scenario
   The selection is sent with the next WEPP action as `reveg_scenario` to the WEPP run or prep endpoints such as `/rq-engine/api/runs/<runid>/<config>/run-wepp` or `/rq-engine/api/runs/<runid>/<config>/prep-wepp-watershed`.

2. Uploading a custom CSV
   The file upload happens immediately when you choose a file. The browser posts it to `/rq-engine/api/runs/<runid>/<config>/tasks/upload-cover-transform`, which saves the CSV under the run and marks it as the active user-defined transform.

That means picking `User-Defined Transform` by itself does not change the model. The uploaded file becomes active, and the change takes effect on the next WEPP prep or run. Likewise, simply changing the dropdown to a built-in scenario does not execute anything until the next WEPP prep or run submits that selection.

## How The Cover Transform Actually Works

This workflow does not create a new vegetation model. It rescales the post-fire RAP cover trajectory that WEPP preparation uses.

At a practical end-user level:

- the transform is anchored to the fire-year cover baseline,
- years before the fire are left alone,
- years after the fire are scaled by the scenario curve,
- only the years already available in the run's RAP and climate data are modeled.

Important consequences:

- choosing a `20-Year ...` scenario does not make the project run for 20 years if the climate and RAP inputs are shorter,
- the transform changes cover assumptions, not soils, topography, or climate,
- if your custom CSV does not include every burn-class and vegetation-class combination, the missing combinations are left unchanged.

## User-Defined Transform Upload Guidance

Use `User-Defined Transform` only if you can defend the curve you are uploading.

The current upload path expects a `.csv` file and stores it under the run's `revegetation/` folder. The downstream parser expects:

- the first row to identify burn-severity classes,
- the second row to identify vegetation labels,
- later rows to hold year-by-year scale factors.

For end users, the important operational limits are:

- upload validation is light at upload time,
- a file can upload successfully and still produce poor or confusing results later if the class names or structure do not match what preparation expects,
- if the curve ends before the modeled period ends, the last factor is carried forward.

## How To Interpret Results

Read revegetation as a scenario-comparison tool, not a source of truth.

In general:

- earlier or stronger cover recovery usually reduces runoff and sediment,
- slower or partial recovery usually keeps post-fire response elevated for longer,
- small differences between scenarios do not necessarily mean the transform failed.

Small differences can happen when:

- the modeled period is short,
- cover is not the dominant control in that watershed,
- the transformed cover does not change the limiting canopy condition enough to change erosion materially.

## Core Assumptions And Limits

- Revegetation does not extend simulation length beyond the available climate and RAP years.
- It changes post-fire cover assumptions only. It does not directly change weather, soils, burn severity mapping, or treatment effects.
- The transform is based on burn class and vegetation class, not on a fully dynamic plant-community process model.
- In WEPP, the resulting cover series acts as a canopy constraint in the growth logic rather than a guarantee that field canopy will exactly match the uploaded percentages every day.
- If the fire date or disturbance context is wrong, the scenario comparison will also be wrong.

## Decision Guidance

Use `Observed` when your main goal is to honor the available record.

Use `20-Year Recovery` or `20-Year Partial Recovery` when you need structured planning scenarios and do not have a site-specific curve.

Use `User-Defined Transform` only when you can explain where the curve came from and why it is more appropriate than the built-in choices.

## Related Docs

- [WEPP](../wepp/ENDUSER.md)
- [WEPP Advanced Options](../../wepp-advanced-options.md)
- [Getting Started](../../getting-started.md)
