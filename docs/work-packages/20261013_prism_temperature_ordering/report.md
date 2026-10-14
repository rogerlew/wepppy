# PRISM temperature-ordering implementation results

Implemented and validated in the development stack, 2026-10-14 UTC (2026-10-13 Pacific). All four writers apply ADR-0092's midpoint repair only to crossed adjusted extrema. No production deployment, existing-project rebuild, or EDDE WEPPcloud integration occurred.

## Delivery and identities

The reviewed contract ancestor is `7bd7707c2`. Native source is `d3e51c2badd2cb30a6bcb2e2f7a3881a8b3b908c`; release refresh is `0515272`. Only the climate extension changed. Its imported SHA-256 is `da1c323a7fa95f147b825a0fa38cfb006ef4f8319b489eb6f77ac7c4f49f7882`; [native provenance](artifacts/native-provenance.json) records the toolchain, command and rollback identity. Fresh Compose processes import the canonical release path. Resident processes were not restarted.

Rust daily, public Python PRISM, NoDb breakpoint, and EDDE revision now preserve ordered adjusted temperatures and collapse only crossed pairs to their midpoint. Source inversions/nonfinite operands and unrepresentable diagnostics fail explicitly. Existing serializers, offsets, precipitation, dates and auxiliary weather remain unchanged. The existing downstream Historic PRISM dewpoint floor uses the repaired Tmin. The public Python output-path annotation was corrected from `None` to `str | None`, reflecting existing accepted arguments without changing call behavior.

Each output has a visible `.temperature-ordering.log`, with working/completed status and correction count/magnitudes. EDDE also records additive monthly adjustment diagnostics in its existing companion. Diagnostic failure cannot publish a complete EDDE manifest. Missing legacy diagnostics mean unavailable, not zero. The [canonical contract](../../schemas/prism-spatialization-temperature-contract.md) owns these rules.

## Generated and consumed evidence

[Writer validation](artifacts/writer-validation.json) calls the actual installed native writer and EDDE adapter for 24 retained cases each. All 21 previously accepted EDDE DataFrames remain identical. The EDDE adapter reports 15 corrected pre-serialization pairs across the three previously rejected cases. Maximum repair is 0.25 C per extreme; largest written calendar-month extrema-mean change is 0.0096774 C. Those three cases each pass a fresh 20-year WEPP run through both writers: six executions with retained exact inputs and fresh finite output/date/precipitation checks.

Counts are precision-dependent: the native writer reports 10 pre-serialization corrections across five files, while six days were inverted in its old serialized output. EDDE reports 15 pre-serialization corrections. Existing arithmetic order differs (`(source-reference)+target` versus `source+(target-reference)`), so strict comparisons include tiny floating-point inversions, including two native files with corrections too small to change serialization. No tolerance was added. Valid serialized native days and non-temperature columns remain identical; cross-writer temperature differences stay within the preexisting 0.1 C serialization precision. The previously validated historical/future pairs remain unchanged; the missing Cascade historical replay still prevents a paired change-signal claim there.

[Project validation](artifacts/project-validation.json) copies project state/geometry into a scratch root, supplies the retained future CLI, and exercises existing ObservedPRISM Multiple orchestration with actual normal-tile acquisition and raster sampling. This is source substitution for validating the existing PRISM path, not new EDDE application integration. It generates 200 hillslope climates and visible diagnostic logs, reloads in a fresh process, and uses normal WEPP preparation. All 200 prepared climates match generated hashes and have ordered extrema. The project records 2,633 corrections across 195 hillslopes, with maximum per-extreme movement 0.617064 C: the 24-case study's smaller magnitude is not a universal bound.

The prepared `wepp/runs/p132.cli` matches `climate/_571.cli` exactly and passes a fresh 7,305-day WEPP execution. The canonical CLI parquet export has 7,305 rows and exactly matches the watershed CLI's weather columns; it describes watershed climate, not the individual revised hillslopes. Per-hillslope summaries select the revised CLI. Execution used configured Compose UID 1000, GID/groups 993, umask 0022 and the normal mounts. Original project NoDb hashes remain unchanged. Retained archives include exact consumed inputs, outputs, normal rasters, diagnostics and a 200-climate hash inventory; [evidence index](artifacts/evidence-index.json) lists member hashes.

Actual browse/download handlers and canonical ZIP archive/restore preserve completed and failed CLI/log bytes in two integration cases. Existing test fixtures mock authorization resolution; this proves handler/artifact behavior under the service identity, not a live authenticated browser session. The change introduces no authorization or serving boundary.

## Verification and limitations

| Gate | Result |
| --- | --- |
| Rust climate crate | 23 passed |
| Focused Python climate/NoDb/archive tests | 80 passed; all four writers, non-EDDE daily/breakpoint fixture, invalid sources, overflow and failure ordering |
| Retained actual-writer study | 24 native + 24 EDDE climates; six fresh WEPP runs passed |
| Actual project chain | 200 climates prepared identically; one further fresh WEPP run and canonical export readback passed |
| Test-stub hygiene | Passed |
| Broad pytest | 1,280 passed, 28 skipped; stopped at unchanged SBS upload-metadata assertion, as in the earlier EDDE study |
| Recursive climate stubtest | Existing `daily_client.d` under `__main__` is absent at runtime; 12 modules pass with a bounded recorded allowlist for that symbol only |
| NoDb helper stubtest | Blocked by existing module typing errors (logger, context-manager annotations and related legacy declarations); no runtime signature changes |
| Broad-exception gate | Default line-based allowlist reports a shifted existing catch; unsuppressed base/current comparison passes with zero added catches |
| Code-quality observability | Completed, observe-only; tooling produced no analyzable Python changed-file metrics |
| Independent correctness review | One medium and two low findings resolved; see review artifact |

[Paired native timings](artifacts/native-timing.json) use the same retained representative file, one warm-up pair and 30 alternating measurements per library. Median is 15.176 ms before and 15.307 ms after (about 0.9%); this is a warm local measurement, not a universal performance guarantee. The separate 24-case sweep had a 177 ms outlier under concurrent work; both sets of raw timings are retained.

Harness development failures are preserved in the validation logs. They included an incorrect reload API, missing explicit export invocation and use of a detached object without a logger. A same-process build/preparation attempt also observed stale in-memory climate selection despite correct persisted mappings; fresh-process preparation, matching the intended job boundary, passed. This observation is outside the numerical change and warrants a separate cache-lifecycle investigation before claiming same-process composition acceptance. No cache workaround was added to runtime code.

The original broad-suite failure and typing/allowlist limitations are recorded as failed gates, not green results. Focused executable acceptance and independent review support closing this bounded implementation package. Production rollout, live browser session acceptance and any existing-project repairs remain separately authorized work. EDDE application integration remains the successor package.

## Reproduction and rollback

Run `wctl run-pytest tests/climates/test_prism_temperature_ordering.py tests/climates/test_edde_client.py tests/climates/test_edde_cligen.py tests/nodb/test_prism_temperature_artifact_retention.py tests/nodb/test_climate_build_helpers.py` and `PYO3_PYTHON=/usr/bin/python3.12 cargo test -p cli_revision_rust` in the sibling native repository. The retained scripts document study, scratch-project, timing and archive checks; baseline study initialization requires the old library, and patched outputs require fresh destinations. Normal project consumption runs in a fresh process.

Rollback must pair Python writer changes with the previous native artifact and restore EDDE introduced-inversion rejection. The old native hash and source parent are retained in provenance/git history. Preserve attempted climates/logs; do not silently substitute a Python writer or mutate existing accepted projects. ADR-0092 remains the durable scientific decision; a rollback is operational regression handling, not evidence against that decision by itself.
