# Water output documentation tracker

Status: Active — contract checkpoint preparation.

- Starting WEPPpy revision: `1ecf04735`; native revision: `54d0867`.
- Audit: `docs/dev-notes/20261020_water_output_documentation_audit.md`.
- Active plan: [water_output_documentation_execplan.md](prompts/active/water_output_documentation_execplan.md).
- Contract checkpoint: pending independent reviews.
- Implementation, artifact validation, and final review: pending.

## Decisions

Preserve all numerical behavior. Add guides under Technical Reference without changing protected navigation sections. Preserve the pre-existing dirty generated Usersum index; validate a fresh temporary index and publish only task-specific changes if safely separable, otherwise document the required rebuild without altering unrelated entries.
