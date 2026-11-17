# Reproduce Roads refactor validation

These commands use the existing running development stack's installed `wctl`
preset and image, with isolated one-off test containers. They do not restart or
remount a shared service. Freeze candidate source during each run and record its
commit plus dirty-source hashes before claiming a candidate result.

## Retained scripts and receipts

The five scripts under `scripts/` are byte-for-byte snapshots of the working
validation helpers. `validation_scripts_receipt.json` records their original
runtime paths, sizes and SHA-256 values. This receipt was captured after baseline
execution; it does not claim hashes were captured before those earlier launches.
It explicitly lists the subsequent safety/parameterization edits to the reusable
host drivers and comparator. Baseline logs retain exact executed command lines.

`baseline_source_receipt.json`, `baseline_project_receipt.json` and
`baseline_comparator_self_check.json` retain compact baseline evidence. Full
native/profile output and exact project declarations remain at the paths recorded
in `baseline_validation.md`; do not overwrite these directories.

The helpers intentionally retain the observed environment paths:
`/home/workdir/wepppy-roads-code-quality`,
`/home/workdir/wepppy-roads-baseline`, `/tmp/roads-refactor-validation`, and
`/wc1/runs/rq`. The host drivers import the repository's existing
`checked_test_command` guard, which requires the source bind to be visible at
container `/workdir/wepppy` before running tests. For another host, prepare an
explicit reviewed path adaptation and new script receipt rather than describing
these exact bytes as portable without changes.

Restore missing working copies from the retained snapshots before execution:

    mkdir -p /tmp/roads-refactor-validation
    cp artifacts/scripts/roads_refactor_baseline.py /tmp/roads_refactor_baseline.py
    cp artifacts/scripts/roads_refactor_projects.py /tmp/roads_refactor_projects.py
    cp artifacts/scripts/project_parity.py /tmp/roads-refactor-validation/project_parity.py
    cp artifacts/scripts/compare_matrix.py /tmp/roads-refactor-validation/compare_matrix.py
    cp artifacts/scripts/response_diagnostic.py /tmp/roads-refactor-validation/response_diagnostic.py

Run those copy commands from this work-package directory. Review existing working
copies before replacing them; a later validation may have its own receipt.

## Candidate checks

Choose a new label for each native attempt; `candidate-final` below is an example,
not permission to reuse an existing destination. Native execution refuses an
existing basetemp; project execution also refuses occupied evidence destinations.
Host logs are separately labeled. Inspect those paths before running any command.

    ROADS_TEST_CHECKOUT=/home/workdir/wepppy-roads-code-quality \
      ROADS_OUTPUT_LABEL=candidate-final \
      python3 /tmp/roads_refactor_baseline.py focused-aligned

    ROADS_TEST_CHECKOUT=/home/workdir/wepppy-roads-code-quality \
      ROADS_OUTPUT_LABEL=candidate-final \
      python3 /tmp/roads_refactor_baseline.py native

    ROADS_TEST_CHECKOUT=/home/workdir/wepppy-roads-code-quality \
      ROADS_OUTPUT_LABEL=candidate-final \
      python3 /tmp/roads_refactor_baseline.py analysis

The focused command aligns the vector-retention filesystem setting with pytest's
`/tmp` fixtures. It does not alter application configuration. Expected completion
is no new focused failure, all 516 matrix profiles complete, and 516 native
summaries validated. Evaluate all failures explicitly; the host helper is not a
replacement for the required final broad suite.

Compare native inputs, outputs and case semantics after the candidate matrix:

    python3 /tmp/roads-refactor-validation/compare_matrix.py \
      /tmp/roads-refactor-validation/native-baseline/roads_matrix0 \
      /tmp/roads-refactor-validation/native-candidate-final/roads_matrix0 \
      --output /tmp/roads-refactor-validation/matrix-candidate-final-comparison.json

The comparator requires all 516 unique cases and matching native binary/extension
identities; validates each side's recorded input/output hashes; and compares all
6,192 native files. Its only byte normalization replaces the exact scratch-root
path. Case elapsed seconds are excluded. Scientific metadata and other bytes
must match exactly. A self-comparison is harness evidence, not candidate parity.
Do not broaden normalization to conceal a discrepancy.

Run the five project controls with a fresh label:

    ROADS_TEST_CHECKOUT=/home/workdir/wepppy-roads-code-quality \
      ROADS_PARITY_LABEL=candidate-final \
      python3 /tmp/roads_refactor_projects.py

The project driver runs at most two one-off containers concurrently. Additive
controls use the original `clogging-starch` project and `wepp_260409`; unrutted
controls use `misty-eyed-divorcee` and `wepp_260803`. Preserve this distinction in
candidate comparisons. Each project records declared upload changes before
preparation, checks unmodified original/copied baseline artifacts, reads native
results, and retains an artifact/executable hash manifest. The positive unrutted
control includes daily water/area reconciliation and current-result admission.
The negative control requires an explicit road-plus-fill fit failure and rejects
current-result admission. Inspect the exact five failures against baseline; the
standalone helper's minimum negative assertion is not itself complete parity.

## Claims and remaining work

These snapshots make baseline controls reproducible. They do not claim that final
candidate checks, independent reviews or broad-suite validation have passed.
Record any later script modification in a new receipt and retain exact source,
image, executable, declared-input and comparison evidence with its result.


## Executed current-policy candidate recipe

The final candidate used the additional exact snapshots listed in
`candidate_validation_scripts_receipt.json`, with results in
`candidate_validation.md`. The candidate project driver calls the checked-in
`tests/roads/unrutted_project.py`; the earlier baseline driver above retains its
original baseline-only unrutted assertions and is not the current harness proof.

The executed candidate commands were:

    python3 /tmp/roads_candidate_projects.py
    ROADS_TEST_CHECKOUT=/home/workdir/wepppy-roads-code-quality \
      ROADS_OUTPUT_LABEL=candidate-20261117b \
      python3 /tmp/roads_candidate_native.py native
    ROADS_TEST_CHECKOUT=/home/workdir/wepppy-roads-code-quality \
      ROADS_OUTPUT_LABEL=candidate-20261117b \
      python3 /tmp/roads_candidate_native.py analysis
    python3 /tmp/roads_candidate_command.py project-comparison-final \
      /opt/venv/bin/python /tmp/roads-refactor-validation/compare_projects.py
    python3 /tmp/roads_candidate_command.py project-field-metadata \
      /opt/venv/bin/python /tmp/roads-refactor-validation/check_project_field_metadata.py
    python3 /tmp/roads-refactor-validation/compare_analysis.py

The project driver and comparison scripts retain the exact successful labels.
For a new attempt, copy the snapshots, select a fresh label in the driver and
comparators, and retain a new script receipt. Do not overwrite the successful
candidate roots or logs. Native comparison uses the unchanged `compare_matrix.py`
command above with `native-candidate-20261117b/roads_matrix0` and a fresh receipt
filename. The native driver and generic command driver additionally bind the
existing Git metadata read-only for repository-aware checks.

## Documentation commands in an isolated worktree

The installed preset defaults documentation commands to the shared project path.
Use `wctl --project-dir /home/workdir/wepppy-roads-code-quality doc-lint --path ...`
for candidate-relative paths. This selects the intended checkout and avoids the
zero-file result observed with relative paths under the default preset. Individual
absolute file paths also worked; final closeout uses the explicit project override.
