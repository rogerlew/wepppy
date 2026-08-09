# Phase 2A Hard-Coded Assumption Inventory

This inventory treats `tools/peakflow_phase2a_pilot.py` and its committed
evidence as compatibility authorities. The reusable engine must preserve the
scientific behavior listed here while moving each site or study choice into a
manifest, explicit command argument, or frozen plan.

## Site, Population, and Filesystem Assumptions

- `REPO`, `PACKAGE`, `ARTIFACTS`, and `PHASE1_ARTIFACTS` select one repository
  and work package. The reusable engine receives manifests, plans, and output
  paths explicitly.
- `RUN_ROOT` and the burned and undisturbed `SCENARIOS` embed Topanga paths.
  Scenario authority and relative `runs` paths move into the study manifest.
- `TOPOGRAPHY` and `CHANNELS` embed Topanga watershed tables. They are not
  needed by a local hillslope census and are excluded.
- `HILLSLOPE_IDS = range(1, 141)`, channel IDs, and outlet 201 assume a
  contiguous Topanga topology. The planner discovers hillslope IDs from
  declared run-deck filename patterns. Channel and outlet assumptions do not
  enter the reusable package.
- Hillslope files use `p<ID>.cli/.man/.run/.slp/.sol`, output uses `H<ID>.hbp`,
  and shared files use fixed WEPP names. The filename pattern and required
  suffixes are manifest fields, with these values as Topanga configuration.

## Pilot Design Assumptions

- Selection is exactly eight hillslopes, forces hillslope 106, and uses
  Topanga-specific terrain and routing covariates. Full-census planning has no
  selection algorithm; a bounded validation manifest may explicitly list the
  accepted eight identifiers.
- The mutation matrix is two scenarios by eight hillslopes by two families by
  two directions, with an assertion of 64. The reusable matrix is derived from
  declared scenarios, discovered or explicitly selected hillslopes, and
  manifest mutation families.
- Trial IDs omit a site and plan binding. New readable IDs bind site, scenario,
  hillslope, family, direction, and plan ID.
- Schema `1.0.0`, source commit, observer build ID/hash, and screening floors
  are module constants. They become versioned manifest fields. The accepted
  Topanga values remain unchanged.
- The evidence path appends the pilot ID, mutation paths append selection ID,
  and absent `terminal.json` files define pending work. The reusable plan
  carries evidence-relative locators and reuses a terminal only after all
  plan, input, executable, and schema bindings match.

## Mutation and Execution Assumptions

- Ksat is token 3 of the first numeric soil horizon and changes by `0.99x` or
  `1.01x`. Cover is initial-condition `inrcov` token 6 plus `rilcov` token 3,
  both changed by `-0.01` or `+0.01`. These accepted adapters and magnitudes
  remain faithful; adapters publish exact line, token, source, expected, and
  realized values.
- The pilot rejects cover clipping only at execution time. The new planner
  freezes any inability to realize both directions as explicit exclusions.
- The pilot copies one hillslope deck plus a fixed list of shared inputs,
  adapts one `.pass.dat` run-deck reference to `.hbp`, touches
  `peak_diag.on`, and invokes the binary with the run deck on standard input.
  These are execution adapter fields and behavior, not site constants.
- The pilot verifies only that one copied file hash changed. The reusable
  mutation realization additionally binds before/after hashes and rejects
  missing tokens, serialization erasure, source writes, and extra changes.
- Process execution uses a direct executable path, working directory, binary
  standard input, captured output, and no shell. The reusable engine pins and
  verifies the executable SHA-256 and retains this invocation boundary.
- Success depends on return code zero, the accepted WEPP success marker, a
  trace, and a hillslope pass. The terminal contract preserves these checks.

## Observer, Pairing, and Screening Assumptions

- Observer trace records are `SCALAR` followed by `RESULT` rows keyed by year,
  day, OFE, and ordinal. The parser rejects orphaned or unterminated records and
  preserves all full-precision numeric fields.
- Event pairing is an outer join on year, day, OFE, and ordinal within one
  scenario and hillslope. Presence flags distinguish missing rows from measured
  zeros. This behavior is immutable compatibility scope.
- Baseline and mutant columns, diagnostic flags, floors, ratios, expected
  response direction, and the union defining `candidate` are accepted Phase 2A
  semantics. They move unchanged into the reusable pairing module.
- Parquet/CSV summary output locations and the fixed pilot terminal schema are
  package-specific. New validators can read the old evidence and emit compact
  parity reports without rewriting it.

## Explicitly Excluded Assumptions

Everything from `parse_topology`, watershed-lane preparation, watershed binary
execution, channel comparison, route commands, replay adjudication, and
hydrograph validation remains in the pilot authority only. No routing command,
watershed executable, topology closure, channel output, canopy, or LAI concept
is part of the reusable local-census plan.
