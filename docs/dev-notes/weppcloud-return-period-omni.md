# Omni comparisons in the return-period report

In the simple Return periods report, open **Configuration → OMNI Scenarios
Selection**, check completed scenarios, and choose **Run report**. Nothing is
selected by default. The current project always remains in the comparison.
Each metric table adds a Scenario column and lists each scenario's own event
dates and values. A return period need not select the same storm in every run.
**Download CSV** exports that metric's concatenated rows in the selected units.

Year/month filters, method, Gringorten correction, channel, custom recurrence
intervals, and output scope apply to every selected run. Selections survive
configuration changes. Clear all scenario checkboxes and run the report to
restore the single-project tables. Extraneous-parameter tables remain
single-project; hide extraneous parameters to return to the selected comparison.

## Availability and recovery

A project with no completed Omni children shows an empty selection message.
Completed children with missing report inputs are listed but disabled. Modern
completion uses the loss output and READONLY finalization marker; supported
legacy outputs are also recognized. Readiness requires readable child state,
query catalog, and scoped staged event/rank Parquets. Roads comparisons require
Roads assets in each selected scenario; they never substitute baseline outputs.

If a selected scenario was deleted or became unavailable, refresh the report
without its `omni_scenario` parameter and select available scenarios. Recover
missing outputs through the existing Omni execution workflow. Viewing this
report does not queue recovery or regenerate child assets. Invalid dataset
content surfaces the existing report error with diagnostics. Filtered metrics
or a channel absent in a child display a scenario-specific no-events message.

## Implementation and verification

The existing GET report route accepts repeated `omni_scenario` names. Discovery
is in `wepppy/weppcloud/routes/nodb_api/return_period_scenarios.py`; table/CSV
composition remains in `wepp_bp.py` and `reports/wepp/return_periods.htm`.
The native Details/checkbox controls reuse the report's Advanced options
`wc-collapse` and `wc-choice` styles. Applied selections live in the URL.

Comparison calls bypass report memoization because the existing cache does not
distinguish all method/interval choices. Each report is evaluated separately,
then converted using the parent presentation preferences. No new stored report
schema, cache, job, or archive path is added. Existing authorization/CAP applies.

Focused coverage lives in `tests/weppcloud/routes/test_return_period_scenarios.py`,
the return-period tests in `test_wepp_bp.py` and `test_pure_controls_render.py`,
and `controllers_js/__tests__/return_period_inline.test.js`. The route tests
parse real fixture Parquets and emitted CSV and exercise warmed caches; filesystem
tests cover both loss layouts, legacy state, restore, and symlink containment.

See the [canonical contract](../ui-docs/contracts/return-period-omni-scenarios-contract.md)
for state/error policy and the [work package](../work-packages/20261010_return_period_omni_scenarios/package.md)
for validation and deployment status.
