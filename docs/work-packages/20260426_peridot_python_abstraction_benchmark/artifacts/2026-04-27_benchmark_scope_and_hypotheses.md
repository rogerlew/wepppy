# Benchmark Scope and Hypotheses (2026-04-27)

## Scope Statement

This benchmark package compares Peridot watershed abstraction against the legacy WEPPpy Python-based abstraction path. The Python path is the requested benchmark target and comparator, but it is stale. The package must verify that it still runs before collecting performance numbers.

## Initial Comparator Map

- `confirmed`: Peridot is invoked from WEPPpy through `/workdir/wepppy/wepppy/topo/peridot/peridot_runner.py`.
- `confirmed`: The legacy Python watershed abstraction implementation is in `/workdir/wepppy/wepppy/topo/watershed_abstraction/watershed_abstraction.py`.
- `confirmed`: The NoDb-level TOPAZ Python abstraction path is `/workdir/wepppy/wepppy/nodb/core/watershed.py::_topaz_abstract_watershed`.
- `confirmed`: `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py::abstract_watershed` dispatches to Peridot when `abstraction_backend` is `peridot`; otherwise it calls the TOPAZ Python path when the delineation backend is TOPAZ.
- `inference`: The first benchmark should use TOPAZ-derived inputs because that is the path the Python comparator was designed around.
- `hypothesis`: WBT-derived Peridot benchmarks may need a different comparator or a separate Python/WBT compatibility path.

## Measurement Hypotheses

- `hypothesis`: Peridot will complete representative watershed abstraction faster than the Python comparator on the same TOPAZ-derived inputs.
- `hypothesis`: Peridot will scale better as raster cell count, hillslope count, channel count, or flowpath count increase.
- `hypothesis`: Peridot can expose stronger parallelization potential because the Rust/Rayon implementation can partition work differently than the Python multiprocessing path.

These hypotheses must not be used as claims until benchmark artifacts convert them to `confirmed` or bounded `inference` statements.

## Required Metrics

### Scalability

Record wall-clock runtime and input workload size. Workload size should include available proxies such as raster cell count, hillslope count, channel count, flowpath count, and source file sizes. A scalability statement is only valid for the measured workload range.

### Topology Flexibility/Correctness

Record whether each abstraction path produces structurally valid watershed outputs for the same input topology. Checks should include required file presence, table schemas, row counts, unique topaz/wepp IDs, network or structure consistency, and slope-file presence.

### Parallelization Potential

Record concurrency settings and, where practical, process or CPU utilization evidence. Compare controlled worker-count runs before claiming parallel speedup. Without controlled worker-count runs, keep parallelization statements as `hypothesis` or clearly marked `inference`.

## Safety Boundaries

- Do not run benchmark commands directly in canonical run roots.
- Do not mutate `/wc1/runs`, `/geodata/weppcloud_runs`, `/geodata/wc1`, or source fixture directories.
- Do not stage Peridot `target/release/*` binaries while collecting benchmark evidence.
- Do not publish universal speedup claims from smoke fixtures.

## Expected First Failure Mode

`hypothesis`: The Python comparator may fail before performance measurement due to dependency drift, assumptions about TOPAZ file layout, or stale Python code paths. If that happens, the package should record the failure as a valid outcome and recommend a comparator-remediation package.
