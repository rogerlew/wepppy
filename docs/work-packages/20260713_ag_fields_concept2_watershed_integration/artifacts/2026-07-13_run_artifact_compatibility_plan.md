# AgFields Concept 2 Run-Artifact Compatibility and Regression Plan

Read this plan before editing AgFields persisted state, route payloads, or generated
run artifacts for the Concept 2 watershed integration.

## Compatibility Contract

The change is additive. Existing projects without Concept 2 state continue to load
and report watershed integration as not run. Do not rename or remove existing
AgFields NoDb keys, route response keys, parquet columns, task timestamps, or files.

Existing artifacts remain authoritative and immutable:

- `wepp/runs/` and `wepp/output/` are the baseline WEPP project.
- `wepp/ag_fields/runs/` and `wepp/ag_fields/output/` are independent sub-field
  simulations.
- `ag_fields/sub_fields/fields.parquet` keeps its current schema.

The implementation may add only this isolated tree:

```text
wepp/ag_fields/watershed/runs/
wepp/ag_fields/watershed/output/
wepp/ag_fields/watershed/manifest/
```

Clearing or retrying integration may remove only `wepp/ag_fields/watershed/` and
its associated additive NoDb signature/summary state. It must not toggle parent
`delete_after_interchange`, rewrite prepared parent inputs, or clear independent
sub-field results.

## Generated Schema Plan

Use versioned, additive artifacts. The initial contract includes:

- `manifest/pass_sources.parquet`: one row per parent/source with source kind and
  identity, parent/source raster and modeled areas, scale, climate/calendar proof,
  source full-run totals, status, and algorithm/ADR version.
- `manifest/pass_event_closure.parquet`: one row per affected parent/day with
  weighted input totals, reparsed combined totals, and residuals for every
  conserved water-volume and sediment-mass quantity.
- `manifest/pass_run_closure.parquet`: one row per affected parent with aggregate
  input/output totals and maximum/aggregate residuals.
- `manifest/integration_summary.json`: version, source signature, executable and
  PASS-family identities, counts, paths, warnings, timestamps, terminal status,
  and required-resource inventory.
- `manifest/README.md`: field definitions, units, algorithms, scientific warning,
  and evaluation-bundle orientation.

Exact columns must be documented before implementation. Add columns when necessary;
do not silently rename or remove them after generated-output acceptance.

## Parent PASS Compatibility

Concept 2 v1 consumes and emits legacy ASCII PASS. Independent AgFields outputs
already use that family. Parent PASS files are materialized from current prepared
`wepp/runs/p*` inputs inside the isolated workspace so the feature works when
baseline PASS files were deleted after interchange or the parent project selected a
different retained-output family.

Record parent and AgFields WEPP executable identities separately. Fail explicitly
when the selected binary cannot generate the required legacy family, a source PASS
is missing, or climate/calendar identity cannot be proved. Do not silently convert
HBP or reconstruct PASS from summary parquet.

## Regression Plan

Automated coverage must prove:

1. A pre-change AgFields NoDb payload loads with absent integration state and no
   migration write.
2. Existing AgFields state responses gain only additive fields.
3. Clear/retry operations cannot address paths outside the isolated subtree.
4. Parent/source area planning rejects overlap, negative/unknown/non-finite areas,
   missing translator ids, and mismatched raster ownership.
5. Weighted source totals close through serialized/reparsed combined PASS output.
6. Exactly one PASS exists for every parent consumed by the watershed run.
7. Required watershed/interchange artifacts propagate into the isolated output.
8. Existing baseline and independent sub-field artifact inventories and hashes are
   unchanged after success, failure, clear, and retry.
9. RQ single-flight, state, staleness, route auth, and canonical error contracts
   remain intact.

## Dev-Project Evidence Plan

Use `/wc1/runs/sa/sacral-self-discipline` only after focused tests pass. Before the
run, capture a hash/inventory manifest for all existing files under the four
authoritative trees. The project currently provides:

- 6,626 independent sub-field PASS sources;
- 1,869 affected parents and 3,543 total parents;
- no overcovered affected parent;
- 482 full-coverage parents; and
- deleted parent PASS files, requiring isolated materialization.

After the run, verify the original hash/inventory manifest, parent/source area
closure, event/full-run water and sediment closure, required artifact inventory,
and terminal state. Keep generated evidence under the work-package artifacts or the
isolated manifest tree; do not copy multi-gigabyte model outputs into git.

## Documentation Propagation

Update in the same implementation change:

- `wepppy/nodb/mods/ag_fields/README.md`
- `wepppy/nodb/mods/ag_fields/ui_control_layout.md`
- `wepppy/weppcloud/routes/usersum/weppcloud/ag_field-mod.md`
- `docs/schemas/rq-response-contract.md` only if the canonical envelope changes
  (it should not)
- `docs/schemas/output-scope-contract.md` only if standard reports add a new scope
- the work package, tracker, ExecPlan, ADR, queue catalog, and native module docs.
