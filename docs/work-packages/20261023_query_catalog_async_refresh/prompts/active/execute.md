# Launch query catalog refresh execution

Execute `docs/work-packages/20261023_query_catalog_async_refresh/prompts/active/implementation_execplan.md` milestone by milestone. Read the canonical `docs/schemas/query-engine-catalog-refresh-contract.md`, caller matrix, reviewed decision and dispositions first. Verify checkpoint `dc2b2ddbe8cfedbd4bae024310f03447ca813c32` is an ancestor before runtime edits.

Async is preferred for eligible producers. Publication/lifecycle coordination, recovery, native GIL release and internal reader freshness barriers are prerequisites, not follow-up cleanup. Preserve synchronous and standalone APIs, primary domain job responses, scientific artifacts, READONLY exceptions and existing authorization. Follow the exact reviewed contract; do not invent a new service/queue or silently change pending-state UX.

Read nearest AGENTS and applicable skills before each subsystem. Preserve unrelated working-tree edits and the generated Usersum index. Keep tracker, active ExecPlan and evidence matrix current. Use agents for bounded analysis/implementation work where files can be owned independently; use independent correctness/security reviewers after changes and disposition every finding. Do not parallelize incompatible publication/lifecycle edits without an explicit ownership split.

Implement and validate through M6 when execution is authorized. Do not deploy or repair production runs without that authority. If environment-dependent tests are unavailable, continue independent local work and report the exact remaining evidence gate. Never claim deployment, repair or incident resolution from unit tests or successful enqueue alone.
