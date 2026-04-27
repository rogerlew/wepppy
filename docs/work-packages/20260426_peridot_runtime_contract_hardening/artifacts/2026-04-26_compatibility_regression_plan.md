# Compatibility and Regression Plan (2026-04-26)

This plan must be read before editing Peridot or WEPPpy code for `20260426_peridot_runtime_contract_hardening`.

## Contract Change

`sub_fields_abstraction` currently writes `field_flowpaths.csv` with duplicate `topaz_id` headers:

```text
field_id,topaz_id,sub_field_id,topaz_id,fp_id,...
```

The intended canonical schema is:

```text
field_id,topaz_id,sub_field_id,flowpath_topaz_id,fp_id,...
```

Meanings:

- `field_id`: source field ID from the field-boundary raster.
- `topaz_id`: parent hillslope/subcatchment ID. This name is preserved for WEPPpy compatibility.
- `sub_field_id`: Peridot-assigned sub-field ID.
- `flowpath_topaz_id`: topaz ID stored on the flowpath record itself, formerly emitted under the second duplicate `topaz_id` header.
- `fp_id`: flowpath ID within the sub-field flowpath bundle.

## Compatibility Rules

- New Peridot outputs must use `flowpath_topaz_id` and must not emit duplicate headers.
- WEPPpy `post_abstract_sub_fields` must accept the new canonical CSV schema.
- WEPPpy `post_abstract_sub_fields` must accept historical CSVs where pandas has read the duplicate second header as `topaz_id.1`.
- If both `flowpath_topaz_id` and `topaz_id.1` are present, WEPPpy must fail explicitly with a clear error because the input is ambiguous.
- If neither `flowpath_topaz_id` nor `topaz_id.1` is present, WEPPpy may proceed only if the field is demonstrably unused; otherwise it must fail explicitly with a schema error.
- Existing historical run artifacts are not rewritten by this package.

## Regression Tests

Peridot tests should cover:

- `write_field_subflows_metadata_to_csv` emits unique headers.
- The header row includes `flowpath_topaz_id` exactly once.
- The parent column remains `topaz_id`.
- CLI wrappers for `abstract_watershed` and `wbt_abstract_watershed` propagate underlying `io::Result` failures rather than returning success.

WEPPpy tests should cover:

- New CSV schema with `flowpath_topaz_id` normalizes to Parquet with `topaz_id`, `flowpath_topaz_id`, `sub_field_id`, and `fp_id` numeric columns.
- Historical CSV schema read by pandas as `topaz_id.1` normalizes to canonical `flowpath_topaz_id`.
- Ambiguous input containing both `flowpath_topaz_id` and `topaz_id.1` fails explicitly.

## Documentation Updates

Update these docs when implementation lands:

- `/home/workdir/peridot/docs/contracts/watershed-output-contract.md`
- `/home/workdir/peridot/docs/migration/prepwepp-to-peridot.md`
- `/home/workdir/peridot/docs/operations.md` if validation examples change
- `/workdir/wepppy/wepppy/nodb/mods/ag_fields/README.md`
- `/workdir/wepppy/docs/dev-notes/data_tables_standardization.spec.md` if field-flowpath parquet schema is described

## Validation Commands

Peridot:

```bash
cd /home/workdir/peridot
cargo test --test watershed_parquet_manifest
cargo test --test <new_or_updated_subfield_schema_test>
cargo test --test <new_or_updated_cli_error_contract_test>
cargo test
```

WEPPpy:

```bash
cd /workdir/wepppy
wctl run-pytest tests/<targeted_peridot_or_agfields_test>.py
wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_runtime_contract_hardening
```

If full `cargo test` or broad WEPPpy tests fail due unrelated preexisting failures, record targeted pass results and the unrelated failure signature in the validation artifact.
