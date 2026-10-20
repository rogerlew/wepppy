# Water output documentation tracker

Status: Active — implementation and validation; index publication awaits operator exception.

- Starting WEPPpy revision: `1ecf04735`; native revision: `54d0867`.
- Audit: `docs/dev-notes/20261020_water_output_documentation_audit.md`.
- Active plan: [water_output_documentation_execplan.md](prompts/active/water_output_documentation_execplan.md).
- Contract checkpoint: `14c7eebb1`, two independent reviews approved after disposition.
- Implementation written; focused 281 checks passed, native Python 163 passed, interchange/reports 105 passed (1 skipped), fresh temporary-catalog discovery 7 passed; isolated Chromium checks passed. Native paired release `3b63064`; final review and broad validation underway.

## Decisions

Preserve all numerical behavior. Add guides under Technical Reference without changing protected navigation sections. Preserve the pre-existing dirty generated Usersum index; validate a fresh temporary index and publish only task-specific changes if safely separable, otherwise document the required rebuild without altering unrelated entries.
