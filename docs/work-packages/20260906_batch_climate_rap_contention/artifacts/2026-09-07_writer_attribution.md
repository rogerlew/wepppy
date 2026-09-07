# Writer attribution and conformance decision

Starting revision: `aafeecc8c3bc3ba9dbf16fec66891770742b35f4`.
Independent source attribution: correctness reviewer `/root/correctness`.

## Scope and authority

The operator explicitly excluded rerunning the workload: this incident belongs
to a different Kubernetes deployment. Execute the code correction and isolated
validation; do not deploy or replay on forest or Kubernetes. The actual
deployment writer and post-fix recurrence remain unmeasured.

This is conformance to the unchanged NoDb persistence contract, "Writer
Ownership and Mutation Topology / Long-running collect-then-finalize pattern."
No scientific parameterization, output schema, queue edges, result tuple, or
completion trigger changes are authorized. No new normative contract decision
or ancestor checkpoint is required. The facade extraction standard's ordinary
lock-preservation rule is not an instruction to retain this explicitly scoped
persistence defect; the dispatched plan specifically corrects these boundaries.

## Source inventory

| Path | Confirmed writes and ownership |
| --- | --- |
| Climate router | Initial derived-state reset and station selection; observed staging now defers derived reset to successful publication. |
| Observed GridMET | Previously dumped at exit from its long `locked()` region; now collects and finalizes once. |
| PRISM revision | Previously dumped at exit from its long lock; workers write CLI artifacts only. GridMET PRISM now finalizes separately from channel collection. Other modes retain their previous path. |
| Seed initialization | `_ensure_cligen_seed` and `_build_climate_prism` can dump, but are not nested writers on the affected observed GridMET/PRISM path. |
| RAP | Constructor/year setters/acquisition exit/analysis exit are controller writers. Workers previously changed only local manager/data dictionaries and files. |
| Catalog | Python updates catalog JSON. Missing catalogs activate with `run_interchange=False`; Rust catalog scan only stats NoDb files. Neither is an invalidating controller writer. |
| Version hydration | Current migration is a no-op for controller payloads; writes `nodb.version` only. |
| Batch base resync | Directly rewrites Climate through `_write_nodb_document`, normally before hydration/build. Duplicate leaf execution could overlap it; no incident evidence proves duplication. |
| Copied identity | Clone updates `wd` but retains old `_group_name`; logger/status/lock keys can use the old batch name while filesystem/cache paths use the new `wd`. Confirmed separate defect, not proof of the incident writer; repair is deferred from this bounded finalization change. |

## Reproduction evidence

The first isolated run failed both new tests at the real `NoDbBase.dump()`:

- PRISM: expected `(mtime=1788763809.202944, size=571)`, observed
  `(mtime=1788763810.202944, size=571)`.
- RAP analysis: expected `(mtime=1788763809.8389573, size=3703)`, observed
  `(mtime=1788763810.8389573, size=3703)`.

The exact invalidating writer in these tests is `_same_size_rewrite`, called
from the injected raster/CLI collection seam in a worker thread. It atomically
replaces a real temporary controller file, changing one equal-width field and
advancing mtime by one second. No dump, lock, stat, or hydration safety boundary
is mocked. This reproduces the signature mechanism, not the Kubernetes cause.

The RAP serialization size changes after the correction because its override
now uses `super().__getstate__()` rather than discarding the filtered state;
runtime logging objects are no longer copied into the persistent payload.
Application fields and legacy reads remain compatible.

## Valid-state and compatibility matrix

Absent RAP manager/source fails before publication; acquisition can initialize
its year/manager state. Empty summaries publish empty typed parquet. Populated
single-/multi-OFE summaries preserve all six bands and units. Legacy embedded
band mappings and integer dataset keys load. Malformed embedded data or years
fail explicitly. Unrelated rewrites survive; relevant year/map/raster/CLI
rewrites reject outputs. Collection, pre-commit, post-commit, unknown-outcome,
and lock-takeover tests verify persistence and artifact behavior. A real GDAL
fixture exercises Rust medians, parquet reload, and `wepp/runs/p1.cov` output.

See [current operator/developer notes](../../../dev-notes/batch-climate-rap-finalization.md)
for publication ordering, recovery limitations, and recurrence signals.
