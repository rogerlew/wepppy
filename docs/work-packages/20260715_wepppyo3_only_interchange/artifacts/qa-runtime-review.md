# QA and Runtime Review

**Reviewer**: independent QA/runtime agent
**Final result**: zero unresolved high or medium findings

## Findings and Disposition

1. **Medium - only the web process initially ran the native release preflight.**
   Resolved in WEPPpy `4f144a986` with one shared preflight for query-engine,
   rq-engine, both RQ worker services, and scheduler. The web service retains
   its bundle-building entrypoint and invokes the same preflight afterwards.
2. **Medium - native-only tests no longer exercised exact schema snapshots.**
   Resolved in `4f144a986` with 22 tracked schema snapshots, including WAT
   `InterceptionStorage` and TC_OUT. Static schema and field metadata remain
   exact; only four run-dependent metadata keys are normalized.
3. **Medium - documented Cargo and release-Python test commands were invalid.**
   Corrected to the actual `wepp_interchange_rust` crate and release-tree
   `PYTHONPATH` invocation.
4. **High during re-review - the production image copied WEPPpyo3 into
   site-packages ahead of the canonical vendored release.** Resolved in WEPPpy
   `9c4f471f7` by removing the duplicate copy. Production now imports the one
   vendored release through `/workdir/wepppyo3`; static image-contract and
   symlinked-root preflight regressions pass.

## Final Runtime Evidence

- Web, query-engine, rq-engine, rq-worker, rq-worker-batch, and scheduler all
  logged extension SHA-256
  `7419203c8b91db1b595590b7c9a28040662d5fad9fdf8b182a17c85a76d518e4`.
- No Python-parser fallback telemetry appeared.
- RQ reported zero queued/executing jobs and ten idle workers.
- Focused WEPPpy suite: 55 passed and one fixture-dependent PASS test skipped.
- Post-production-fix startup contract: 9 passed.
- WEPPpyo3: 68 unit and 16 integration tests passed.
- Release-tree Python suite: 22 passed.

The production image was not rebuilt during this local review. The corrected
canonical-import behavior is covered by the Dockerfile contract test and a
symlinked-root runtime regression; this is a non-blocking residual limitation.
