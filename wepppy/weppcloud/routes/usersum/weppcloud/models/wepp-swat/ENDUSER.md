# WEPP-SWAT+

WEPP-SWAT+ combines two model layers in one workflow: WEPP generates daily hillslope runoff and sediment, and SWAT+ routes those hillslope loads through the channel network. Use it when plain WEPP is not enough because channel-routing behavior is part of the question you need to answer.

## What Extends Beyond Standard WEPP

Standard WEPP already gives you hillslope results and, when enabled, watershed/channel routing within WEPP. WEPP-SWAT+ adds a second routing stage:

- WEPP remains the hillslope generator,
- SWAT+ receives WEPP daily outputs as recall inputs,
- SWAT+ routes water and sediment through its channel network.

That means a WEPP-SWAT+ result should be read as:

1. hillslope generation from WEPP, then
2. channel routing from SWAT+.

## What You Actually See In The UI

When a run is SWAT-enabled, the main control title becomes `WEPP-SWAT+` and the main run button becomes `Run WEPP-SWAT+`.

The additional user-facing SWAT controls appear under `SWAT+ Advanced Options`:

- `Hydraulic-Sediment Parameters`
  - `Channel Manning's n (mann)`
  - `Floodplain Manning's n (fpn)`
  - `Channel erodibility factor (erod_fact)`
  - `Channel cover factor (cov_fact)`
  - `Median bed material size (d50)`
- `SWAT Print.prt`
  - header fields such as `nyskip`, `day_start`, `yrc_start`, `day_end`, `yrc_end`, `interval`
  - per-object output toggles for `daily`, `monthly`, `yearly`, and `avann`
- `SWAT Exec`
  - `Run SWAT+`

If `Bootstrap` is enabled, users can also see:

- `Run SWAT+ Channel Routing`

The visible SWAT controls are not per-channel editors. They are run-scoped controls layered on top of the existing WEPP form:

| UI control | What the user is changing | Why it matters |
| --- | --- | --- |
| `Channel Manning's n (mann)` | A uniform roughness override applied to all SWAT-DEG channel records in `hyd-sed-lte.cha` | Higher roughness generally slows routing and attenuates peaks |
| `Floodplain Manning's n (fpn)` | A uniform floodplain roughness override | Only matters when overbank routing is important; leaving it blank preserves the template default |
| `Channel erodibility factor (erod_fact)` | A uniform channel erodibility override | Higher erodibility generally raises routed sediment production |
| `Channel cover factor (cov_fact)` | A uniform SWAT channel cover/armoring parameter | This is calibration-sensitive and can materially change routed sediment behavior; treat it as a routing parameter, not a simple land-cover label |
| `Median bed material size (d50)` | A uniform bed-material-size override in millimeters | Larger material generally reduces transport efficiency and makes the bed harder to move |
| `nyskip`, `day_start`, `yrc_start`, `day_end`, `yrc_end`, `interval` | The output window and write cadence for `print.prt` | Controls how much SWAT output is written and for which years or dates |
| Per-object `daily`, `monthly`, `yearly`, `avann` checkboxes | Which time scales are written for each SWAT object row | Useful for QA and routing review; does not change model physics |

The key assumption behind this UI is that the five hydraulic-sediment parameters are **uniform overrides**. The standard end-user surface does not expose per-order, per-reach, or per-material parameterization.

## What The UI Actions Trigger

Several visible controls trigger different API-backed actions:

1. `Run WEPP-SWAT+`
   This posts the current form to `/rq-engine/api/runs/<runid>/<config>/run-wepp`. In other words, the main combined button is still backed by the WEPP run route. In a SWAT-enabled run, the submitted form includes both WEPP settings and any SWAT channel-parameter overrides currently shown in the form.

2. `Run SWAT+`
   This posts to `/rq-engine/api/runs/<runid>/<config>/run-swat`. Use it when WEPP hillslope outputs already exist and you want to rebuild/run the SWAT+ routing side without rerunning hillslopes.

3. `Run SWAT+ Channel Routing` in `Bootstrap`
   This uses `/rq-engine/api/runs/<runid>/<config>/run-swat-noprep` and assumes you already have a bootstrapped input checkout that you intentionally edited.

4. Changing `SWAT Print.prt`
   These edits are saved immediately, not only on full run. Object checkboxes post to `/rq-engine/api/runs/<runid>/<config>/swat/print-prt`, and the print header fields post to `/rq-engine/api/runs/<runid>/<config>/swat/print-prt/meta`.

## The Most Important UI Controls

| UI control | What it means | Why it matters |
| --- | --- | --- |
| `Channel Manning's n (mann)` | Roughness for the routed channel | Higher values generally slow routing and dampen peaks |
| `Floodplain Manning's n (fpn)` | Roughness for floodplain flow when overbank routing matters | Higher values increase overbank resistance |
| `Channel erodibility factor (erod_fact)` | Ease of erosion in the routed channel | Higher values generally increase routed sediment production |
| `Channel cover factor (cov_fact)` | SWAT channel cover or armoring parameter | Treat this as a calibration-sensitive sediment-routing parameter rather than a simple "more cover/less cover" switch |
| `Median bed material size (d50)` | Representative bed-material size | Larger material generally makes transport and detachment harder |
| `SWAT Print.prt` header fields | Which years or dates are written and how often | Useful when you only need a subset of the record or want to avoid oversized outputs |
| `SWAT Print.prt` toggles | Which SWAT outputs are written and at what time scale | Useful for QA, routing review, and keeping outputs manageable |

## What The `SWAT Print.prt` Fields Actually Do

The `SWAT Print.prt` table is easy to misread because it looks technical and does not change routing directly.

- `nyskip` controls how many early years SWAT skips before writing outputs.
- `day_start` and `yrc_start` define the first day and year written.
- `day_end` and `yrc_end` define the last day and year written.
- `interval` controls the write interval for supported output frequencies.
- The object rows are raw SWAT object names. Their `daily`, `monthly`, `yearly`, and `avann` checkboxes only control which text outputs SWAT writes on the next build.

Use these controls to inspect the WEPP-to-SWAT handoff, channel routing response, or recall outputs. Do not expect them to fix routing behavior by themselves.

## How To Use It Well

Use the workflow in this order:

1. Make sure the WEPP hillslope setup is already defensible.
   If the hillslope forcing is wrong, better SWAT routing will not fix that.

2. Decide whether you need a combined run or a SWAT-only rerun.
   Use `Run WEPP-SWAT+` when hillslope inputs or WEPP options changed. Use `Run SWAT+` when the hillslope outputs already exist and you only changed SWAT-side settings. This distinction matters because the main combined button is still backed by the WEPP route, while `Run SWAT+` is the explicit SWAT rerun surface.

3. Adjust only the SWAT channel parameters you can defend.
   Manning roughness, erodibility, cover factor, and D50 can change results substantially.

4. Turn on extra `SWAT Print.prt` outputs only when they answer a question.
   For example, enable recall outputs when you need to verify the WEPP-to-SWAT handoff.

## Core Assumptions And Remaining Limits

- The handoff from WEPP to SWAT+ is daily, not sub-daily. This is a routing workflow built on daily hillslope forcing.
- WEPP provides the hillslope runoff and sediment time series; SWAT+ does not replace WEPP hillslope physics.
- The current handoff focuses on hydrology and sediment. Nutrients, pesticides, and similar constituents are set to zero unless explicitly supported.
- Channel connectivity is derived from the watershed abstraction and hillslope-to-channel mapping, not from a separate surveyed hydraulic network.
- Channel geometry is partly derived from watershed geometry and empirical relationships; some channel properties still need literature-based selection or calibration.
- The visible `Hydraulic-Sediment Parameters` are uniform overrides applied across the routed network. The default UI does not let you vary them by reach, order, or material class.
- SWAT routing uses the SWAT-DEG channel object set. That is an implementation choice with its own assumptions about channel representation.
- Changing `print.prt` changes what SWAT writes out, not how the model routes flow.

## How To Interpret Results

A difference between WEPP and WEPP-SWAT+ does not automatically mean one model is "right" and the other is "wrong." It often means:

- the hillslope forcing is the same, but
- the channel-routing assumptions differ.

That is why the most useful interpretation is usually:

- what changed after routing,
- whether those changes are physically plausible,
- whether the SWAT-side channel assumptions are strong enough for the decision you are making.

## Related Docs

- [WEPP](../wepp/ENDUSER.md)
- [Mods Overview](../../mods-overview.md)
- [Getting Started](../../getting-started.md)
