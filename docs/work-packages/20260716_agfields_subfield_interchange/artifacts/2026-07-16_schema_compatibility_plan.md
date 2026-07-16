# AgFields Sub-field Interchange Schema Compatibility Plan

**Date**: 2026-07-16
**Status**: Pre-implementation contract
**Repositories**: `/home/workdir/wepppy`, `/home/workdir/wepppyo3`

## Mutation Summary

The package will add six dedicated AgFields writer APIs alongside the six native
ordinary hillslope bulk writers. The AgFields datasets begin with
`field_id: int32` and `sub_field_id: int32`, followed by the existing
measurement/date columns for that family. The numeric token in the raw `H<n>`
filename must equal `sub_field_id`. The parent hillslope `topaz_id` and
`wepp_id` are source context but are not the identity of the sub-field and are
not propagated as row identity.

The six existing ordinary public APIs and schemas are immutable for this package.
They must retain their field lists, field order, types, field metadata, dataset
metadata, row order, values, null behavior, compression, and public call
compatibility.

## Source Contract

WEPPpy builds the native mapping from
`<run>/ag_fields/sub_fields/fields.parquet`. Each row must provide finite,
integer-compatible `field_id`, `sub_field_id`, and the current parent context.
Before calling Rust, WEPPpy builds coupled
`(path, field_id, sub_field_id)` descriptors and must verify:

- `sub_field_id` is unique and positive;
- every target raw family contains exactly one `H<sub_field_id>` file;
- all six raw families contain the same identifier set;
- no mapping id is missing from the files and no file id is missing from the
  mapping;
- the mapping contains no duplicate or conflicting `field_id` for one
  `sub_field_id`;
- all ids fit the declared `int32` output type.

The native boundary repeats the one-to-one checks that are necessary to prevent a
Python caller from bypassing the contract. It must reject invalid mappings with
an explicit error and must not silently fill, drop, or infer identities.

## Output Contract

The six targets are:

- `H.pass.parquet`
- `H.ebe.parquet`
- `H.element.parquet`
- `H.loss.parquet`
- `H.soil.parquet`
- `H.wat.parquet`

For the AgFields dataset kind, place `field_id` and `sub_field_id` before the
existing measurement/date columns and omit `wepp_id` and `topaz_id`. Both
identity columns are required and non-null in actual rows. Empty outputs must
still expose the AgFields schema. Add dataset metadata that names and versions
the kind, for example `dataset_kind=ag_fields_hillslope` and
`ag_fields_schema_version=1`. Do not change the ordinary dataset version only to
describe this new kind. Existing `needs_major_refresh()` behavior is not enough
to establish AgFields readiness; the specialized orchestrator must validate the
dataset kind, schema version, and required columns. If implementation shows that
the canonical versioning machinery cannot represent the kind safely, stop and
revise this plan before changing the global interchange version.

## Backward Compatibility

Compatibility is additive and isolated:

- Existing Python positional and keyword calls remain valid because their
  functions do not change.
- Ordinary calls execute the pre-change path and emit the exact ordinary schema.
- Existing ordinary schema snapshots do not change.
- The new schemas exist only under `wepp/ag_fields/output/interchange` when the
  specialized orchestrator calls the dedicated APIs.
- Existing raw AgFields outputs, NoDb keys, RQ route payloads, and UI job keys do
  not change.
- The Features Export catalog changes its AgFields hillslope source keys to
  `sub_field_id` in the same change; baseline catalog entries do not change.
- The stage-4 RQ result may add a relative interchange path/resource summary, but
  must preserve `run_count` and existing status/error fields.

No user-visible key or column is renamed or removed.

## Downstream Propagation

The implementation must demonstrate that identities travel through all of these
boundaries:

1. `fields.parquet` source row;
2. WEPPpy strict mapping builder;
3. Python-to-PyO3 coupled source descriptors;
4. Rust record accumulation for all six writers;
5. Arrow schema and arrays;
6. staged Parquet files;
7. published AgFields interchange bundle;
8. RQ terminal result and discoverable run resource.

The generated run assertion is a full anti-join in both directions between the
distinct `(field_id, sub_field_id)` pairs in every output and the authoritative
source mapping. Row counts differ by report family, so acceptance compares
distinct identities and also asserts that every row is non-null and valid.

## Regression Matrix

### Native ordinary APIs

- Capture pre-change golden Parquet for one small fixture per family before code
  edits.
- After the change, compare schema, metadata, row values, ordering, and writer
  summaries. Use byte equality where writer metadata is deterministic; otherwise
  use exact logical and metadata equality and record why bytes differ.
- Cover legacy ASCII PASS and HBP PASS because both feed the same public writer.
- Preserve empty-output schemas and summaries.

### Native AgFields APIs

- Two files from different fields prove positive propagation.
- Two sub-fields from one field prove a non-unique `field_id` is valid while
  `sub_field_id` remains unique.
- Missing, extra, duplicate, conflicting, non-integer, out-of-range, and filename
  mismatch cases fail explicitly.
- An injected late-family failure leaves no final bundle.

### WEPPpy ordinary consumers

- Run all 22 native-only interchange schema snapshot checks.
- Run hillslope facade cleanup/publication tests and representative reports that
  query `wepp_id`.
- Confirm baseline and roads resource paths and schemas are unchanged.

### RQ and AgFields consumers

- Assert order: invalidate timestamp, run WEPP, build interchange, stamp
  timestamp, publish result, publish completion.
- Inject native failure and assert no timestamp/completion and no partial final
  bundle.
- Assert no new queue child or dependency edge.

### Generated forest corpus

The read-only discovery baseline on 2026-07-16 was:

- run root: `/wc1/runs/sa/sacral-self-discipline`;
- 6,626 files in each target raw family;
- 6,626 unique source `sub_field_id` values, range `1..6626`;
- 2,169 distinct source `field_id` values;
- about 13.5 GiB apparent input across the six target families, with about
  3.7 GiB allocated across all seven sparse raw families;
- no existing `wepp/ag_fields/output/interchange` directory;
- 1.1 TB free on `/wc1`.

Acceptance must inventory protected baseline `wepp/output`, AgFields watershed
scheme trees, NoDb files, and source mapping before conversion. After staged
publication it must verify the six resources, exact distinct identity coverage,
no null identities, dataset-kind/schema metadata, readable row groups, no leftover
stage directory, and byte-identical protected artifacts.

## Publication and Recovery

Write into a unique sibling stage owned by this run and job. Validate every file
before moving the bundle into its final path. If a prior complete bundle exists,
retain it until the new stage has passed validation, then use a recoverable
backup-and-replace sequence. Remove a backup only after the final directory is
confirmed readable. On any error, preserve raw reports, restore the prior bundle
if publication began, and leave a concise diagnostic identifying the failed
family and stage.

Rollback restores the prior WEPPpyo3 release artifact and WEPPpy code, restarts
the local stack, and optionally removes only the additive AgFields interchange
directory. Raw model outputs are sufficient to retry conversion without rerunning
WEPP.
