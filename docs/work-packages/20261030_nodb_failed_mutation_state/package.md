# Failed NoDb mutation state repair (NFMS-01)

Status: implemented, independently reviewed and locally validated; implementation commit and push authorized.
Started: 2026-10-31 UTC. Owner: operator with Codex implementation/review agents.

## Outcome and scope

Previously, failed mutations left rejected values in a reusable controller;
unrelated later saves and preparation could consume them. Shared high-level
boundaries and confirmed manual/aliased consumers now recover or fence state;
preserve disk authority, singleton identity, owner tokens and explicit low-level
retry semantics. Broken assumption: disk non-persistence and lock release do not
imply that a shared mutable object reverted its failed changes.

The durable decision is in `docs/schemas/nodb-persistence-concurrency-contract.md`,
“Failed high-level mutation state (NFMS-01)”.
This is a normative extension, not solely conformance to the prior cache contract.
The operator authorized the bounded outcome by requesting execution of
`/tmp/nodb-failed-mutation-state-repair-prompt.md`; retained copy is
`prompts/active/operator_prompt.md`. The operator subsequently authorized the standalone checkpoint commit, `2b998e08d`;
the operator subsequently authorized the implementation commit and push.

## Boundaries and complexity budget

No new dependency, service, datastore, queue, generic transaction framework,
scientific value, persistent schema, auth, permission, deployment or lock TTL
change. No new branch, production job or deployment. Preserve WAM-01 and MRS-01;
closed packages remain immutable history. No distributed rollback, arbitrary
nested-alias repair, process-death recovery or already-published artifact rollback.

## Security impact

Triage: high, because recovery changes shared persistence/ownership enforcement
and must prevent cross-owner state replacement while preserving valid states.
No new network endpoint or privilege is proposed. Dedicated security review,
independent correctness and QA review are required before closure. Two independent
contract reviews precede the standalone checkpoint commit. Runtime-only recovery
metadata must not leak into persisted payloads or expose private diagnostics.

## Compatibility and regression plan (before edits)

No on-disk schema or user-visible key change. Use existing coherent reads and
legacy decoding, replace persisted attributes without copying logging or Redis
resources, preserve optional absence and first initialization behavior. Direct
`dump` precommit retry remains intentional. Failed high-level instances either
recover current disk state in place or refuse state access until safe recovery.
Audit aliases that survive failures and all manual producers before closure.

Acceptance requires real files plus held-reference and unrelated-save assertions,
manual and decorator/context paths, two real controllers and generated input
readback. Use real `prep_soil` and parse `wepp/runs/p101.sol`; add option-map
preparation evidence if that consumer is repaired. Full model execution and fresh
reports are not required because the target boundary is executable-input
preparation. Focused generated-input correction is established; final broad results and limits
are recorded in `artifacts/validation.md`.

## Signals and closure

Health: no rejected B in held references, later persisted C, or prepared files;
valid empty/default/legacy operations succeed. Danger: dirty reuse after recovery
failure, owner-token interference, stale snapshot redump, listener growth or
healthy-path deep-copy cost. Use recurrence-triggered observation: retain local
baseline/post-change evidence, promote operator signals to NoDb README, and open
a new package on recurrence. No temporary mitigation is proposed for retirement.
Deployment and any affected-run recovery remain outside this package.

See `tracker.md`, `prompts/active/implementation_execplan.md` and
`artifacts/consumer_matrix.md` for executable work and evidence limits.
