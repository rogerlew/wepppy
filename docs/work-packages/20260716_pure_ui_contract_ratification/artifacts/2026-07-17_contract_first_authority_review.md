# Contract-First Authority Review

**Reviewer**: `/root/controller_inventory_audit`
**Mode**: Read-only
**Date**: 2026-07-17 UTC
**Initial verdict**: Not closure-ready

## Findings

### H1 - Archived plans remained live amendment targets

`wepppy/weppcloud/controllers_js/AGENTS.md` still instructed agents to update
archived 2025 controller plans for payload, event, and behavior changes. Because
the nearest AGENTS file is operational authority, those instructions could make
historical documents appear canonical.

Required disposition: remove every archived-plan maintenance instruction; label
archived plans read-only historical leads and route amendments to current
canonical contracts or registered contract packages.

### H2 - Umbrella package inverted normative authority

The umbrella package named templates, controllers, routes, NoDb, workers, and
tests as authoritative source paths. That contradicted contract-first governance,
under which implementation is authoritative only for observed behavior.

Required disposition: name normative contract authorities separately and label
source/runtime/test paths as implementation-conformance evidence that cannot
define intent.

### M1 - Child prompt could self-authorize intent

The reusable prompt told an agent to amend a contract after baseline evidence but
did not require operator-approved intent.

Required disposition: branch explicitly between unchanged-contract conformance
fixes and operator-approved intended changes; stop when intent is absent or
unclear.

### M2 - Canonical authority was underspecified

Root and subsystem language could include stale repository prose and controller
guidance omitted shared/cross-cutting contracts.

Required disposition: limit authority to applicable current canonical domain and
shared/cross-cutting contracts in the ratified registry/README; explicitly
exclude archived plans.

### M3 - NoDb was a sequencing loophole

Root and nearest NoDb guidance did not require contract-first sequencing for
UI-coupled mutation, persistence, or reload behavior.

Required disposition: include NoDb in the full contract boundary and distinguish
approved intent changes from conformance restoration.

## Initial Validation

The reviewer reported `git diff --check` clean. No other high or medium authority-
ordering findings were identified in the initial diff.

## Post-Fix Confirmation

At 2026-07-17 04:01 UTC the reviewer reported closure-ready with no remaining
high or medium findings. The final pass confirmed that the finite allowlist is
exclusive only to Pure UI/UI-coupled behavior, other nearest-subsystem
specifications remain authoritative, AgFields layout prose is evidence pending
ratification, and all earlier authority findings remain closed.
