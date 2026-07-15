# WEPP Interchange

WEPP interchange converts WEPP hillslope and watershed text reports into
versioned, unit-aware Parquet datasets for queries, derived products, and
exports. WEPPpy provides the public orchestration API;
`wepppyo3.wepp_interchange` is the required report parser and primary Parquet
writer.

## Runtime Contract

There is one production conversion path:

```text
WEPP text reports
    -> WEPPpy public facade and orchestration
    -> required WEPPpyo3 parser/writer
    -> atomic Parquet publication
    -> DuckDB queries, derived products, and exports
```

WEPPpy does not recover from a missing or failing native writer by parsing the
report in Python. The public exception hierarchy is:

- `WeppInterchangeNativeError`: base native-boundary failure;
- `WeppInterchangeUnavailableError`: missing module or required symbol;
- `WeppInterchangeExecutionError`: native parse, I/O, schema, or writer failure.

Each error identifies the operation, retains the original failure as its cause,
and stops before replacing the affected final target. See the
[native contract](wepppyo3-interchange-spec.md) and
[ADR-0020](../../../docs/adrs/ADR-0020-require-wepppyo3-interchange.md).

## Outputs

Hillslope writers combine sorted per-hillslope sources into one table. Each
source maps to one Parquet row group in source order.

| Input pattern | Output |
| --- | --- |
| `H*.pass.dat` | `H.pass.parquet` |
| `H*.ebe.dat` | `H.ebe.parquet` |
| `H*.element.dat` | `H.element.parquet` |
| `H*.loss.dat` | `H.loss.parquet` |
| `H*.soil.dat` | `H.soil.parquet` |
| `H*.wat.dat` | `H.wat.parquet` |

Watershed writers produce:

| Input | Output |
| --- | --- |
| `pass_pw0.txt` | `pass_pw0.events.parquet`, `pass_pw0.metadata.parquet` |
| `ebe_pw0.txt` | `ebe_pw0.parquet` |
| `chan.out` | `chan.out.parquet` |
| `chanwb.out` | `chanwb.parquet` |
| `chnwb.txt` | `chnwb.parquet` |
| `soil_pw0.txt` or `.gz` | `soil_pw0.parquet` |
| `loss_pw0.txt` | average and all-years hill, channel, outlet, and class-data Parquet tables |
| `tc_out.txt` | `tc_out.parquet` |

The aggregate entry points preflight all required native symbols for the selected
formats before removing incompatible output or starting conversion. Watershed
formats run concurrently after that preflight; hillslope formats run as
source-ordered native bulk conversions.

## Quick Start

```python
from pathlib import Path

from wepppy.wepp.interchange import (
    run_wepp_hillslope_interchange,
    run_wepp_watershed_interchange,
)

output = Path("/wc1/runs/example/wepp/output")
run_wepp_hillslope_interchange(output, start_year=2000)
run_wepp_watershed_interchange(output, start_year=2000)
```

Both aggregate functions return `output/interchange`. Individual public writers
return the path or paths established by their existing facade contract.

`delete_after_interchange=True` removes covered text sources only after the
selected aggregate completes and writes its version manifest. Source removal is
audited in `wepp/output/interchange.log`.

## Version and Schema Metadata

Every primary table carries the dataset version metadata defined by
`schema_with_version()`, including `dataset_version_major` and
`dataset_version_minor`. `interchange_version.json` records the directory-level
version.

A major version mismatch causes `remove_incompatible_interchange()` to remove
stale Parquet before regeneration. A minor version is additive and compatible.
Downstream consumers can use `needs_major_refresh()` before opening an older run.

Fields carry `units` and `description` metadata. Unit metadata documents values;
query engines do not apply conversions automatically.

Calendar-aware formats use a discovered `climate/wepp_cli.parquet` when present.
If no climate resource exists, native writers use their established Gregorian
behavior. An existing unreadable climate Parquet fails explicitly.

## Public APIs

The main orchestration and consumer APIs are:

| Function | Purpose |
| --- | --- |
| `run_wepp_hillslope_interchange()` | Generate all selected hillslope tables and the version manifest. |
| `run_wepp_watershed_interchange()` | Generate the selected watershed tables and the version manifest. |
| `run_wepp_*_interchange()` | Generate one report family's primary Parquet output. |
| `run_totalwatsed3()` | Build daily watershed hydrology, sediment, baseflow, and optional ash summaries with DuckDB. |
| `generate_interchange_documentation()` | Render schemas and sample rows beside a generated interchange directory. |
| `totalwatsed_partitioned_dss_export()` | Write per-channel DSS time series. |
| `chanout_dss_export()` | Write channel peak DSS records from `chan.out.parquet`. |

`max_workers` remains accepted by hillslope facades for caller compatibility,
but parsing and primary Parquet construction occur inside the native bulk writer.

## Derived Products

`run_totalwatsed3()` joins hillslope PASS and WAT Parquet with DuckDB. It can add
baseflow diagnostics and first-year ash transport mass from ash-run Parquet.
See [README.totalwatsed3.md](README.totalwatsed3.md) for formulas and units.

DSS export reads interchange and derived Parquet; it is not part of the native
report parser boundary. See [README.dss_export.md](README.dss_export.md) for the
DSS and browse workflow.

The query engine discovers interchange tables through the required native
`catalog_scan` operation, then uses DuckDB for table access. Incremental
catalog bookkeeping remains Python orchestration, but a full scan does not have
a Python implementation.

## Adding or Changing a Format

A new primary format requires paired changes:

1. Add or change the parser, schema metadata, atomic writer, and release export
   in `/home/workdir/wepppyo3/wepp_interchange`.
2. Build and test the release package under
   `/home/workdir/wepppyo3/release/linux/py312`.
3. Add or update the stable WEPPpy facade, schema declaration, stub, and aggregate
   preflight symbol inventory.
4. Add fixture coverage for values, metadata, row ordering, native failure, and
   target non-publication.
5. Update the native contract and bump `INTERCHANGE_VERSION` when compatibility
   rules require it.
6. Recreate every local Python service that imports WEPPpyo3 and verify the
   loaded extension path and SHA-256.

Do not add a Python report parser, record-batch builder, or alternate primary
Parquet writer as a recovery path. Rollback restores a known-good paired release.

## Validation

Run focused WEPPpy validation with:

```bash
wctl run-pytest tests/wepp/interchange
wctl run-stubtest wepppy.wepp.interchange
wctl check-test-stubs
```

Run the native crate and release-package validation from `/home/workdir/wepppyo3`:

```bash
cargo test -p wepp_interchange_rust
PYTHONPATH=release/linux/py312 \
  /home/workdir/wepppy/.venv/bin/pytest -q tests/wepp_interchange
```

The release tests must import the release tree being deployed, not an unrelated
installed copy.

## Troubleshooting

### Native module unavailable

Confirm the paired release exports the full API and that the runtime imports its
shared object from the expected release tree. In the local forest stack,
`docker/wepppyo3-interchange-preflight.py` logs the resolved path and SHA-256 for
the web, query, RQ, worker, and scheduler processes and rejects a baked
development copy when the bind-mounted release is authoritative.

### Native conversion failed

Read the `WeppInterchangeExecutionError` message and chained cause. Native errors
include operation context; parser errors should include the source and record
location when available. Fix the input or paired release, then rerun the facade.

### Version mismatch

Rerun the appropriate aggregate facade. It removes incompatible primary tables
and writes a current `interchange_version.json` after successful conversion.

### Empty tables

Check that WEPP completed and wrote the expected source names. A valid empty
Parquet may represent a present source with no report records; a missing source
may be either an allowed empty family or an explicit input error depending on the
format.

## Related Documentation

- [Native interchange contract](wepppyo3-interchange-spec.md)
- [Fixture and test guide](../../../tests/wepp/interchange/README.md)
- [WEPPpyo3-only cutover package](../../../docs/work-packages/20260715_wepppyo3_only_interchange/package.md)
- [Query engine](../../query_engine/README.md)
- [WEPPpy architecture](../../../ARCHITECTURE.md)
