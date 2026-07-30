# DOM-05A Topaz Conditioning Contract Decision

**Date**: 2026-07-30 UTC

**Starting WEPPpy revision**:
`efd526ef72d13a893b7d3b88dc4aab02a34d6eea`

**Starting WBT revision**:
`0f2960ffa45b69814ab3a0dc1c6cc7216574fb48`

**Classification**: Intended additive UI/workflow behavior and
config-scoped parameterization change

**Security impact**: High

## Operator Decision and Durable Authorization

The requesting WEPPcloud operator explicitly authorized:

> “scaffold and execute a workpackage to build the release and integrate into
> wepppy. This should add a Topaz Conditioning Algorithm to the Depression
> smoothing algorithm select of the chanel delineation control. the
> work-package should use contract first authoring and update the contract
> tests. make it the default mode in the disturbed9002_wbt.cfg”

The authorization venue is this Codex API workspace thread on 2026-07-29 PDT.
The approving role is the requesting WEPPcloud operator. The API context
available to the agent exposes neither a personal identity nor an external
issue/request identifier, so this exact retained request is the durable
authority record. It approves the finite behavior below.

## Normative Delta

For the Weppcloud-WBT Channel Delineation control:

1. The existing selector id, submitted name, data hook, endpoint, request key,
   nullable compatibility behavior, persistence ordering, and reload hydration
   remain unchanged.
2. The allowed user-visible/token pairs add
   `Topaz Conditioning Algorithm` / `topaz` to the existing Fill/`fill`,
   Breach/`breach`, and Breach (Least Cost)/`breach_least_cost` values.
3. `Watershed.wbt_fill_or_breach` accepts and persists `topaz`.
4. During WBT channel building, `topaz` invokes the installed WBT
   `TopazConditionDem` against the prepared DEM and writes the usual
   `dem/wbt/relief.tif`. The integration passes
   `max_obstruction_width=2` explicitly rather than depending on a wrapper or
   binary default.
5. The existing WBT D8 pointer, flow accumulation, stream qualification,
   pruning, and channel/hillslope pipeline consumes that conditioned raster
   unchanged.
6. `disturbed9002_wbt.cfg` changes its new-run default from
   `breach_least_cost` to `topaz`.
7. No persisted project is migrated. Other configs and the Watershed fallback
   remain unchanged.
8. If the installed WBT binary lacks or fails `TopazConditionDem`, the existing
   explicit WBT failure contract applies; no fallback silently substitutes a
   different conditioning algorithm.
9. The mutation route explicitly allowlists the four tokens before controller,
   timestamp, persistence, or enqueue mutation. The defensive NoDb boundary
   raises `ValueError` for invalid state; it does not depend on `assert`.
10. The route applies the canonical path-config versus `Ron.config_stem`
    integrity guard before mutation.
11. The WBT wrapper bounds the native process, terminates its process group on
    timeout, waits for cleanup, and reports timeout or nonzero exit explicitly.

Implementation conformance is pending until the reviewed checkpoint is a
standalone ancestor and the release/tests pass.

## Applicable Contracts

- `docs/ui-docs/controller-contract.md`: shared controller singleton,
  serialization, and feedback rules remain unchanged.
- DOM-05 field matrix: amended by this checkpoint to define the fourth token,
  dispatch semantics, config-scoped default, and compatibility behavior.
- `docs/schemas/nodb-persistence-concurrency-contract.md`: the existing setter,
  atomic dump, cache invalidation, and worker ordering remain unchanged.
- `docs/schemas/rq-response-contract.md`: no response, enqueue, job, or error
  shape changes.
- `docs/schemas/weppcloud-csrf-contract.md`: the existing authenticated mutation
  and CSRF boundary is unchanged.
- ADR-0032: authoritative parameterization decision for the config-scoped
  default and obstruction-width choice.

No conflict is identified. This additive field contract narrows neither a
shared invariant nor an existing authorization rule.

## Compatibility and Data Plan

The persisted string field is unchanged, so no schema migration is needed.
Legacy tokens retain their behavior. Old projects hydrate their stored token.
New `disturbed9002_wbt` projects obtain `topaz` from config initialization.

Rollback is staged. The immediately safe rollback restores
`disturbed9002_wbt.cfg` to `breach_least_cost` for new projects while retaining
the additive `topaz` option, setter compatibility, dispatch, and binary for
projects that already selected it. This does not mutate persisted projects.

Full removal of the token/code/binary is a separate destructive compatibility
operation and is not authorized by this package. It requires a separately
approved inventory and migration plan, lock/cache-safe NoDb mutation, an audit
log that distinguishes default-derived and user-selected state where possible,
failure-atomic execution, archived/batch coverage, and a zero-residual
verification before old code can be deployed.

## Regression Evidence Required

- Actual rendered select contains all four exact token/label pairs and hydrates
  `topaz` selected.
- Both channel controllers submit `"wbt_fill_or_breach": "topaz"`.
- Watershed config initialization and setter accept `topaz`, while invalid
  values still fail explicitly.
- A pre-existing project persisted with each representative legacy token
  reloads that token after the `disturbed9002_wbt` default changes; no migration
  occurs.
- RQ persists `topaz` before channel construction and retains null compatibility.
- Emulator dispatch calls only `topaz_condition_dem` with
  `max_obstruction_width=2` for `topaz` and preserves the three legacy calls.
- Invalid/hostile enum and path/config-mismatch requests in normal and
  batch/base modes return the canonical error before persistence, timestamp,
  or enqueue mutation.
- The built/installed WBT binary discovers and executes `TopazConditionDem`.
- A forced wrapper timeout proves process-group termination, wait/reap, and an
  explicit failure; a nonzero child exit is also explicit.
- A disposable WEPPpy path creates the usual `relief.tif`.
- `disturbed9002_wbt.cfg` resolves to `topaz`; representative other configs do
  not change.

## Security and Operations

No route shape, auth, CSRF, queue, shell, output-path, or file-upload behavior
changes. Existing canonical config/run integrity and invalid-enum rejection are
repaired on this route before enabling the new default. The worker receives one
additional validated enum and invokes an owned wrapper with fixed keyword
arguments, not shell-composed input. The high-impact review must verify
fail-closed validation, bounded native cleanup, run-scoped output, WBT release
provenance, staged rollback, and absence of unrelated queue/catalog drift.
