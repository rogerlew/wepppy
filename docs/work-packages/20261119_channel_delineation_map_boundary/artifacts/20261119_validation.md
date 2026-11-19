# Channel boundary validation

The validated candidate was `5db003b405514abdedb8e99881258c02b0ddbb6d`,
which includes runtime implementation `18c9d4e84` and the OpenAPI metadata
follow-up `5db003b40`. Contract checkpoint `77dbafa04` precedes both.
The default isolated test runner verified the candidate source and recorded
container UID 1000 and GID 993.

| Gate | Result and evidence |
| --- | --- |
| Focused Python, API metadata and RQ | 302 passed, 1 skipped. Source unchanged. Receipt `5290668afcfa4c0b98b0de5da251216b`. |
| Real Redis/RQ and WBT acceptance | 39 boundary tests passed in the dev image with a disposable Redis socket. Real upload, VRT source and content, RQ root and child, native channel cells, map GeoJSON and rejection readback passed. |
| Documentation and test hygiene | Changed Markdown lint passed. Stub completeness passed. Changed-file broad exception enforcement recorded zero new catches. |
| Full pytest on the final code | 6,706 passed, 230 skipped, 99 deselected and 1 failure. Source unchanged. Receipt `fa0a6730919a46b5b39b1e23f328a578`. |
| Baseline reproduction | The same SSURGO fixture failed on untouched `1d8e078333d7f340e3a7db19e3b32ff1d8c5cfac` with the same missing `Soils._config` error. Source unchanged. Receipt `760289607e8d42a2a1be89ff51549048`. |

The isolated full run uses the compatible browser dependencies and two
source-validated parser binaries. The first run found the dev image lacked
the Parquet CSV test prerequisite. The checkout's ignored test target was
populated from the local Parquet CSV package build with the identical Rust
tree `addc94f2ca2c00c85300112588f308acb8ee32e7`. All 12 previously blocked CSV
cases passed. A subsequent full run caught the OpenAPI byte budget on the
longer description. The focused and final full runs passed that gate after
the metadata was shortened.

The final full run stopped, as configured, at
`tests/nodb/test_soils_ssurgo_cache.py::test_project_ssurgo_cache_paths_are_derived_from_soils_dir`.
The test, soils controller and NoDb base are identical between candidate and
baseline. The local channel acceptance is complete. Repository-wide
acceptance awaits repair of the baseline fixture and a clean full rerun.
