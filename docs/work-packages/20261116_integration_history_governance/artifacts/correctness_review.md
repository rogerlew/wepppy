# Correctness and operational review — integration history governance

## Metadata

- Package: `20261116_integration_history_governance`.
- Reviewer: delegated correctness/QA agent.
- Date: 2026-11-16 (UTC).
- Review type: design and acceptance review; controls are not implemented or validated.
- Evidence context: restored master `420e31b97`; root `AGENTS.md`, work-package
  guidance, generated-artifact validation and hardening lifecycle standards.
- Scaffold readback: `package.md` and `tracker.md` reviewed; proposed controls
  already cover receipt freshness, merge-mode decisions, and behavior checks.
- Scope: remote integration receipts, safe synchronization, task isolation,
  valid developer states, regression design, and recovery.

## User outcome

Accepted work remains available in the declared remote integration branch, and
completion claims identify exactly what was accepted, integrated, tested, and
released. A failed check reports what could not be established without modifying
or discarding unrelated tracked, staged, untracked, or ignored work.

A receipt proves a historical observation at a specific remote commit. It does
not promise that the remote can never advance or that a later descendant cannot
revert the implementation. These are separate preservation and behavior checks.

## Failure-class coverage

The broken assumption was that reviewed local history would survive the next
synchronization and therefore could support an integrated completion claim.
Consumers include package closure, issue closure, handoff summaries, merge
validation, image publication, and deployment. The scope must distinguish local
loss prevention, remote inclusion, and continuing behavioral conformance.

The incident topology is specific: the remote was older, the local rebase
retained only a later soils change, and the remote then accepted a fast-forward.
A test that merely rejects a force-push does not reproduce this incident.

## Findings and required decisions

| ID | Severity | Finding and evidence | Required action | Status |
| --- | --- | --- | --- | --- |
| COR-01 | High | An ancestry receipt against a stale local tracking ref can falsely claim current integration; a successful push alone does not bind acceptance to the intended repository/branch. The incident closure existed at `4194fd43b` while this checkout's remote tracking ref remained `ff1740239`. | Fetch the explicit target, record repository identity, branch, accepted SHA, observed target SHA, UTC time and check result. Network/auth/unknown history errors must prevent an integrated claim while preserving a locally accepted state. | Acceptance requirement; implementation unvalidated |
| COR-02 | High | Ancestry does not prove preservation of behavior: a revert remains a descendant. Existing shape CI is path-filtered in `.github/forest_workflows/pytest-shape-converter-gates.yml`; this incident's remote push did not change those paths. | Keep inclusion proof separate from a small always-run behavioral baseline. Exercise stale architecture and explicit revert cases; control changes to the baseline through the selected protected review path. | Acceptance requirement; implementation unvalidated |
| COR-03 | High | Worktree cwd is not proof of the tested checkout. `tools/wctl2/commands/python_tasks.py` sends pytest to container `/workdir/wepppy`; the existing mounted source can differ from a new host worktree. | Before crediting validation, verify the host candidate and actual container source identity, including dirty content when permitted. Prefer serialized validation against the existing stack initially; do not add per-task Compose stacks without evidence they are needed. | Confirmed consumer hazard; design decision required |
| COR-04 | Medium | Raw accepted-commit ancestry rejects legitimate squash/rebase integrations even if content was integrated. Root `AGENTS.md` also prohibits creating/switching branches without user instruction. | Ratify a commit-preserving merge policy for the first version, or specify an explicit reviewed-to-integrated mapping and fresh validation. Amend branch authority before making per-task branches mandatory. | Decision required |
| COR-05 | Medium | A receipt cannot contain the hash of the same commit that introduces it. Requiring the final closure commit to prove its own remote reachability produces a circular completion rule. | Bind receipts to an immutable accepted implementation SHA and an observed remote SHA; store the receipt in a subsequent audit commit or approved remote record. Clearly distinguish acceptance content from later administrative closure. | Design clarification required |
| COR-06 | Medium | Hooks and wrappers are bypassable; rerunning a mutation after an ambiguous failure can duplicate work or overwrite state. | Label local guards as accidental-loss defenses; name the server gate separately. Make inspection read-only and ensure interrupted operations leave durable evidence and a manual recovery path. Avoid automatic reset, stash application, or cleanup. | Acceptance requirement; implementation unvalidated |

High ratings reflect recurrence of undetected loss or false validation of
security-critical work. Medium findings concern compatibility and completion
semantics that must be settled before the controls are treated as authoritative.
None is a claim that an unimplemented control has passed or failed runtime tests.

## Valid-state matrix and direct acceptance evidence

Every row below is proposed acceptance coverage, not an executed test result.
Use real temporary Git repositories and a bare local remote for history tests;
use a disposable branch/repository for actual server-policy denial tests.

| State or operation | Required behavior | Direct evidence to retain |
| --- | --- | --- |
| Fresh clone; no accepted checkpoint | Allow development; do not invent accepted state or demand a nonexistent receipt. | Parsed absent-state result and unchanged refs/worktree. |
| Empty or malformed receipt | Explicit validation error; no integrated claim. | Error classification and no writes outside intended artifact. |
| Valid accepted commit already on remote | Receipt succeeds for exact target identity and observed SHA. | Fresh fetch, ancestry result, parsed receipt. |
| Accepted commit local only | Allow local acceptance; prevent integrated/closed claim. | Real remote lacks accepted SHA; receipt failure. |
| Incident reproduction: accepted commits plus unrelated later commit; synchronization drops accepted range; remote fast-forward succeeds | Local preservation guard refuses loss, or closure remains visibly incomplete; baseline rejects stale behavior. | Real before/after graphs, ordinary push result, guard result, baseline result. |
| Stale local `origin/master` | Fetch before deciding; unavailable remote gives unverified, not pass. | Deliberately stale tracking ref and fresh remote result. |
| Remote advanced concurrently | Accept a descendant only after checking the newly observed SHA; refuse non-fast-forward overwrite. | Two independent clones and target observations. |
| Missing objects or shallow clone | Deepen/fetch required history or report insufficient evidence; do not interpret an object lookup error as non-inclusion or success. | Shallow clone through a transport that honors depth, explicit error/result. |
| Offline or authentication failure | Preserve locally validated work; no remote-integration claim. | Bounded failure and retry after connectivity restored. |
| Merge commit preserves accepted history | Accept exact ancestor proof and identify merge target. | Real merge history. |
| Squash/rebase integration | Reject as unsupported under merge-only policy, or require the approved mapping and validation. | Real rewritten integration, no accidental ancestry pass. |
| Revert of accepted code with accepted SHA still ancestral | Inclusion may pass; behavior baseline must fail unless an approved supersession exists. | Real revert, ancestry pass, semantic test failure. |
| Dirty index, tracked edits, untracked files, ignored files | Inspection and refused synchronization preserve all bytes, staged state and refs. | Before/after manifests plus `git diff --cached`, refs and status. |
| Two agents on separate worktrees | Separate indexes/working files; only designated integrator updates shared branch. | Concurrent candidate edits without cross-contamination. |
| Candidate in alternate worktree, tests run through existing container | Wrong checkout is detected before validation credit. | Host and container revision/content readback. |
| Guard missing or bypassed | Cannot claim local prevention; enforced server checks still block in-scope unsafe integration. | Real bypass demonstration and separate remote policy rejection. |
| Crash between backup and integration | Original accepted commit remains referenced; retry is nondestructive. | Recovery ref/bundle verified by reopening objects. |
| Valid authorized recovery or baseline supersession | Explicit bounded procedure can proceed with recorded authorization and fresh validation. | Recovery receipt, new target identity and direct content checks. |

## User-reachable error policy

Unavailable remotes, unsupported integration modes and missing history are
expected verification failures with actionable messages. They must not erase
local acceptance or cause automatic cleanup. A mismatched test checkout is a
validation error. A blocked branch update leaves the proposed candidate intact.
A server-policy denial must explain the required check or allowed recovery path.

## Generated artifact evidence chain

| Stage | Expected meaning | Required evidence | Current result |
| --- | --- | --- | --- |
| User intent | Named accepted implementation and destination repository/branch. | Explicit checker inputs and approved integration mode. | Proposed |
| Persisted state | The acceptance record refers to a real immutable commit. | Object readback and retained reference. | Proposed |
| Generated receipt | Binds accepted commit to freshly observed remote target. | Parse and verify receipt fields against real Git objects. | Proposed |
| Consumer | Closure/publication/deploy uses the exact candidate and receipt. | Consumer-side identity checks; no stale-file substitute. | Proposed |
| Execution | Required checks ran against the consumed source. | Source revision/content and test results. | Proposed |
| User result | Integrated status only after inclusion proof; release status separately qualified. | Closure/readback tied to evidence. | Proposed |

No runtime validation or deployment occurred during this design review. Existing
recovery evidence establishes the prior incident repair, not the effectiveness
of these future controls. Repository review artifacts are the applicable
observability surface; this package does not create project/run data requiring
browser or run-archive integration.

## Recommended implementation order and decision points

First ship a small read-only integration verifier and a canonical completion
contract. Pair it with safe synchronization guidance and refusal of routine
shared-master rewrites. Use the actual incident topology as the first failing
regression. Next wire a stable always-run check and server-side enforcement,
then validate task isolation against the real mounted test checkout.

The operator needs to decide: whether commit-preserving merges are mandatory;
who may integrate and exercise emergency bypass; whether task branches become
preauthorized; and whether early rollout uses serialized testing on the existing
stack. Recommend preserving commits, one designated integrator, explicitly
scoped task-branch authority, and serialized existing-stack validation initially.
Do not require a new service, queue, merge bot, or parallel container topology.

## Verdict

Design review completed with 3 High and 3 Medium acceptance/decision findings.
Implementation gate: HOLD until the controls are built and directly validated.
This artifact is suitable input to the scaffold and decision review; it is not
an independent implementation sign-off.
