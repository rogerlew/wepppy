# Local validation record

The baseline was c82da0a9411b20a41b9d579fca1fc1b12133301f. Production source was frozen at 254ed7b78a743884e0d7ae95fed11a2fe77320cf. The final test fixture revision was dad9a99a1f246eea02a19980652016a344599837. The latter was tested in a clean detached worktree.

| Gate | Result |
| --- | --- |
| Focused HTTP and collaborator tests | 132 passed on baseline and final candidate. Final receipt 59def6f9be5b4eada5e53cbe55ba2dd5. |
| Full pytest | 14,869 passed, 533 skipped, 99 deselected. Final receipt b1cce06f96fc40e398db0d7608b8ce35. |
| Source and runtime integrity | Both final wctl receipts report passed. |
| Independent HTTP comparison | See [parity receipt](discovery_parity.json) for exact image, scenarios and probe instructions. |
| Quality | Zero worsened metrics. All 17 production modules below all three red thresholds. See [metrics](quality_metrics.json). |
| Static checks | Endpoint inventory, route contract checklist, broad exception enforcement, Vulture and stub hygiene passed. |

From the task checkout, the focused command was:

    WCTL_COMPOSE_FILE_EXTRAS=/tmp/wepppy-comrak-compose.R93hfiGw.yml wctl run-pytest --profile python -- tests/microservices/test_rq_engine_schema_defaults_routes.py tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py tests/microservices/test_rq_engine_errors_progress_outputs_routes.py tests/microservices/test_rq_engine_auth_concurrency_routes.py -q

The installed stock image lacked Comrak. Both comparison runs used the same local Comrak validation image. Full-suite invocation used the existing validated parser binaries with their adjacent provenance, the shared frontend runtime, and a Compose override mounting the matched climate extension read-only. The original image's extension rejected the raw_tdmean_c keyword on the historic dew-point test. The successful mount's SHA-256 was 813b8fe82de37d90860c768daac7dcf836f1ea03337820360006f760e3480e68.

    WCTL_COMPOSE_FILE_EXTRAS=/tmp/schema-defaults-prism-runtime.yml wctl run-pytest --runtime-root /home/workdir/wepppy --shape-parser /tmp/wepppy-comrak-parsers.0qeS3pwN/shape_parser_cli --geoparquet-parser /tmp/wepppy-comrak-parsers.0qeS3pwN/geoparquet_parser_cli -- tests --maxfail=1

Production deployment and remote integration were outside the execution scope.
