# Baseline label checkpoint

Starting implementation ccba373e4. Operator explicitly requests GL dashboard
baseline naming parity and verification. Source verifies Undisturbed/Burned,
not SBS. Existing commit/proceed authority covers this bounded follow-up.

Applicable contracts: return-period-omni-scenarios-contract (Tables and CSV),
controller-contract (consistent presentation), output-scope-contract unchanged.
Delta: baseline display/CSV cell label only; child scenario names remain exact.
Use existing BAER/Disturbed has_map state, prefer BAER when enabled as dashboard
endpoint does. No optional controller creation; single-input/absent state is
Undisturbed. Registered map is the server predicate; browser image transport
failures do not change CSV identity. This distinction is explicit in contract.

Regression plan: absent/no-map/map states, BAER precedence, single-input scope,
HTML/CSV same baseline label and preserved child names/data. No new columns,
API parameters, model output schemas, or derived artifact logic. Low incremental
security impact: fixed literal labels; existing report authorization retained.
No broad full-suite repeat for this bounded presentation change after the prior
10,554-pass sanity; run targeted route/template tests and live forest check.

Independent read-only correctness and security reviews approved with no
blocking findings. Keep label lookup comparison-only. Verify optional absence
without creation and BAER precedence. Implementation untouched before ancestor.
