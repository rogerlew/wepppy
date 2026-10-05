# Climate CLIGEN Seed Contract

## Status and scope

This is the accepted canonical contract for the optional CLIGEN random seed
selected in WEPPcloud Climate Options and consumed by Climate NoDb build paths.
The operator approved contract amendment `CLIMATE-SEED-01` on 2026-10-05;
implementation conformance remains pending.

The contract governs the Pure UI field, request representation, Climate NoDb
state, queued payload replay, build snapshots, Python CLIGEN adapters, and final
native process argument. It does not govern random seeds used by WEPP or other
data generators.

## User-visible behavior

Climate Options MUST expose `cligen_seed` under Advanced options as an optional
integer field. Help text MUST explain that blank uses the existing automatic
behavior and that an explicit seed makes repeated otherwise-identical CLIGEN
runs reproducible. The permitted range is `0..99999`, inclusive.

The rendered field MUST show the currently persisted explicit override when one
exists. Automatically generated legacy runtime values MUST NOT populate the
field. Read-only projects MUST not permit editing through this field. The field
MUST also be available for Tenerife station catalogs; other advanced options
may retain their existing Tenerife visibility rules.

## Input and persistence

The JSON/form key is `cligen_seed`; the persisted user-configuration attribute
is `_cligen_seed_override` and its canonical type is `int | None`. The existing
`_cligen_seed` attribute remains path-owned automatic/runtime state and is not
user configuration.

- An omitted key MUST preserve the current persisted override. This supports
  legacy clients and exact RQ payload replay.
- A present empty string or JSON `null` MUST persist `None`, selecting automatic
  behavior for the next build.
- A JSON integer or a whitespace-trimmed ASCII digit string from `0` through
  `99999` MUST persist as an integer. Leading zeros are accepted. A leading
  plus or minus sign is not accepted.
- Booleans, fractional numbers/strings, non-numeric strings, negative values,
  and values above `99999` MUST fail validation before enqueue.
- Validation failure MUST roll back every mutation made by the same
  `parse_inputs` transaction.
- A legacy NoDb object with no `_cligen_seed_override` attribute MUST behave as
  `None`. Existing `_cligen_seed` values MUST remain automatic/runtime state.
- A malformed durable override MUST fail the next build before CLIGEN starts
  with an actionable validation error; it MUST NOT silently become automatic.

## Build and execution propagation

An explicit persisted override MUST be captured once for a logical build and
passed unchanged through every applicable Climate-owned CLIGEN path: vanilla
multi-year, PRISM/E-OBS/AGDC modified stochastic, observed Daymet/GridMET/PRISM,
future, multiple-interpolated workers, and the dormant single-storm helper
interface. The native command MUST contain exactly one argv element formatted
`-r<seed>`. This contract does not re-enable currently unsupported single-storm
Climate modes.

Every child in a multiple-climate build MUST receive the same captured explicit
override. Collect/finalize observed builds MUST include the override in their
immutable input snapshot and reject output if it changes during collection.
Modified stochastic builds that retain the Climate lock across their worker
pool MUST capture the override once and pass that same value to every worker.

Batch base-to-leaf synchronization MUST copy `_cligen_seed_override` as user
configuration. It MUST continue excluding `_cligen_seed`, which remains
per-leaf generated runtime state. Retry/drift comparison MUST distinguish these
two attributes.

When the explicit override is `None`, each path MUST retain its pre-amendment
automatic/default behavior. A path that historically omitted `-r` continues to
omit it. Modified PRISM/E-OBS/AGDC paths continue their current effective
`-r12345` behavior, even if they generate/persist a separate runtime
`_cligen_seed`. The new UI MUST NOT impose a new numeric default.

CLIGEN interprets a positive `-rN` as advancing each active random stream `N`
times; it does not replace the generator state with `N`. `-r0` retains native
default streams. `-r-1`, which requests clock-derived behavior, is prohibited.
The `0..99999` range is a WEPPcloud application policy based on its existing
five-digit automatic-state convention, not a native CLIGEN limit.

## Observability and generated-output evidence

CLIGEN diagnostic command output MUST make the `-r<seed>` argument observable
without changing existing run-log retention. Acceptance requires reloading the
saved integer from `climate.nodb`, observing the exact consumed argv, parsing a
fresh `.cli`, and proving byte-identical results from two otherwise-identical
runs with the same explicit seed. Real-binary boundary tests MUST include `0`,
a representative positive value, and `99999`.

Mock-only evidence, successful enqueue, a persisted value alone, or output file
existence alone is insufficient.

## Compatibility and recovery

No NoDb migration is required. Removing the feature leaves older files
readable because `_cligen_seed_override` is additive and optional. To recover
from an undesired explicit seed, clear the field and rebuild; automatic behavior
resumes according to the selected climate path.

## Security and containment

The seed MUST remain a validated integer argv element. It MUST NOT be evaluated
by a shell, interpreted as a path, or accepted outside the bounded range.
Existing run authorization, NoDb locking, queue conflict handling, and project
containment remain unchanged.
