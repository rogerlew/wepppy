# Consistent 200 mm soil boundaries

Status: complete locally, 2026-10-29. Implementation and validation complete; no deployment.

## Operator scope and rationale

The operator requests consistent 200 mm horizon insertion across soil writers
in WEPPpy and wepppyo3. This follows the native split/unsplit sensitivity study:
prepared-soil cases already include the boundary; raw generated writers do not
consistently include it. This package standardizes generated inputs, not native
WEPP code or road erosion parameters. It does not remove the boundary to lower
sediment or reopen the completed scientific study.

Default scope is generated/prepared soils. An optional clarification was sent
about uploaded soils; absent a requested change, preserve the explicit upload
contract and immutable accepted sources. Rust output-Parquet writers are not
WEPP input-soil writers and must not synthesize input horizons.

## Compatibility and regression plan

Generated output horizon counts may increase by one per OFE. Preserve version,
physical properties, total depth, restrictive data and all unrelated text;
insert a duplicate-material upper piece ending at 200 mm. Existing boundaries
and shallow profiles are unchanged. Do not merge layers or silently exceed the
native ten-layer capacity when adding a layer. Keep source objects immutable
when normalizing serialized output. Preserve source uploads and prior study data.

Trace all direct dataset writers, ordinary serialization, Disturbed conversion,
multi-OFE synthesis, Roads/channel assembly and deprecated file modifiers. Validate
consumed `wepp/runs` files, native split/unsplit replay, and representative direct
writers. Inventory wepppyo3 ownership without modifying unrelated native work.
No native release refresh, deployment or new dependency is planned.

See [plan](prompts/completed/implementation_execplan.md), [tracker](tracker.md),
[contract](../../schemas/soil-horizon-boundary-contract.md) and
[ADR](../../adrs/ADR-0110-generated-soil-200mm-boundary.md).

Writer ownership and existing legacy header limitations are recorded in the
[audit](artifacts/writer-audit.md). Native consumed-input/output identities and
calendar checks are retained in [native evidence](artifacts/native-evidence.json).

Final repository coverage: **12,135 passed, 298 skipped**. See
[validation](artifacts/validation.md) and [review](artifacts/review.md).
