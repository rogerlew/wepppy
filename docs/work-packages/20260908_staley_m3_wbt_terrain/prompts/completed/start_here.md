# Completed Handoff: Staley M3 Terrain

Outcome (2026-09-09 UTC): registered command/bindings and 24-pair evaluation
completed; recommend genuine 10 m for initial M3. All required gates/reviews
passed. The following is the original execution handoff, retained as history.

Execute [staley_m3_wbt_terrain_execplan.md](staley_m3_wbt_terrain_execplan.md)
end-to-end. This package implements new terrain tooling in
`/workdir/weppcloud-wbt` and evaluates 10 m versus 30 m for Staley M3; it does
not implement the postfire dashboard or deploy anything.

Read `/workdir/wepppy/AGENTS.md`, `/workdir/weppcloud-wbt/AGENTS.md`, applicable
nested guidance, the package brief, and the full ExecPlan before editing code.
The package is currently documentation only. Confirm git status in both
repositories, preserve unrelated work, and do not create/switch branches or
commit without user authorization. In WEPPpy ignore a dirty usersum
`generated/docs_index.json`.

Carry out milestones autonomously within this scope. Follow repository review
requirements at closeout; keep tracker and plan current. Do not assume the
candidate relief formula already has pfdf parity or that 30 m is accepted.
Use an independently derived Rust implementation and synthetic expectations;
GPL pfdf is an external comparison reference only. Record evidence and update
the canonical postfire specification with the final findings.
