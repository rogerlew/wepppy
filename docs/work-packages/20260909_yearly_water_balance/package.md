# Yearly water-balance report repair

Status: completed locally, 2026-09-09. Production deployment is separate.

Scope: expose existing surface runoff in yearly HTML/CSV reports and repair
the explicit all-years selection and download. User approval: "add runoff and
fix the include all years bug" (2026-09-09). No model execution, data migration,
deployment, auth change, or queue change. Security impact: low; existing
run authorization and output isolation remain unchanged. No dedicated security
artifact is required.

Authority: [output-scope contract](../../schemas/output-scope-contract.md#yearly-water-balance-presentation).
Success: correct yearly sums/statistics/ratios and CSV for both scopes; explicit
all-years links round-trip without exclusions; read-only parity against the
reported production dataset. Missing required data fails explicitly.
