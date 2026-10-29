# Contract and package review dispositions

Prepared 2026-10-29 UTC. Independent read-only [correctness](20261029_contract_correctness_review.md) and [security](20261029_contract_security_review.md) reviews completed. Primary author: Codex `/root`. Runtime gates remain open even after design approval.

| Finding | Disposition | Contract/plan change | Confirmation |
| --- | --- | --- | --- |
| C1 / SEC-DM-01 (medium) | Operator resolved: existing archive replacement is allowed to clear mode. No preservation or denial. | DM-01 State and lifecycle, checkpoint, ADR-0088 and ExecPlan explicitly make archived Ron authoritative; regression proves incoming true/false/missing state works. | Operator approved; correctness and security reviewers confirmed design closure, 2026-10-29 UTC |
| SEC-DM-02 (medium) | Operator resolved: existing failed-fork recovery uses source mode even when destination mode was true. | DM-01 and ExecPlan milestone 4 preserve replacement behavior and require real readback; no additional role check or sticky state. | Operator approved; security reviewer confirmed design closure, 2026-10-29 UTC |
| C2 (medium) | Accepted; require consistent mode/value publication across clone AND archive interleavings. | DM-01 State and lifecycle; ExecPlan milestone 4 requires real capture/copy barrier tests and existing serialization or monotonic reconciliation. | Correctness reviewer confirmed design closure, 2026-10-29 UTC |
| C3 (low) | Accepted; immediately refresh policy/status without discarding unsaved fields. | DM-01 Activation authorization and presentation; ExecPlan milestone 2. | Correctness reviewer confirmed design closure, 2026-10-29 UTC |

## Operator lifecycle decision

On 2026-10-29 UTC the operator explicitly approved restoring incoming archive/source state even when it clears developer mode. They rejected both sticky preservation and mode-based rejection: preserving established archive/fork functionality offers the simplest implementation and greatest recovery flexibility; blocking those operations could make projects unusable. Earlier preserve/reject recommendations are superseded. The contract now limits the one-way rule to dedicated mode editing and documents the two lifecycle replacement exceptions. New clones still inherit source mode. No further policy input is needed.

## Completion boundary

The operator decision and corresponding canonical/plan amendments are complete. Both independent reviewers confirmed all design findings closed; no policy decisions remain open. Implementation still requires the standalone reviewed ancestor commit and subsequent implementation authorization; this task remains documentation-only. No finding is implicitly waived: the former invariant is explicitly narrowed by its decision owner.

## Documentation validation

Scoped `wctl doc-lint` passed for all 15 changed/new Markdown files with zero errors or warnings; the final package (9 files), DM-01 and PROJECT_TRACKER rerun also passed. `git diff --check` passed. `uk2us` preview identified only unrelated existing PROJECT_TRACKER wording, including the `axe` tool name; no spelling replacements applied. Runtime tests were not run because no runtime code changed.
