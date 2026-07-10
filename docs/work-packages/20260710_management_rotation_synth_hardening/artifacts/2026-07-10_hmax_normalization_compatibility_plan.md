# Applied-Residue `hmax` Compatibility and Regression Plan

Read this plan before editing AgFields plant archive ingestion.

## Additive State Contract

Existing `_plant_file_provenance` entries contain `source_filename`, `format`,
and `replaced`. The ingestion repair adds an optional `normalizations` list. Old
NoDb state without that key remains valid and inventory returns an empty list.
Each normalization record contains the scenario, field, original value,
normalized value, units, and reason.

No existing key is renamed or removed. Historical final `.man` artifacts are not
rewritten automatically. Re-uploading or otherwise reprocessing an archive
creates normalized final files; preserved `plant_files/2017.1/` sources remain
byte-identical to the uploaded originals.

## Normalization Contract

- Identify plant scenarios through parsed `ScenarioReference` relationships.
- A candidate must have `hmax <= 0`, be referenced by a cropland residue-addition
  operation (`pcode` 10 or 12), and not be referenced by a yearly `itype` or
  initial-condition `iresd`.
- Set only `hmax` to `0.00001 m`.
- Do not match names such as `L179_weed`; semantics, not naming, control behavior.
- Do not modify `cuthgt`, `rdmax`, `xmxlai`, operations, or active plants.
- Preserve top-of-file comments when rewriting an uploaded 98.4 management.

## Regression Plan

- Exact Jim-interface 2017.1 fixture: final downgraded management has the floor,
  archived original retains zero, and provenance reports the change.
- Raw 98.4 fixture: final management has the floor and header comments survive.
- Active zero-height plant: helper leaves it unchanged and reports no fallback.
- Re-upload: normalization provenance replaces deterministically with the file.
- Downstream synthesis: the p3733 schedule still yields 17 years, 3 plants, and
  10 operations; `L179_weed` now carries the floor.
- Current binary: `HMAX <= 0` is absent. Any later failure is captured separately.

## Rollback

Revert the ingestion helper and provenance addition. Re-uploaded normalized
files can be restored from their preserved 2017.1 source copies. No NoDb
migration is required because the additive provenance key is optional.
