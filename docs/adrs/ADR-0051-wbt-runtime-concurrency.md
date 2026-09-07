# ADR-0051: Process-local WBT concurrency

Status: Accepted\
Date: 2026-09-07

## Context and Decision

WBT previously used executable-adjacent settings.json, defaulting max_procs to
-1 (all available CPUs). Its setter changes shared persistent settings. Use a
positive-integer WBT_MAX_PROCS runtime environment override instead. It takes
precedence over settings for execution but is never persisted. Unset standalone
WBT retains settings/default behavior; invalid or empty values fail explicitly.

WEPPpy default and batch worker Compose services supply
`WBT_MAX_PROCS: ${WBT_MAX_PROCS:-12}`. Thus an unset Compose interpolation variable
produces 12 inside those containers, while standalone WBT with the environment
variable genuinely absent retains automatic selection if no settings file exists.

## Decision Provenance

Decision Venue: operator/Codex conversation, 2026-09-07 (America/Los_Angeles).\
Participants Present: requesting operator and Codex.\
Decision Owner: requesting operator, who selected WBT_MAX_PROCS=12.\
Implementer: Codex.

## Rationale and Alternatives

The valid-tabletop full channel computation completed in 420.566 seconds on 12
forest cores. Shared file setters and per-call persistent CLI flags were rejected
because of shared-state races. A project/NoDb parameter is unnecessary for an
operator execution budget. Job concurrency is unchanged at the operator's request.

## Evidence and Compatibility

WBT package: /workdir/weppcloud-wbt/docs/work-packages/20260907_wbt_runtime_concurrency/.
Benchmark evidence: /workdir/weppcloud-wbt/docs/work-packages/20260907_breach_least_cost_optimization/artifacts/results.md.
The Python wrapper already inherits subprocess environment. A rebuilt WBT binary
with override support is required; adding the environment to an older binary does
not enable the limit. Persistent CLI --max_procs remains compatible; the runtime
environment wins for execution if both are supplied.

## Risk and Rollback

This is a thread budget, not a CPU reservation. No scientific formulas, input
schemas, queue edges, or fallback rules change. Removing the new Compose entries
and unsetting WBT_MAX_PROCS restores legacy settings/default selection. Do not
roll out until the container wrapper workflow passes with the rebuilt binary.
