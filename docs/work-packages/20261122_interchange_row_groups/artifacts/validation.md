# Verification evidence

The final py312 native package commit is `b236ab0eed894e5664bdee5800c62f97f63ea81b` on `fix/interchange-row-groups` in wepp-in-the-woods/wepppyo3. Its extension was built from `250243df5b40d72266247fa9308334b80bd93c26` on `fix/interchange-row-groups-release-source` with rustc 1.92.0 and workspace lock SHA-256 `8135dc7071158b42d6382e5089b0510ef9017a0e6be4e3f9c7cbf1e963f26155`. WEPPpy pins the package commit in its publication workflow and verifies SHA-256 `9c16555afa70595c3a4031eb8bab94a1cdc6a7ea23637f40aff6120ab83520f9` at startup.

| Verification | Result |
| --- | --- |
| Public hillslope PASS on 47,582 distinct one-day source IDs | Previous release failed at group 32,768. Candidate wrote 47,582 rows in 15,861 groups. Reopened footer and full ordered identity column agreed with its summary. |
| Full-count daily reduction | Repeated the first PASS and WAT day from real hill 1 under 47,582 distinct source IDs. Each public native writer produced 15,861 groups. totalwatsed3 produced one 79-column row for all IDs and for selection 1, 32,768 and 47,582. Area and subsurface runoff volume scaled by selected count. Runoff depth and calendar key matched the single-input output. Areas were 2,482,765,951.760226 and 156,536.04 square meters. This local one-day process peaked at 859,064 KiB RSS. |
| AgFields | Repeated the retained five-row LOSS report under 47,582 sub-field IDs with five sub-fields per field. Reopened and validated 237,910 rows across 15,861 groups. |
| Native crate | 112 unit and 19 integration tests passed on the released-slope source. Includes unknown-length 32,768-chunk stream, multiple physical groups from one oversized chunk, zero rows and staged rollback. |
| Native release Python suite | 182 passed, including overstated and malformed footers, scientific oracles, AgFields, water balance and Roads. |
| WEPPpy interchange and startup | 154 passed, 1 skipped. Final receipt `a940e69abd554290b22dd45e88d29539`. |
| Real 45-year data and Roads | All six families, all 79 daily columns, subset, empty, interleaved and no-statistics layouts. See the independent correctness review for exact comparison tolerances. |
| QA follow-up | 34 tests passed with distinct values by hillslope across mixed and split groups. The AgFields regression accepts a packed six-file bundle and rejects a manifest with an incorrect physical group count. Receipt `dfab484ab1fc43a9b918e3b0f6d22be7`. |
| Repository-wide WEPPpy tests | Initial receipt `b29433c0fb704f8e8f7f49a39a584fc5` stopped after 8,077 passes at the Roads publication ledger. Its sole unreviewed source was the changed AgFields validator. Recorded the reviewed hash and linked evidence, preserving the original report, results, provenance and stale designation. The publication checks passed on continuation. The continuation then caught an unrelated MOFE endpoint change in the provisional binary. A fresh unfiltered repository-wide run is in progress with the replacement binary. |

## Reproduction

From the WEPPpy task checkout, select the py312 native release root using PYTHONPATH and run the boundary script with Python 3.12. Run the same command with the prior release to obtain the original failure. The script creates and removes its own scratch directory. [PASS boundary fixture](pass_boundary.py)

From the native task checkout run the following with the existing workspace lock and a Python-linked test target.

    PYO3_PYTHON=/usr/bin/python3.12 RUSTFLAGS='-C link-arg=-lpython3.12' cargo test --locked -p wepp_interchange_rust
    PYTHONPATH=release/linux/py312 /workdir/wepppy/.venv/bin/python -m pytest tests/wepp_interchange -q

On Forest the isolated wctl profile borrowed the compatible browser/parser assets and selected the existing comrak validation image with the candidate py312 release mounted read-only. The first focused invocation overlapped replacement of the candidate shared object and segfaulted in catalog scanning. It was discarded. The first successful focused suite used a fixed provisional release. The broad continuation showed that the provisional release had accidentally included candidate-only MOFE segmentation from native main. Its rounded endpoint yielded a gradient of 0.7 instead of the released 0.1. The replacement applies only the interchange repair to the last shipped crate. Fresh runs with that replacement verify both slope artifacts and interchange.

    WCTL_COMPOSE_FILE_EXTRAS=/tmp/rowgroups-runtime.yml wctl run-pytest --profile python -- tests/wepp/interchange tests/docker/unit/test_wepppyo3_interchange_startup_contract.py --maxfail=1 -q
    WCTL_COMPOSE_FILE_EXTRAS=/tmp/rowgroups-runtime.yml wctl run-pytest --runtime-root /home/workdir/wepppy --shape-parser /tmp/wepppy-comrak-parsers.0qeS3pwN/shape_parser_cli --geoparquet-parser /tmp/wepppy-comrak-parsers.0qeS3pwN/geoparquet_parser_cli -- tests --maxfail=1

Raw sample manifests and final-binary comparisons are in the [correctness review](20261122_correctness_review.md). The result supports local validation on original inputs and synthetic scale. Production repair requires the paired worker and a fresh full-run artifact.
