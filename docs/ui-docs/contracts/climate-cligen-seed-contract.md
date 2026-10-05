# Climate CLIGEN Seed Contract

## Status and scope

This is the canonical contract for the optional CLIGEN random seed selected in
WEPPcloud Climate Options and consumed by Climate NoDb build paths. Contract
amendment `CLIMATE-SEED-01` is accepted in design; implementation conformance is
pending until the associated package closes.

The contract governs the Pure UI field, request representation, Climate NoDb
state, queued payload replay, build snapshots, Python CLIGEN adapters, and final
native process argument. It does not govern random seeds used by WEPP or other
data generators.

## User-visible behavior

Climate Options MUST expose `cligen_seed` under Advanced options as an optional
integer field. Help text MUST explain that blank uses the existing automatic
behavior and that an explicit seed makes repeated otherwise-identical CLIGEN
runs reproducible. The permitted range is `0..99999`, inclusive.

The rendered field MUST show the currently persisted explicit/generated value
when one exists. Read-only projects MUST not permit editing through this field.

## Input and persistence

The JSON/form key is `cligen_seed`; the persisted Climate attribute is
`_cligen_seed` and its canonical type is `int | None`.

- An omitted key MUST preserve the current persisted value. This supports
  legacy clients and exact RQ payload replay.
- A present empty string or JSON `null` MUST persist `None`, selecting automatic
  behavior for the next build.
- An integer or base-10 integer string from `0` through `99999` MUST persist as
  an integer.
- Booleans, fractional numbers/strings, non-numeric strings, negative values,
  and values above `99999` MUST fail validation before enqueue.
- Validation failure MUST roll back every mutation made by the same
  `parse_inputs` transaction.
- A legacy NoDb object with no `_cligen_seed` attribute MUST behave as `None`.

## Build and execution propagation

An explicit persisted seed MUST be captured once for a logical build and passed
unchanged through every applicable Climate-owned CLIGEN path: vanilla
multi-year, PRISM/E-OBS/AGDC modified stochastic, observed Daymet/GridMET/PRISM,
future, multiple-interpolated workers, and single-storm generation. The native
command MUST contain exactly one argv element formatted `-r<seed>`.

Every child in a multiple-climate build MUST receive the same captured seed.
The immutable multiple-build input snapshot MUST include the seed; finalization
MUST reject output if durable seed state changed during collection.

When the persisted value is `None`, each path MUST retain its pre-amendment
automatic/default behavior. A path that historically omitted `-r` continues to
omit it. A path that historically generated/persisted an automatic seed retains
that behavior. The new UI MUST NOT impose a new numeric default.

## Observability and generated-output evidence

CLIGEN diagnostic command output MUST make the `-r<seed>` argument observable
without changing existing run-log retention. Acceptance requires reloading the
saved integer from `climate.nodb`, observing the exact consumed argv, parsing a
fresh `.cli`, and proving byte-identical results from two otherwise-identical
runs with the same explicit seed.

Mock-only evidence, successful enqueue, a persisted value alone, or output file
existence alone is insufficient.

## Compatibility and recovery

No NoDb migration is required. Removing the feature leaves older and newer
files readable because `_cligen_seed` remains optional. To recover from an
undesired explicit seed, clear the field and rebuild; automatic behavior resumes
according to the selected climate path.

## Security and containment

The seed MUST remain a validated integer argv element. It MUST NOT be evaluated
by a shell, interpreted as a path, or accepted outside the bounded range.
Existing run authorization, NoDb locking, queue conflict handling, and project
containment remain unchanged.
