# Independent correctness review

Reviewed on 2026-11-22 at 23:22 UTC by the independent correctness reviewer. Scope includes native sink, bulk families, AgFields staged identity validation, baseline and Roads daily aggregation. The candidate and WEPPpy branches are both named `fix/interchange-row-groups`. The reviewed native release file has SHA-256 `1769c18b5fb0454026d3ea6dee7192f082a3eabf41f0b33d710af891458443fd`. The previous binary used for comparison has SHA-256 `7f67d3a8e56066d43b2fdb1ffc5360d357d61f2fcc963190c67fe288373702ad`.

## Failure class and operating states

Physical row groups had served simultaneously as parser batch boundaries, source identities and units for completeness checks. Arrow may divide a single batch. Packing can also put multiple identities into one group. Reviewed the sink's physical footer count, all six hillslope bulk call sites, the common AgFields writer, streaming writers, the Roads accounting writer, source identity validation, totalwatsed3's mixed-group index and every caller of its scan method.

| State | Expected behavior and evidence |
| --- | --- |
| Source absent or malformed | Existing parser and staged publication boundaries propagate failure. Sinks publish after successful close. AgFields requires the mapping and verifies its identities before publication. |
| Empty selection or zero-row source | Four-hill replay produced a valid empty daily file with 79 columns. AgFields accepts validated zero-row EBE sources through its existing explicit identity accounting. |
| Old homogeneous, mixed and split groups | Freshly generated artifacts and comparison results appear below. Public hillslope facades and daily producer were exercised with the candidate loaded from its paired release root. |
| Interleaved legacy IDs, unavailable statistics | Reordered four real families by year, simulation day and ID, used groups of 3,001 rows and disabled statistics. Full and two-ID subset results matched across 79 columns. The test crosses the sixteen-group reader window. |
| Invalid AgFields identities | Focused regressions use real Parquet tables with incorrect mapping, missing source, and reappearing source identities. Actual row ordering must be monotonic by subfield. |
| Concurrent readers and failed publication | Physical group changes use the existing per-file staging and rollback paths. Recovery requires the originating raw files and the corrected paired runtime. |

## Actual project and generated results

Read-only inspection on wepp1 found 47,582 inputs in each of PASS, EBE, ELEMENT, LOSS, SOIL, WAT and PLOT, plus one 61,898,339,040-byte watershed PASS. The interchange output directory was empty when inspected. Public RQ parent `8687cc43-a76e-4d74-bda1-d04f1de92070` and failed child `6b56bb1a-4066-4dd0-b952-594e6fcda338` identify the incident.

The sample uses source IDs 1, 2, 32,768, and 47,582 to cover the start, the failing group number and the last ID. Each of the six converted families and the canonical climate calendar was copied to isolated Forest storage. Server and local hashes matched for all 25 files. The calendar covers 16,436 days from 1981 through 2025. The persisted run settings supply groundwater storage 0, baseflow coefficient 0.04 and deep seepage coefficient 0. [Source manifest](incident-sample.sha256)

| Comparison | Direct readback |
| --- | --- |
| Candidate and prior ordinary source writers | Exact Arrow schema, field metadata, values, nulls and ordering for PASS 65,744 rows, WAT 65,744, SOIL 65,744, EBE 1,560, ELEMENT 5,775 and LOSS 20. |
| Candidate daily producer with mixed and split inputs | Repacked sources with groups of approximately half the rows minus one, forcing mixed and split boundaries. Against ordinary-layout previous release output, 16,436 daily rows for all hills, 16,436 for the two upper IDs and zero for empty selection. All 79 columns, schema metadata and null masks passed. The maximum absolute difference for the full set was 1.14e-13 in sbrunv. Two-ID and empty outputs were equal. |
| Candidate public WEPPpy facades | Six public family converters and run_totalwatsed3 read the sample with the canonical run calendar. Ordinary-layout full, selected and empty daily values matched the reference. |
| Candidate Roads producer | Used one modeled accounting source per real hill with 60% represented area. All four decoded geometries matched. The paired publication yielded 16,436 rows and 79 columns in daily output, and 65,744 rows and 32 columns in target accounting. Both files matched legacy layout element-for-element including metadata and nulls. This is constructed Roads coverage using real model outputs. |

The semantic comparison used absolute tolerance 1e-12 and relative tolerance 1e-11 for daily scientific values. Sample inputs, commands, fresh outputs and logs are retained locally at `/workdir/interchange-row-group-replay`. Replay entry points are `replay.py`, `facade.py`, `interleaved.py` and `roads.py`. The input manifest digest is `365e92dac8814cc6bdcd5f0058e0be2a7a31360d4b99197a07f2c5f0171bcf45`.

## Findings and verdict

The initial candidate used decoded mixed-group spans with a footer-supplied row count. The final binary validates their agreement before constructing Arrow's row selection. The reader avoids materializing adjoining source rows for contiguous packed input. An externally interleaved group may still require reading rows between the first and last match. Source packing and physical Arrow splits remain subject to the writer's finite file capacity.

The local correctness gate passes for the reviewed producer and consumer changes. The real watershed inventory and four-source replay establish original-input compatibility on a sample. The synthetic boundary run separately exercises the reported source count. Neither is a full 47,582-hillslope, 45-year production replay. Operational acceptance still requires the compatible runtime in the worker and direct readback of freshly regenerated interchange and dependent daily outputs.

## Replacement release addendum, 2026-11-23 00:26 UTC

The review above records the first candidate, SHA-256 `1769c18b5fb0454026d3ea6dee7192f082a3eabf41f0b33d710af891458443fd`. Subsequent broad tests found it also carried unreleased MOFE segmentation behavior. That invalidated its release sign-off. The words “final binary” above describe the bytes tested on November 22.

The replacement module SHA-256 is `9c16555afa70595c3a4031eb8bab94a1cdc6a7ea23637f40aff6120ab83520f9`, verified before and after replay. Its declared source commit `250243df5b40d72266247fa9308334b80bd93c26` is a direct child of released source `4d4c075421c4013cba99a0addc76482229e7f3f7`. Independent Git comparison found changes to the ten row-group production files and one totalwatsed3 regression file. Cargo manifests and lockfile match the released source. Both commits reference MOFE source blob `67e4ab4c748c3ecce990dee19da7316ff14c332c`. By comparison, the first candidate's base used blob `917907d1d96a1fe5d743adced0e2de7388394b56`.

The reviewer rechecked all 25 inputs against the retained source manifest and ran independent fresh conversions into `/workdir/interchange-row-group-replay/release-9c16555a`. The public WEPPpy facades loaded the replacement from the paired native checkout. The previous-release baseline remained the comparison oracle.

- All six fresh hillslope tables matched the baseline schema, metadata, values, nulls and ordering exactly, including 65,744 rows each for PASS, WAT and SOIL.
- Ordinary, mixed and split daily layouts passed on all four hills, two selected hills and the empty selection. The maximum absolute difference in the full mixed layout was 1.14e-13 in sbrunv. The selected and empty outputs matched exactly.
- Reordering the input by day and ID with disabled statistics and 3,001-row groups produced 16,436 rows and 79 columns for both full and selected cases. The maximum full-layout difference in sbrunv was 5.69e-14. The selected output matched exactly.
- The Roads modeled-area case matched exactly for all four geometries, the daily table with 16,436 rows and 79 columns and the accounting table with 65,744 rows and 32 columns.

The replacement passes this independent local correctness review. The sample covers four hillslopes and 45 years. Full-watershed production replay and original-child recovery remain separate operational gates.
