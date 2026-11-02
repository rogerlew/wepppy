# MOFE management and PMET producer audit

Date: 2026-11-02 19:35 UTC. Scope: read-only production-source audit and isolated
actual Python writer experiments. No production inputs, binaries or formulas
changed. This report uses the docs-maintainer skill. Native consumer findings
are static corroboration; no full native MOFE simulation was run here.

## Findings

### PMET-01: first plant scenario only

High impact where coefficients differ. Confirmed generated-artifact defect.
`wepppy/wepp/management/managements.py:3333-3355` scans management files but adds
only `man.plants[0].name`. The actual two-OFE writer emitted plants `Tah_6892`
and `OFE2_Tah_6892`, while `pmetpara.txt` contained only `Tah_6892`.
This also affects multiple crop scenarios within a single-OFE rotation.
The native fallback can mask the omission when all intended coefficients are
identical. First plant scenario does not necessarily mean OFE1's active crop.

Minimal repair: enumerate required plant scenarios from consumed managements
with deterministic ordering and retain coefficient provenance. Acceptance must
read actual `.man` and PMET rows and verify distinct native coefficients for
different current crops. Check native crop-array capacity before expanding rows.

### PMET-02: Disturbed uses hillslope dominance instead of segment identity

High impact; confirmed static producer mismatch.
`wepppy/nodb/mods/disturbed/disturbed.py:2033,2047,2050,2112` uses hillslope
`domlc_d`, dominant `domsoil_d`, and unprefixed source `plants[0]` rather than
final MOFE segment assignments and synthesized names. Consequently, the writer
cannot reliably carry segment-specific texture/disturbance coefficients into
the final management crop lookup.

Minimal repair: join existing segment soil/management coefficient selection to
final serialized crop identity. Preserve lookup values and existing fallback
rules unless separately authorized. Acceptance needs a mixed-soil,
mixed-disturbance profile with actual prepared inputs and native lookup readback.

### PMET-03: eight-character lookup collisions

High impact when colliding keys have different coefficients; confirmed static
representation gap, not a reproduced full model outcome.
`wepppy/wepp/management/utils/multi_ofe.py:309,314` prefixes plant names with
`OFE<n>_`; `managements.py:1845` serializes full names. Native
`/workdir/wepp-forest/src/scenhd.for:47` reads `a8` and
`pmetcoef.for:35,60-65` uses eight-character names and the first matching row.
Different synthesized names sharing their first eight characters cannot select
distinct coefficients. Disturbed can also emit duplicate source plant names
with different texture-derived values across hillslopes.

Minimal repair: define native-compatible identity and conflict handling before
emitting all names. Equal-key/equal-coefficient deduplication is different from
conflicting coefficients. Validate common-prefix rotation names, long names,
same-name/different-texture hillslopes and row-order independence. Do not claim
that sorting alone repairs missing or conflicting rows.

### MAN-01: residue-addition plant references cross OFE boundaries

High impact; confirmed serialized and reparsed defect.
The ordinary merge renames plants but does not update `operation.data.iresad`
at `wepppy/wepp/management/utils/multi_ofe.py:304-345`. Its deduplicating branch
already performs that remapping at lines 184-186.
Two actual oats fixtures were combined, with OFE2's final residue plant `hmax`
changed to `0.123` solely to distinguish the definitions. The emitted table has
`L179_weed` at index 3 and `OFE2_L179_weed` at index 6, but `OFE2_RES_2` points
to index 3 after parsing the emitted file. Serialization succeeds with the wrong
plant reference.

Minimal repair: apply the existing residue-reference remapping in the ordinary
merge branch. Acceptance must serialize and reparse different residue plant
definitions, verifying operation codes 10 and 12 against their intended OFE.

### MAN-02: mixed rotation periods lose the later OFE's schedule

High impact; confirmed in-memory synthesis and emitted scenario omission.
Both merge branches follow the first management's rotation/year topology
(`multi_ofe.py:241-246,366-372`). Combining oats with two one-year rotations
as OFE1 and a two-year corn/soybean rotation as OFE2 keeps only `OFE2_Year 1`;
Year 2 is removed by yearly compaction. Four-year expansion repeats Year 1.

Minimal repair requires a temporal alignment decision: preserve each source's
schedule over the requested simulation interval, or explicitly reject
unsupported combinations. Do not silently truncate. Validate 1/2-year and
2/3-year cycles, multiple rotations and final per-year OFE references.

### MAN-03: multiple-rotation expansion fails emitted readback

High impact; confirmed parser failure, root cause not fully isolated.
The same mixed management, expanded with `build_multiple_year_man(4)`, writes
`rotation_expanded.man` that `read_management()` rejects with
`IndexError: pop from empty list`. Unexpanded combined readback also changes
one OFE2 yearly-reference list. The earlier exploratory result inspected
in-memory references only; retained evidence now distinguishes these stages.

Investigate `managements.py:2740-2806` together with rotation serialization and
the aliasing/reuse of source year objects in MOFE synthesis. Do not attribute
the parser failure exclusively to one mechanism before isolation. Acceptance
must compare intended timelines, in-memory timelines, serialized/reparsed
timelines and native consumption for multiple-rotation inputs.

## Verified boundaries and remaining risks

Normal preparation ordering is correct: `wepp_prep_service.py:64-73` prepares
MOFE managements before lines 106-107 produce PMET. No ordering defect was
established. Native selection is per current OFE crop, not restricted to OFE1.
The generic collector's `list(set(...))` also makes the fallback first row
unstable; include determinism in the repair.

The separate native audit identifies PMET array capacity and consumer bounds;
coordinate that gate before increasing admitted crop counts. This report does
not establish deployed incidence, field-output magnitude, full native validity,
or complete coverage of all management families. No broad tests ran.

## Reproduction and provenance

Executed from `/workdir/wepppy` (resolved `/home/workdir/wepppy`) with
`/workdir/wepppy/.venv/bin/python`, Python 3.12.3, GCC 13.3.0,
Linux 6.8.0-146-generic x86_64, glibc 2.39. Git HEAD was
`41c8b53cfe93f9657a0ce53f602e3e134b48d172`; individual source hashes bind the
working tree rather than assuming HEAD describes all concurrent work.

```bash
/workdir/wepppy/.venv/bin/python \
  docs/work-packages/20261102_mofe_input_producer_audit/artifacts/reproduce_management_audit.py \
  --repo /workdir/wepppy \
  --output-dir docs/work-packages/20261102_mofe_input_producer_audit/artifacts/management_reproduction
```

For a repeat, choose a fresh output directory. The harness refuses an existing
destination and checks source hashes again after execution. It imports actual
writers without mocks, uses an existing test fixture and catalog managements,
and records failures explicitly. A zero harness exit means observations were
captured, not that the input producers passed.

- [Reproduction script](reproduce_management_audit.py)
- [Observations, command, source hashes and environment](management_reproduction/observations.json)
- [SHA256 manifest of all retained generated inputs and observations](management_reproduction/manifest.json)
- [First attempt failure](management_reproduction_attempt1/failure.json)
- [First attempt artifact hashes](management_reproduction_attempt1/manifest.json)

The first attempt stopped on expanded-file readback; its generated files are
retained unchanged. The revised harness records that failure as an observation.
All retained artifacts are text; no binaries or model outputs were generated.
