# Backend-independent MOFE executable selection

Status: contract checkpoint preparation; implementation pending.

Repair the executable choices for TOPAZ/MOFE projects such as
`bronzed-liberator/disturbed9002-10-mofe`. The operator explicitly requires the
same compatible releases for TOPAZ and WBT with equal input requirements.

Scope: shared binary policy, run-page/schema/submission consumers, regression
tests, and executable-selection documentation. Builder creation geometry,
saved project configuration, model defaults, and production deployment are
excluded. Complexity budget: existing helpers only; no new infrastructure.

Security impact: low. Installed-ID and sidecar validation, geometry admission,
authorization, and NoDb locking remain enforced. No dedicated high-impact
security artifact is required; checkpoint reviews assess noninterference.

Exit criteria: backend parity in rendered choices, schemas and admission;
real save/reload evidence; unchanged config/manifest; focused and broad checks;
independent correctness review. No model-output correctness claim is made by
selector tests. Deployment requires separate production workflow evidence.
