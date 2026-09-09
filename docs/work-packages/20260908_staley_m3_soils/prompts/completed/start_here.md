# Archived Start Prompt: Staley M3 Soils

Completed 2026-09-09. Offline implementation and comparison are delivered;
reviews and validation pass. See the package decision report for the
recommendation to retain original STATSGO pending scientific source approval.
The original execution instructions follow for historical reproducibility.

Execute [staley_m3_soils_execplan.md](staley_m3_soils_execplan.md) end-to-end.
Read root and nested AGENTS, the package brief, canonical postfire specification,
SSURGO feasibility assessment, and full ExecPlan before executable changes.

The terrain task is completed: initial M3 support is recommended for genuine
10 m terrain. This task audits SSURGO raw soil horizons, implements a testable
offline cumulative-thickness derivation, compares it against original STATSGO
THICK, and specifies readiness/coverage semantics for future production use.
Do not assume SSURGO is accepted merely because its mapping is finer.

Use the three supplied 10 m terrain sites and archived assessed outlet records.
Their soil caches are not committed with the terrain fixtures; source inventory
and minimal fixture acquisition are the first milestone. Work read-only against
existing projects. Do not rebuild live soils, introduce silent defaults, or
wire production NoDb/UI/RQ behavior. Do not create/switch branches, commit, or
deploy unless separately authorized for the executing session. Preserve
unrelated work and ignore a dirty usersum generated docs_index.json.

Proceed milestone by milestone, recording evidence and unresolved scientific
questions explicitly. Keep package tracker and ExecPlan current, obtain required
independent reviews, and promote durable findings into canonical module docs.
