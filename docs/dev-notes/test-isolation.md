# Test isolation checker

Run `wctl check-test-isolation` for five repeated suite runs and per-file tests.
Without a randomization plugin, the repeats retain collection order and do not
establish shuffled-order coverage. `--json` retains structured failure details;
`--log-dir` retains each pytest stdout/stderr stream.

## State boundary

Snapshots bracket collection and execution: after pytest/plugins/root conftest
initialization (`pytest_sessionstart`) and after fixture teardown, before
pytest shutdown (`pytest_sessionfinish`). Collection-time test stubs and leaked
environment values remain detectable. Inspect module dictionaries directly;
observation must not invoke lazy `__getattr__` imports.

Ordinary file-backed imports are expected. Added fileless modules are suspicious,
and replacement of an existing module remains a finding. CFFI library objects (the native `_cffi_backend.Lib` type, such as `_openssl.lib`)
are not Python module stubs. OpenSSL's enclosing `_openssl` module is recognized
by its native FFI/Lib pair. Cryptography deprecation and Passlib compatibility proxies expose metadata from
their underlying real module without invoking attribute forwarding. Cython's
`Cython.Shadow` objects (`CythonDotParallel`, `CythonCImports`, and
`CythonDotImportedFromElsewhere`) and Passlib's `_PasslibRegistryProxy` are also
expected imports, identified by their concrete class module/name. Known native import
helpers are exceptions only when their observed shape matches: `cython_runtime`,
versioned `_cython_N_N_N` modules (including `limited`/`nofinalize` ABI suffixes)
with a Cython function type, SWIG's
`swig_runtime_data4` with its capsule, and DuckDB's `typing`/`functional` helper
modules with their exported types. These names/shapes are a bounded heuristic,
not provenance authentication. Replacements remain findings even for these names.

The following absent-to-default environment additions are accepted only together
with a newly imported real dependency: Pint's `PINT_ARRAY_PROTOCOL_FALLBACK=0`,
Threadpoolctl/Scikit-learn's `KMP_DUPLICATE_LIB_OK=True`,
and Rasterio/Pyogrio/Fiona's `GDAL_CURL_CA_BUNDLE`/`PROJ_CURL_CA_BUNDLE` pointing to the loaded
Certifi package's `cacert.pem`. Other values, additions without that import,
and all changed/removed existing values remain findings. Do not add broad
namespace or environment suppressions to make tests pass.

## Failure semantics

Nonzero pytest results cannot become clean merely because repeat outcomes agree.
Worker/collection/internal errors return 2; test or pollution findings return 1.
Baseline suppressions apply to pollution/order findings, not failed executions.
The explicit `--allow-failures` report-only option still returns zero, but findings
remain visible. Missing requested snapshots are tool errors. No tests or inability
to collect files is not successful isolation evidence.

For diagnosis, a bounded `--iterations 1` or `--pytest-args=--collect-only` run
can isolate setup problems. Neither replaces the default full acceptance gate.
