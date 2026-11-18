# Shape-converter parser availability diagnostic

The baseline and candidate both fail
`test_inspect_rate_limit_returns_429_with_retry_after_header` during application
startup with `RuntimeError: parser_binary_or_provenance_missing`. Baseline result:
one failed in 10.75 seconds; candidate: one failed in 10.79 seconds. Neither probe
reaches its HTTP request or rate-limit assertions. Each used the canonical guarded
one-off container, a fresh pytest temporary directory and container-local scratch.

The selected `/usr/local/bin/shape_parser_cli` and its adjacent provenance sidecar
are absent in both test containers. Their source-tree build locations are also
absent in both worktrees. The inspected shape-converter Python modules and probe
test/helper have identical baseline and candidate hashes. The missing ignored
native build artifact explains this reproduced failure independently of Roads.

The primary checkout already contains a parser and sidecar. Its three recorded
Rust source files match the baseline and candidate exactly, including size and
SHA256. The sidecar records source revision `a5d9f0fc3`, release label
`recovery-validation`, and the locked Cargo build; exact source matching is
established from the recorded files, not inferred from that older revision.

| Artifact | SHA256 |
| --- | --- |
| shape_parser_cli | `4fb067f0953002194e5a8269459559ff27ad0acc681635640efb0ac68c2f7d01` |
| shape_parser_cli.json | `539e94369f87ab6ff61a3b63eefde9c2aaa6ffd085e3f9334419f40fc08adbae` |

The authorized qualification environment adds exactly two read-only file mounts
from that primary build directory to `/usr/local/bin/shape_parser_cli` and
`/usr/local/bin/shape_parser_cli.json`. These are the installed paths established
by `docker/Dockerfile.shape-converter` and selected by the existing Python code.
There are no environment overrides, source edits, builds, dependency installs or
shared-service changes. Native artifact hashes are identical before and after the
isolated runtime check. The real provenance validator, including binary hash and
`--version`, succeeds inside the candidate container.

This check establishes parser availability and identity only. Full affected
module qualification waits for completion of the original v5 diagnostic. The
original failure logs remain retained and cannot count as passing coverage.
GeoParquet parser availability was not repaired or qualified by these two mounts.

`shape_parser_environment_receipt.json` binds the probe logs, JUnit results,
source/availability receipts, and exact guarded helper under `scripts/`.
`shape-parser-existing-artifact-check.json` retains the complete sidecar and
per-file source comparisons. The future module replacement observer must record
the same native hashes before and after its run alongside its source manifest.
