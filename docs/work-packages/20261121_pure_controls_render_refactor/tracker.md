# Pure controls render refactor tracker

**Started** 2026-11-22 04:57 UTC

- [x] Identify shared mutable state and repeated setup.
- [x] Capture baseline and refactor fixture setup.
- [x] Confirm focused results and collection parity.
- [x] Record results and close the package.

[Package](package.md) · [Execution plan](prompts/completed/implementation_execplan.md)

## Validation

- Baseline at `dcd42728a1bda64c6da33b45a98fb4e8e5a1608d` passed all 299 cases in
  32.21 seconds. The all-function-scoped trial passed in 96.57 seconds.
- The final candidate passed the same 299 node IDs in the same order in
  35.43 seconds with four warnings, matching the baseline warning count.
- An AST comparison preserved assertions and decorators across all 160 test
  functions and the module-level marker.
- The reordered selection below passed all seven cases. Running the developer
  indicator with `True` before `None` exercises the former nested-state leak.
- The default broad preflight could not find the GeoParquet parser or its
  provenance and stopped before pytest. Focused runs used the Python profile.

```bash
p=tests/weppcloud/routes/test_pure_controls_render.py
wctl run-pytest --profile python -- "$p" -q -rA
wctl run-pytest --profile python -- -q -rA \
  "$p::test_run_header_developer_indicator_uses_current_view_model[True]" \
  "$p::test_run_header_developer_indicator_uses_current_view_model[None]" \
  "$p::test_run_header_hides_team_public_readonly_for_anonymous" \
  "$p::test_return_period_comparison_renders_independent_dates_and_empty_parent" \
  "$p::test_wepp_return_period_template_reports_empty_core_measures" \
  "$p::test_pmet_advanced_template_renders_payload_and_routine_contract" \
  "$p::test_wepp_control_renders_core_run_and_lifecycle_contract"
```
