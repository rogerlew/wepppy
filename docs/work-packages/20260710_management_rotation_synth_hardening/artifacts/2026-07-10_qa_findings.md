# QA Findings - Management Rotation Synthesizer Hardening

## Scope

QA exercised the exact p3733 source schedule, existing stack modes, residue
reference behavior, WEPP limit handling, serialization round-trip, and the
current hillslope binary with source-project support files.

## Findings

### QA-01 - Exact overflow regression

- Status: pass
- Before repair: 17 years, `ncrop=50`, `nop=136`.
- After repair: 17 years, `ncrop=3`, `nop=10`, `nini=1`, `nseq=17`, `nscen=17`.
- The result writes and re-parses with all scenario references resolvable.

### QA-02 - Spring/fall composition

- Status: pass
- The oat fixture normalizes to retained `Year 2` and one surface sequence.
- Operation days remain `110, 110, 110, 111, 111, 112, 135, 274`; synthesis
  neither duplicates nor reorders the combined spring/fall operations.

### QA-03 - Distinct-plant overflow

- Status: pass
- A generated schedule with more than 20 referenced, structurally distinct
  plants raises an actionable `ValueError` before the destination file exists.

### QA-04 - Initial real-binary replay

- Status: scoped pass with follow-up finding
- Binary: `wepp_260430_hill`, SHA-256
  `3b2fdd2b7a9e264b84f1e7b161dfb0730d49d3cb652218139efeb3ba17d7a160`.
- The repaired management has no `ncrop` error, proving the incident failure is
  closed on the wired binary path.
- WEPP then rejects the source's referenced `L179_weed` plant because `hmax=0`.
  This finding is resolved by the reopened ADR-0016 ingestion milestone.

### QA-05 - ZIP-ingestion normalization

- Status: pass
- Exact Jim-interface 2017.1 input installs with `hmax=0.00001 m`; its preserved
  source copy is byte-identical and remains at zero.
- Raw 98.4 input receives the same normalization and retains leading conversion
  notes.
- Inventory provenance reports scenario, field, original/final values, units,
  and reason. Old entries default to an empty normalization list.
- A forced zero-height active canola plant remains unchanged.
- Installed canola plus sixteen oats synthesizes to 17 years, 3 plants, and 10
  operations with canonical residue `hmax=0.00001 m`.

### QA-06 - Post-normalization binary replay

- Status: pass for ADR-0016; project completion still blocked
- `ncrop` and `HMAX <= 0` are absent and the simulation enters year 2.
- The process then returns `-8` with SIGFPE at `frcfac.for:184` while calculating
  random-roughness friction after the zero-roughness residue operation.
- Finding disposition: separate incident/follow-up. No `rro` fallback or binary
  guard is added under this package.

## Security QA

Security impact is low. Content normalization runs after existing archive
signature/path/quota checks and changes no route, authorization, extraction,
path-resolution, queue, secret, or egress behavior. Fixtures contain management
parameters and numeric run identifiers only; no credentials, tokens, user
geometry, or personal data were copied.

## QA Verdict

Pass for management synthesis and applied-residue height ingestion. Project-level
completion remains blocked on the independently exposed random-roughness failure.
