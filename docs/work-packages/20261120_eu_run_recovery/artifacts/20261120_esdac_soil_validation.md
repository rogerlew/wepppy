# ESDAC soil implementation validation

## Candidate readback on forest

The candidate batch builder ran against the original Es Fangar 58 hillslope locations and the installed ESDAC and HydroGrids sources. The 58 base soil files referenced by the assignments parsed successfully. The quality report recorded 37 hillslopes with the fixed project profile and 21 native profiles. Comparing the 21 native profiles against a separate control batch gave identical stable content and matched generated keys. The control processed the same locations through the same runtime without fallback. Thirty-five soils passed configured 7778 Disturbed serialization and format-aware readback. The existing land-use lookup left 23 using their base files. The output and test scripts are retained on forest under `/var/tmp/wepppy-eu-run-recovery-baseline/`.

The actual Soils Summary template rendered “Subsoil defaults applied,” “37 of 58,” and the quality report link above the coverage table. Rendering without accepted fallback metadata omitted the warning. The controller test covers the accepted warning surviving a rejected request and disables form fields outside gridded mode.

## Gates and limits

- All 168 focused Python tests passed. They cover ESDAC, the Disturbed runtime gate, soil API, RQ concurrency, and submission recovery. The isolated receipt is `.wctl-test-runs/b1a99ac5a9e144ee9ea9a32ce3115d22/receipt.json`.
- Frontend lint and 1,099 Jest tests plus nine Node tests passed. The controller bundle rebuilt from the candidate.
- The dependency graph and test-stub inventory checks passed.
- The final broad test preflight passed with verified compatible donor binaries and browser dependencies. The run stopped at `test_culverts_runner_creates_runs_and_get_wd[initialized]` after 349 passed and 28 skipped. The same lock conflict, including the same lock owner, reproduced on the unchanged base revision `c2e6f4d1a`. The broad candidate receipt is `.wctl-test-runs/e558d3fd07e34afc81b401d177ba08aa/receipt.json`. A complete broad pass remains open.
- Stubtest stopped before runtime compatibility checks on existing mypy errors in unchanged `wepppy/eu/soils/esdac/quality.py`.

Independent correctness review found and dispositioned queued mode drift, accepted summary timing, persistence failure before job ID replacement, malformed 7778 metadata, and repeated MOFE keys. This is local implementation and artifact evidence. A full forest deployment, browser reload under deployed orchestration, and both incident replays remain part of the parent package.
