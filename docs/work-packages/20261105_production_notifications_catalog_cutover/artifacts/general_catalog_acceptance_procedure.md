# Independent general-cycle artifact and age acceptance

This procedure supplements the bounded observer; it does not release admission,
enqueue work or repair a catalog. Run it under the actual worker UID 1002/GID 130
with the converged production configuration. Retain private paths and accounts
only in the mode-0700 observation evidence directory.

## Coverage and launch preparation

Before observer launch, select representative existing production/model scopes
and write a private `artifact-samples.json` array:

```json
[
  {
    "path": "/wc1/runs/<shard>/<owned-run>",
    "datasets": [
      "watershed/channels.parquet",
      "wepp/output/interchange/H.pass.parquet",
      "climate/<actual-dataset>.parquet"
    ]
  }
]
```

Use actual catalog keys, not these placeholders. Include available writable
examples from all four namespaces, a nested/parent-backed scope when present,
and the newly executed model scope. Record why a class has no eligible writable
Parquet example; do not silently replace an uncovered class with another owned
fixture. Readonly noninterference remains separate preserved evidence; generic
refresh does not publish readonly projects. At most 32 scopes and 16 explicit
Parquet keys per scope are supported by this bounded helper. These are observation
limits, not claims of statistically representative coverage.

Copy the reviewed helper into the existing private evidence directory and retain
its SHA256. Verify the observer's manifest/target-cycle files and the canonical
worker configuration agree. Do not change the application or import an override
to make a production check pass. Keep the parent heartbeat monitor running while
the separate readback process executes.

## Readback after the target cycle completes

Wait for matching completed cursor/discovery cycle, zero frontier/stream, no cycle
errors or cycle-pending items. The observer must remain healthy and must already
have retained genuine ordinary arrivals. The helper rechecks completion before
and after its census. Use the existing worker and a new output filename per attempt:

```bash
wctl docker compose exec -T rq-worker /opt/venv/bin/python \
  /wc1/query-catalog-validation/20261106/general-observation-01/read_general_catalog_evidence.py \
  --evidence /wc1/query-catalog-validation/20261106/general-observation-01 \
  --samples /wc1/query-catalog-validation/20261106/general-observation-01/artifact-samples.json \
  --output /wc1/query-catalog-validation/20261106/general-observation-01/artifact-census-01.json \
  --maximum-seconds 1800 --maximum-scopes 100000
```

The helper WATCH-validates the union of retained cycle `:scopes`, dirty-index,
cursor-pending and admitted locators. It does not recursively enumerate roots
again. Alias locators deduplicate by canonical scope ID, with matching physical
identity/incarnation/catalog bytes required. Deleted children are reported
separately after the canonical validator establishes that their root still exists;
a missing required namespace is not a successful deletion.

Every retained live scope receives raw incarnation/status/catalog/receipt checks.
The helper reads twice around each metadata observation and rejects detected
changes. It never creates an incarnation, acknowledges a receipt or invokes
`run_query()`, whose freshness barrier can repair publication. Representative
artifact checks validate actual Parquet metadata/schema and the production query
planner/executor's count against Parquet row counts. Source identity/stat and
catalog publication must remain unchanged around the check. No native scientific
model is run and no model outputs are rewritten.

## Interpreting ages and coverage

- `oldest_pending_receipt_age_seconds` is the oldest observed immutable receipt
  creation time among the full retained union during this census. If no receipt
  exists, the age is null and the receipt count is zero. Null with a nonzero
  unknown-age count is missing evidence, not zero delay.
- `pending_or_noncurrent_writable_scopes` measures actual pending/noncurrent raw
  metadata. For those scopes, a matching retained published attempt can establish
  last-publication age. A queued/running status timestamp is not publication age.
  Missing provenance remains explicitly unknown.
- `current_publications_predating_cycle` and oldest current-publication age are
  separate metrics. An older current publication is not automatically an
  unreconciled scope. The cursor's cycle-pending state and complete-cycle evidence
  establish cycle progress; publication time alone does not prove a cycle visit.
  Newly refreshed artifact samples deliberately require a publication during the
  target cycle. Do not force extra publication solely to change an age metric.
- Record measured discovery and reconciliation duration separately from configured
  cycle spacing, which starts after prior completion. Counts of locator traversal
  and unique scopes must remain distinct. A completed retained inventory does not
  discover projects created after its frontier passed them.

This is an interval census, not an atomic filesystem snapshot. Its scope is broader
than the observer's pending/admitted sample but still limited to the retained
union. It cannot reconstruct the peak age of receipts already acknowledged before
the census, prove the oldest undiscovered project during traversal, or certify
every scientific dataset from representative queries. Report those limits beside
the actual numbers. Do not relabel cycle elapsed time as oldest unreconciled age.

## Authoring acceptance

The helper always leaves `pending_age_coverage_accepted=false`. Do not rename its
output to `artifact-acceptance.json` or set that field merely because exit status
is zero. Independently review:

1. The observer is uninterrupted, target cycle is still the same, and its ordinary
   wait/cap/configuration/failure checks pass.
2. The census says `readback_complete`, has no errors, retains stable membership
   and clean start/end cycle checkpoints, and accounts for all four namespaces.
   Explain deleted children and readonly exemptions without treating them as
   refreshed writable projects. Unknown receipt/publication ages for unresolved
   writable scopes leave the age gate open.
3. Read the actual pending/noncurrent counts and ages. Resolve or explicitly retain
   any pending/noncurrent scope as incomplete rollout evidence; a conservative
   acceptance checkpoint has none. Older otherwise current publications are a
   separate observation and do not alone block acceptance.
4. The selected namespace/project-class matrix is adequate, each listed catalog,
   schema and query check passed, and expected model/report/HTTP evidence remains
   valid. Document uncovered classes rather than implying whole-fleet parity.
5. Retain the census/sample/helper hashes, observation timestamps, actual measured
   cycle duration and coverage limitations in the acceptance record.

Only then write a new private acceptance record atomically with the exact target
`cycle`, literal booleans `artifacts_verified=true` and
`pending_age_coverage_accepted=true`, and the reviewed evidence references/hashes,
reviewer, sample matrix, age summary and limitations. The observer independently
requires its same-cycle completion and coherent zero-outstanding checkpoint.
An incomplete census, exhausted readback bound or unavailable namespace leaves
acceptance absent; retain diagnostics and follow the existing observer deadline
and owned-pause procedure. Do not manufacture a timestamp or reset retained state.
