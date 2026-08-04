# Return period analysis (user-provided exports)
Use this when a WEPPcloud user asks “why are the 2/5/10-year peak flows higher in scenario A than B?” and you need an event-by-event comparison.

## What to ask the user to provide

For each scenario (burned and undisturbed):
- `ebe_pw0.txt` (event-by-event file that includes peak discharge).

If the `ebe_pw0.txt` file uses simulation years (1..N) instead of calendar years, also ask for the climate start year (or the climate period shown in the UI).

## What to generate

Run:
- `scripts/return_period_compare.py --burned-ebe <burned_ebe_pw0.txt> --undisturbed-ebe <undisturbed_ebe_pw0.txt> --start-year <yyyy>`

Outputs (in the script’s output folder):
- CTA and AM peak-discharge return period tables (2/5/10-year by default)
- Event-date comparison tables
- Histogram overlay plot for peak discharge event distributions
