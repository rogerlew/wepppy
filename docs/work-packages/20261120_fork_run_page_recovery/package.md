# Fork destination project page recovery

Status: Contract accepted. Implementation pending.

A fork that reached WEPP postprocessing returned a project-page HTTP 500
because the after-request query credential hook propagated the existing fork
guard conflict. The operator approved the proposed project and results states
and requested contract-first implementation on 2026-11-20.

Scope covers fork destination page rendering and status, exact query cookie
conflict handling, and on-demand catalog readiness for the run page WEPP loss
map. Existing ownership, query access, queued work, recovery mutations, and
scientific outputs remain under their current contracts.

Security impact is high because this changes browser credential error handling
and introduces receipt-derived presentation on an existing public route.
Independent security and correctness artifacts are required before closure.

- [Contract checkpoint](artifacts/20261120_contract_decision.md)
- [Tracker](tracker.md)
- [Execution plan](prompts/active/implementation_execplan.md)
