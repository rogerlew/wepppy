# Candidate Roads validation

Candidate source: task worktree `/home/workdir/wepppy-roads-code-quality`,
HEAD `5ef264810`; baseline `96555f2f95326350d2d7007c19327378ea831ab0`.
The source receipt records every Roads production/test Python file, including
uncommitted current-policy harness files. The project driver verified those
hashes were unchanged after all five controls. No production changes were made
by this validation worker. Commit `d6ecf9a2a` subsequently captured the exact
tested source bytes; the receipts preserve the original execution HEAD and
uncommitted-file hashes.

## Execution and controls

All five fresh project controls completed through the real controller and native
binaries using guarded, isolated `wctl run --rm --no-deps --pull never` containers
on the existing development stack. The nonce guard verified the candidate source
mount before imports. Shared services were not restarted or remounted.

Artifacts live under `/wc1/runs/rq/roads-quality-candidate-20261117b-<control>`;
immutable baseline roots use `baseline-20261117a` instead. Each root retains its
native executable/artifact manifest and declared geometry inputs. The three
additive controls used `clogging-starch` and `wepp_260409`; the two unrutted controls
used `misty-eyed-divorcee` and `wepp_260803`.

| Control | Native completed profiles | Outcome |
| --- | ---: | --- |
| inslope_bd | 35 | Completed; current artifacts admitted |
| inslope_rd | 35 | Completed; current artifacts admitted |
| outslope_rutted | 35 | Completed; current artifacts admitted |
| unrutted-positive, 5 m fill | 24 | Completed; current artifacts admitted |
| unrutted-negative, 30 m fill | 15 | Five exact fit rejections; current artifacts absent |

The unrutted runs executed the checked-in `tests/roads/unrutted_project.py` helper,
including source/copy-baseline isolation assertions, durable reload, input hash
checks, emitted OFE soil/management/slope readback, and positive daily water/area
reconciliation. All 55 upload features were retained. Supplemental positive
readback confirms 15 strips (six top-placed) plus nine remainders, with nonempty
source membership for every strip. The five failed identities and finite
road-plus-fill dimensions exactly match the pinned baseline negative control.

## Comparison rules

Project comparison checks native binary SHA-256 equality, artifact membership,
recorded artifact hashes, native bytes, exact JSON values, and parquet schemas,
metadata mappings, ordered rows and values. It verifies linked artifact digests
before substituting semantic references. It applies only these observed
nonscientific normalizations:

- Exact run-root strings and randomized parameterization scratch-directory names.
- Executable `binary_mtime_ns` diagnostic values; executable bytes and sizes match.
- `prepared_at`, comparison `completed_at`/`run_id`, durable summary
  `completed_at`/`failed_at`, and report-resource `generated_at`.
- Parquet metadata dictionary serialization order. Embedded `source_sha256` maps
  are checked against their own artifacts, whose schemas and ordered values must
  already compare equal.
- Accounting input/product hashes, allocation digests, and current-result snapshot
  hashes are verified against their own files or recomputed allocation before
  comparing the referenced semantic content.

Failed-attempt native files are archived by lifecycle cleanup. The comparator
selects exactly one negative archive whose 20 execution records exactly equal the
durable failed summary; it compares all its inputs and 15 completed outputs.
Copied older history is not evidence of the new attempt. Source and copied baseline
inventories were independently protected by each harness execution.

## Results and retained evidence

Candidate native tests: **527 passed** (516 profiles), two dependency deprecation
warnings, 373.32 seconds. `candidate_matrix_comparison.json` verifies all 6,192
native input/output files are byte-for-byte identical to baseline, even before
allowed root substitution. Binary and native-extension identities match.

`candidate_project_comparison.json` records **4,577 file comparisons**, with no
scientific or durable-summary differences. Counts by control are
1,128 / 1,128 / 1,127 / 714 / 480 in the table order above. A separate
`candidate_project_field_metadata.json` checks all 92 parquet field-metadata
schemas; row/schema/top-level metadata comparisons are in the main receipt.

`candidate_source_receipt.json`, `candidate_source_delta.json` and
`candidate_native_identity.json` retain source provenance and distinguish task
changes from the immutable baseline. `candidate_positive_placement_readback.json`
retains positive fixture coverage. `candidate_validation_scripts_receipt.json`
identifies exact driver/comparator snapshots under `scripts/`; successful runtime
logs are under `candidate_logs/`. Each project root retains its full executable
and artifact manifest. The reproducible commands are in `validation_recipe.md`.

Parsed native analysis validated all **516 complete profile summaries**. The
compact `candidate_analysis_comparison.json` verifies every analyzed case and
scientific summary value exactly equals baseline; only per-case elapsed time is
excluded. Native input/output/template hashes remain exact in that comparison.
Broad-suite validation and its baseline failure assessment are owned by the
integrator; this artifact does not claim the repository-wide suite passed.
