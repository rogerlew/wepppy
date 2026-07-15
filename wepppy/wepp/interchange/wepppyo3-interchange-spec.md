# WEPPpyo3 Interchange Contract

## Status

- Implemented and required as of 2026-07-15.
- Owners: WEPPpy and WEPPpyo3 maintainers.
- Governing decision: [ADR-0020](../../../docs/adrs/ADR-0020-require-wepppyo3-interchange.md).

## Purpose

`wepppyo3.wepp_interchange` is the sole production implementation for parsing
WEPP report text, assembling records, and writing primary interchange Parquet.
WEPPpy preserves its public Python facades and orchestration, but it does not
contain a second report parser or primary writer.

This boundary keeps report conversion fast and makes release drift explicit.
Missing, incomplete, or failing native releases stop the operation instead of
continuing through a Python implementation with different resource behavior.

## Ownership Boundary

WEPPpyo3 owns:

- WEPP hillslope and watershed report parsing;
- typed record construction and schema metadata emitted by the writers;
- chunked Parquet writing and atomic target publication;
- one source-ordered row group per hillslope input file;
- watershed EBE outlet inference and raw `chan.out` peak-signal audit;
- watershed PASS climate-file hint discovery;
- the full query-engine catalog scan.

WEPPpy owns:

- stable public `run_wepp_*_interchange` facades;
- path discovery, option normalization, aggregate scheduling, and source cleanup;
- interchange version manifests and schema declarations used by consumers;
- climate Parquet discovery/materialization before the native call;
- DuckDB queries, DataFrame helpers, derived products, DSS exports, and schema
  documentation;
- stable Python exceptions at the native boundary.

An absent climate resource may select the established Gregorian behavior. An
existing unreadable climate Parquet is an error.

## Required Native API

The paired release must export callable implementations of all of these names:

| Area | Required symbols |
| --- | --- |
| Hillslope bulk writers | `hillslope_pass_files_to_parquet`, `hillslope_ebe_files_to_parquet`, `hillslope_element_files_to_parquet`, `hillslope_loss_files_to_parquet`, `hillslope_soil_files_to_parquet`, `hillslope_wat_files_to_parquet` |
| Watershed writers | `watershed_pass_to_parquet`, `watershed_ebe_to_parquet`, `watershed_loss_to_parquet`, `watershed_soil_to_parquet`, `watershed_chan_peak_to_parquet`, `watershed_chanwb_to_parquet`, `watershed_chnwb_to_parquet`, `watershed_tc_out_to_parquet` |
| Supporting native operations | `watershed_pass_cli_hint`, `catalog_scan` |

`wepppy.wepp.interchange._rust_interchange.REQUIRED_WEPPPYO3_INTERCHANGE_API`
is the executable inventory. Aggregate hillslope and watershed entry points
preflight the subset they are about to use before removing or publishing output.

## Data Contract

- Public WEPPpy facade return types remain `Path` objects.
- Parquet field names, types, units, descriptions, row ordering, and dataset
  version metadata remain compatible with the declarations in the facade
  modules.
- Hillslope bulk writers receive a sorted source list and emit one row group per
  source in that order, including an empty row group where the format contract
  requires source identity to be retained.
- Writers use Snappy compression unless their native API explicitly accepts a
  different supported value.
- Writers publish through a temporary path and rename only after a successful
  close. A failed operation must not replace its final target.
- Watershed PASS stages both outputs and watershed LOSS stages all eight outputs
  before sequential same-directory publication. If a later publication fails,
  the writer restores the preceding complete generation (or removes newly
  created siblings). This is failure-atomic rollback, not simultaneous
  multi-path visibility; the aggregate version manifest remains the completion
  signal.
- Multi-output formats return summary metadata but do not change the WEPPpy
  facade return contract.

## Failure Contract

WEPPpy exposes three exceptions:

- `WeppInterchangeNativeError`: base class for required-native failures;
- `WeppInterchangeUnavailableError`: import or required-symbol failure;
- `WeppInterchangeExecutionError`: parse, I/O, schema, or native writer failure.

Messages name the operation and native symbol. The original Python/PyO3
exception is retained as `__cause__`. There is no environment flag or runtime
path that selects a Python WEPP report parser.

Rollback restores a known-good paired WEPPpy/WEPPpyo3 release and restarts every
Python service that imports the extension.

## Release and Startup Contract

The development forest stack loads the bind-mounted release at:

```text
/workdir/wepppyo3/release/linux/py312/wepppyo3/
```

`docker/wepppyo3-interchange-preflight.py` verifies package and extension
origins, the complete required API, and logs the native shared-object SHA-256.
The web build entrypoint invokes it directly; query-engine, rq-engine, both RQ
worker services, and scheduler use it as their process entrypoint. The required
root resolves the production image symlink but rejects a baked development copy
when the bind-mounted release should be authoritative.

The release package and native shared object must be committed with provenance
that identifies the source commit used to build them.

## Validation

Before publishing a paired release:

1. Run the WEPPpyo3 Rust tests and release-tree Python tests.
2. Run `wctl run-pytest tests/wepp/interchange` in WEPPpy.
3. Run stub and changed-exception gates for the Python public surface.
4. Start or recreate every Python service that imports WEPPpyo3.
5. Confirm service logs report the expected extension path and SHA-256.
6. Exercise the public aggregate facades and a generated WEPP output without
   any Python-parser recovery telemetry.

The committed fixture suite covers all required facade formats, exact static
schema/field metadata snapshots, normalized run-dependent schema metadata,
row-group ordering, missing-symbol failure, native-execution failure, and
non-publication of failed targets.

## Related Documentation

- [WEPP interchange overview](README.md)
- [Retired migration plan](wepppyo3-interchange-plan.md)
- [Cutover work package](../../../docs/work-packages/20260715_wepppyo3_only_interchange/package.md)
- [WEPPpyo3 release documentation](../../../../wepppyo3/README.md)
