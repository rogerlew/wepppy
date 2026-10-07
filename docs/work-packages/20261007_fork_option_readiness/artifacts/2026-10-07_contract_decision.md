# FORK-UI-01 Contract Decision

Status: Operator accepted; independent reviews passed; standalone ancestor pending.
Prepared: 2026-10-07 23:09 UTC.
Starting revision: `918b3ca0a1639c0ec057decbf4fd1b6bac25b10b`.

## Operator direction and bounded delta

The operator requested disabling skip Omni when no scenarios/contrasts exist,
disabling undisturbify without an SBS map, and correcting readiness validation.
On 2026-10-07 UTC, the operator explicitly answered "Approve checkpoint,
reviewers, and implementation" to the request naming this package, its current
contract, the checkpoint commit, and two independent reviewer agents. The exact
matrix in the [current contract](../../../ui-docs/contracts/fork-console-contract.md)
is accepted; implementation remains pending until the reviewed ancestor exists.

The normative additions are source-aware disabled/unchecked controls and
readiness acceptance of absent unused Omni state. Existing client payloads and
worker behavior stay compatible, including previously queued true skip flags.
No migration, stored schema change, model rule, queue edge, or new API is needed.

## Applicable authority

- `docs/ui-docs/contracts/fork-console-contract.md`: proposed domain authority.
- `docs/ui-docs/controller-contract.md`: bootstrap, forms, presentation, polling.
- `docs/schemas/rq-response-contract.md`: errors and authoritative job status.
- `docs/schemas/nodb-persistence-concurrency-contract.md`: read-only state access.
- `docs/schemas/weppcloud-session-contract.md` and
  `docs/schemas/weppcloud-csrf-contract.md`: unchanged auth/transport boundaries.
- `docs/adrs/ADR-0021-fork-console-status-backpressure-thresholds.md` and
  `docs/adrs/ADR-0031-fork-destination-readiness-retry-budget.md`: unchanged
  lifecycle authority, status handling, and retry budget.

Historical SURF-04B required Omni artifacts whenever skip was true. It lives in
a closed package and cannot authorize current work. Promote the bounded present
controller checks and explicitly ratify the absent-controller no-op instead of
editing history. The option restrictions are an intended UI change; this is
not classified solely as a conformance patch to avoid the checkpoint.

## Incident evidence

Read-only checks on wepp1 used `docker logs` for rq-engine, RQ job inspection,
and directory/controller inspection inside `docker-weppcloud-1` as uid 1002,
gid 130. The deployed readiness helper returned false for every destination.

| Job | Source | Destination | Ended UTC |
| --- | --- | --- | --- |
| `161bdb7b-2119-445f-9d25-47b3d3979ec2` | `perceivable-fishnet` | `mdobre-coiled-rifleman` | 2026-10-07 00:06:41 |
| `ab64c24d-d1fe-41bd-a032-226a3b0b5f0c` | `beatable-facial` | `mdobre-smoke-free-trefoil` | 2026-10-07 00:07:28 |
| `31e2b0ee-afc3-413b-bfaf-ee5c487b4ab3` | `perceivable-fishnet` | `mdobre-solvent-courtier` | 2026-10-07 00:12:08 |

All jobs were finished with no RQ exception and flags `(False, True, True)`.
All destinations had the four core NoDb files, no Omni controller or directories,
and mods `disturbed`, `debris_flow`, `ash`, `treatments`. The worker's explicit
no-controller branch skips the reset. This proves the readiness mismatch, not
the correctness of unrelated model outputs.

## Exact implementation boundary

- `wepppy/weppcloud/routes/fork_console/fork_console.py`: read capabilities,
  normalize unavailable query selections, and correct the readiness predicate.
- `wepppy/weppcloud/templates/controls/fork_console_control.htm`: native disabled
  state and associated explanations through existing macros.
- `wepppy/weppcloud/static/js/fork_console.js`: bootstrap and serialization of
  disabled controls; existing polling/retry/link flow retained.
- Corresponding route, actual-Jinja, and console Jest tests; developer/user docs.

No edit to RQ producers/workers, NoDb persistence methods, shared controllers,
auth, infrastructure, or model output is included. Generated bundles are rebuilt
only as required by existing tooling. Security impact is high solely because
readiness accepts one previously rejected filesystem state; no-follow checks
must continue rejecting hostile entries.

## Regression and review plan

The current contract defines valid-state and input matrices. Run the exact
absent-controller incident regression before implementation; render real Jinja
and test disabled payloads with hostile query/programmatic checked values.
Test real symlink/file/FIFO and missing-ancestor cases, existing reset state,
legacy job arguments, authorization, and unrelated-job rejection. Replay a
read-only candidate on the real production destinations without changing files.

Two independent read-only contract reviews must assess intent, bounded scope,
compatibility, valid-state coverage, and containment before the checkpoint
commit. Final correctness and security review must close medium/high findings.
Independent reviewer identities, final approvals, and finding dispositions are
recorded in `2026-10-07_checkpoint_reviews.md`.

## Review-driven compatibility clarifications

The correctness reviewer required preserving the existing derived SBS map
fallback and defining named-child versus collection-root emptiness. The security
reviewer required replacing detached hydration (which can migrate legacy source
files) with bounded read-only JSON metadata inspection. Both clarifications
preserve existing valid workflows within the accepted scope. The contract now
requires these cases, absolute/relative SBS references, no-follow regular metadata
reads, and real source nonmutation tests. No shared NoDb change is authorized.
