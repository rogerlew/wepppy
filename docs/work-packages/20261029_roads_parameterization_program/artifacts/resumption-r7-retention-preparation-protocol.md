# Revision-7 paired retention preparation protocol

Status: authored for parent review; declaration and preparation have not run.
The [helper](resumption_r7_retention_prepare.py) has separate `declare` and
`prepare` actions. Neither action fetches source data or invokes a native model.
This protocol follows the [role API review](resumption-r7-retention-role-api-review.md)
and [source feasibility review](resumption-r7-retention-feasibility-review.md).

## Purpose and fixed scope

Prepare default/optional pairs for B2/B3 small-failure cases, B4 passing control
and B5 opposite-direction control. Use the exact r7 modern seed tasks:

| Case | Stratum | Climate | Material | Geometry / surface / traffic |
| --- | --- | --- | --- | --- |
| B2 | small_gravel_less_runon | flagstaff | 1718494 | outunrut / gravel / high |
| B3 | small_gravel_dry_legacy | denver | 1718494 | outunrut / gravel / high |
| B4 | passing_same_signature | site | 1718465 | outunrut / gravel / high |
| B5 | underprediction_less_supply | site | 2711184 | outunrut / gravel / high |

Each task remains `erosion_road_cap`, runtime `project`, road/fill/buffer order,
9002, unchanged density, source-preserving full depth and initial saturation 0.75.
Compare the admitted explicit policy against the unchanged default builder from
the same fresh source cohort. Do not fit new parameters or change native code.
No withheld material or outcome is admitted. This is a preparation gate, not
full project-controller validation or scientific acceptance.

## Source prerequisite and declaration

QA owns the fresh seven-development-material acquisition under
`/wc1/runs/ro/roads-parameterization-program-20261103/retention-source-v1`.
The helper requires the final `acquisition.json` to pass source association and
bind `collection.sqlite`, `cache-association.json`, `declaration.json` and the
complete requested/represented set:
1718465, 1718494, 1718510, 1856573, 2711184, 2711250 and 53949.
The source receipt is the SHA256 of that actual acquisition JSON, not a new
receipt invented from an older cache or rounded model inputs. The finalized
cache must have no WAL/SHM companions.

The `declare` action binds every retained cohort file, all four selected seed
tasks' twelve exact native input filenames and auxiliary `reference.sol`, the
matched legacy soil inputs supplying road priors, the lookup, exact r7 binary,
protocol, actual installed source/consumer dependencies, numeric code/model
resources and interpreter/UID/GID. It creates a fresh exclusive evidence root
and copies the helper/protocol as declared snapshots. It does not build sources.

Later, after the source gate and parent review, the declaration command is:

```bash
wctl exec weppcloud python /workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts/resumption_r7_retention_prepare.py declare
```

The parent inspects that concrete declaration and records its digest before
launching `prepare --declaration-sha256 <reviewed digest>` in the same installed
environment. Any input, dependency, source cohort, interpreter or identity change
invalidates the declaration. The digest is an integrity binding; it does not
replace the independent review or imply that a declaration has already passed.

## Preparation mechanics

The helper copies the bound finalized cache into the fresh evidence root.
`SurgoCollectionWorkerViewFactory` opens it read-only and builds the same
in-memory view used by the owned source builder. The installed
`_build_soil_for_process` builds all seven profiles in each arm sequentially,
using unchanged horizon defaults and `ksflag=0`. Both complete requested sets
must succeed before source files are published. No collection constructor is
used: its cache synchronization can refetch a completely empty auxiliary response.
No network hook, research overlay or substitute source calculator is installed.

Original horizon fields are joined back to the actual bound cache. Paired
component selection, horizon masks, restrictive selection and default FC/WP
branch values must agree. Source-v3 companions validate optional decisions and
actual serialized rows. Ordinary default files remain unmarked.

For each arm and case, the output layout is:

```text
retention-preparation-v1/
  source-builds/{default,optional}/<mukey>.sol[.retention.json]
  {default,optional}/B2/                 # similarly B3, B4, B5
    soils/<mukey>.sol[.retention.json]
    soils/B2-{road,fill,buffer}.sol[.retention.json]
    soils/B2-stack.sol[.retention.json]
    runs/p1.sol[.retention.json]
```

Copying a source-v3 pair into a case preserves its bytes and source receipt;
source companions have no parent paths to relocate. The source, role and stack
parents stay together in that case's `soils` directory. The final soil is
validated recursively with the case directory as caller-owned provenance root.
A later runner can add the remaining eleven exact native inputs to `runs`
without moving the marked soil or breaking its parent references.

Each role goes directly from source through the installed
`_build_disturbed_mofe_soil`. Road replacements compose bare lookup conductivity
and the bound matched legacy cap, and copy the frozen road erosion values.
Fill/buffer use the bound bare/forest rows. Density remains blank/no override;
Rosetta density recomputation and organic-row removal are disabled. Fresh source
texture must still match the declared lookup class; otherwise retain the failure
for review. No global lookup or persisted project state is modified.

The installed `SoilMultipleOfeSynth.write` stacks those role treatments, followed
by installed `prep_soil` with saturation 0.75, no conductivity override, clipping
false and minimum-depth extension false. The old bridge's direct mutation is
never used. All optional outputs and companions are exclusively created.

## Artifact gates and distinct comparisons

Independent readback parses every paired source, role, stack and final soil,
including all seven native hydraulic trailer fields in 9002 rows. Excluding
comment/header provenance, only horizon FC/WP may differ between policy arms.
Native hydraulic trailer FC/WP are separate fields and must remain identical.
Optional companions must recursively validate against actual source/parent
hashes, lineage and settings; default artifacts receive no fabricated companions.

Compare fresh default against each frozen U12 input separately, retaining every
changed field. This captures source-vintage or current-builder drift without
attributing it to the optional policy. Material-value drift is reported for
review; it cannot be presented as a clean recovery of the old frozen baseline.

Ordered horizon depths must exactly match the frozen role profiles, including
the 200 mm support boundary. B2/B3 must retain **1600 mm in all three roles**.
Retain structural drift in `case-readback.json`, then fail the preparation gate.
Changed geometry requires a declared amendment before native work. A fresh
1718494 source producing no final FC/WP contrast also stops the pilot for review.

The outputs are `source-readback.json`, `case-readback.json`, and a final
`preparation-result.json` binding their hashes and the generated inventory.
Success establishes paired preparation only; the parent reviews artifact parity,
geometry, eligibility and fresh-default drift before any later native campaign.
The protocol does not create a native runner or copy the other native inputs.

## Failure preservation and next boundary

An exclusive `preparation-start.json` prevents a second attempt in the same root.
Any preparation exception records `preparation-failure.json` with retained
artifact inventory and re-raises. No retry, overwrite, deletion or cleanup occurs.
Use a separately declared fresh versioned root after reviewing any failure.
Interrupted runs retain their start receipt and partial artifacts even if no
failure receipt can be written.

No scientific gate, default, formula, UI, source-family admission or release
authority changes. This task authors the helper/protocol only. Acquisition,
declaration, preparation and model execution remain distinct retained actions.
