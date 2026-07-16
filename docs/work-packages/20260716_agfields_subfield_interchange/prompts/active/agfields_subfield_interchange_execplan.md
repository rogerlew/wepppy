# Wire AgFields sub-field outputs into native interchange without changing ordinary writers

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current
as work proceeds.

Maintain this document in accordance with
`docs/prompt_templates/codex_exec_plans.md`. Also keep
`docs/work-packages/20260716_agfields_subfield_interchange/tracker.md` current at
every stopping point because this is an active work-package ExecPlan.

## Purpose / Big Picture

After this work, the existing AgFields "Run WEPP" job will not report success
until it has converted every sub-field's six supported text-report families into
native Parquet interchange files. Each generated row will identify the actual
agricultural `field_id` and `sub_field_id`. It will not pretend that the
sub-field has a TOPAZ hillslope id or use the parent hillslope's WEPP id as the
sub-field identity.

The result is visible under
`<run>/wepp/ag_fields/output/interchange/` as `H.pass.parquet`, `H.ebe.parquet`,
`H.element.parquet`, `H.loss.parquet`, `H.soil.parquet`, and `H.wat.parquet`.
On the forest acceptance project, each file must cover the same 6,626 distinct
sub-fields as `ag_fields/sub_fields/fields.parquet`. Ordinary baseline and roads
interchange outputs must remain exactly compatible.

## Progress

- [x] (2026-07-16 18:53 UTC) Traced the stage-4 RQ, NoDb, raw-output, native
  writer, release, schema snapshot, and downstream catalog paths.
- [x] (2026-07-16 18:53 UTC) Inspected the local acceptance corpus and recorded
  file counts, identity counts, allocated/apparent size, and free space.
- [x] (2026-07-16 18:53 UTC) Authored the pre-implementation schema compatibility
  plan and selected dedicated AgFields APIs as the regression boundary.
- [ ] Capture ordinary pre-change golden outputs and release/import provenance.
- [ ] Implement and validate one dedicated AgFields native writer as a contained
  prototype while proving its ordinary sibling is unchanged.
- [ ] Implement the remaining five dedicated native writers and their complete
  identity/error/schema test matrix.
- [ ] Build and verify the paired canonical native release without restarting
  services.
- [ ] Implement the staged WEPPpy AgFields orchestrator, Features Export catalog
  correction, and RQ ordering/error behavior.
- [ ] Pass targeted and full repository gates in both repositories.
- [ ] Benchmark and validate direct conversion of the full forest corpus.
- [ ] Restart the forest stack, verify native origin/SHA in every importer, and
  complete an actual authenticated stage-4 RQ acceptance.
- [ ] Complete independent code and QA reviews, resolve findings, update docs,
  and archive this ExecPlan with an outcome.

## Surprises & Discoveries

- Observation: The current stage-4 worker stamps completion immediately after
  `AgFields.run_wepp_ag_fields()` and has no interchange call.
  Evidence: `wepppy/rq/ag_fields_rq.py::run_ag_fields_wepp_rq` places
  `prep.timestamp(TaskEnum.run_ag_fields)` directly after the model call.

- Observation: AgFields uses the sub-field id in every raw `H<n>` filename, but
  all six ordinary native parsers name that token `wepp_id`.
  Evidence: `wepppy/nodb/mods/ag_fields/run_templates/sub_field.template` and
  the six `/home/workdir/wepppyo3/wepp_interchange/src/hill_*.rs` parsers.

- Observation: AgFields source rows contain parent `topaz_id` and parent
  `wepp_id`, but neither is the identity of the independently executed
  sub-field.
  Evidence: the acceptance `fields.parquet` schema and
  `wepppy/nodb/mods/ag_fields/ag_fields.py::run_wepp_ag_fields`.

- Observation: The current Features Export catalog prefers `wepp_id` for the
  planned AgFields metrics join even though `fields.parquet.wepp_id` is the
  parent WEPP hillslope and `H<n>` uses the sub-field id.
  Evidence:
  `wepppy/nodb/mods/features_export/layer_catalog.yaml` entry
  `ag_fields.metrics.subfields`.

- Observation: The supplied corpus is much larger logically than its allocated
  disk use suggests because reports are sparse. The six target families contain
  39,756 files and about 13.5 GiB apparent content; all seven raw families occupy
  about 3.7 GiB allocated on `/wc1`.
  Evidence: read-only `find`, `du`, and Parquet schema/count inspection on
  `/wc1/runs/sa/sacral-self-discipline`.

- Observation: The general `run_interchange_migration(runid, "ag_fields")`
  function discovers the right directory, but it invokes the ordinary hillslope
  schema and `totalwatsed3`, both of which assume ordinary WEPP identity. It is
  not safe to call unchanged.
  Evidence: `wepppy/rq/interchange_rq.py::run_interchange_migration`.

- Observation: Global interchange compatibility refresh checks only the major
  version. A minor version alone cannot prove that an AgFields bundle contains
  the required dataset kind and identity columns.
  Evidence: `wepppy/wepp/interchange/versioning.py::needs_major_refresh`.

Add discoveries with exact paths, commands, or concise test output. Do not erase
historical observations that changed the design.

## Decision Log

- Decision: Add six new AgFields PyO3 functions and do not change the six
  ordinary public writer signatures or schemas.
  Rationale: The native-only release is shared by baseline, roads, web,
  query-engine, RQ, scheduler, and worker processes. Separate APIs make ordinary
  compatibility testable as a hard invariant instead of a conditional branch in
  an existing public contract.
  Date/Author: 2026-07-16 / Codex and reconnaissance reviewers.

- Decision: Each native AgFields source descriptor is one coupled tuple
  `(path, field_id, sub_field_id)`, not parallel lists and not a position-only
  identity array.
  Rationale: Coupling prevents silent cross-row attribution when files are
  sorted or filtered. Both WEPPpy and Rust will validate that the filename's
  `H<n>` token equals the descriptor's `sub_field_id`.
  Date/Author: 2026-07-16 / Codex and reconnaissance reviewers.

- Decision: The new AgFields schemas contain `field_id`, `sub_field_id`, then
  the existing family measurement/date columns. They do not contain a fake
  `wepp_id` or `topaz_id`.
  Rationale: There is no existing AgFields interchange bundle to preserve, and
  starting with real identity avoids cementing the current filename-derived
  mislabeling. The Features Export join must be corrected in the same change.
  Date/Author: 2026-07-16 / Codex.

- Decision: Keep ordinary interchange version metadata stable and give the
  AgFields outputs their own dataset-kind/schema marker and manifest.
  Rationale: A global version bump would churn unrelated outputs but still would
  not be sufficient under the current major-only refresh check. Specialized
  readiness must validate the marker and required columns directly.
  Date/Author: 2026-07-16 / Codex and regression reviewer.

- Decision: Publish the six files as one staged bundle and write its completion
  manifest last.
  Rationale: Per-file atomic writers do not prevent a consumer from observing a
  mixed six-family generation after a later-family failure.
  Date/Author: 2026-07-16 / Codex and reconnaissance reviewers.

- Decision: Call interchange synchronously in the existing stage-4 RQ worker
  after model execution and before its timestamp/result/completion sequence.
  Rationale: This prevents false success without adding queue edges,
  cancellation semantics, UI child-job state, or dependency graph complexity.
  Date/Author: 2026-07-16 / Codex and reconnaissance reviewers.

## Outcomes & Retrospective

Planning is complete and implementation has not started. At each major
milestone, summarize what passed, what remains, measured performance, any
deviation from the compatibility contract, and lessons for shared native release
work. At closeout, compare the generated forest evidence against the purpose and
state the residual risk honestly.

## Context and Orientation

WEPPcloud uses RQ, a Redis-backed job queue, for long-running model stages. The
authenticated route in
`wepppy/microservices/rq_engine/ag_fields_routes.py` enqueues
`wepppy/rq/ag_fields_rq.py::run_ag_fields_wepp_rq`. That worker loads the
run-scoped `AgFields` NoDb controller, calls
`AgFields.run_wepp_ag_fields()`, stamps `TaskEnum.run_ag_fields`, publishes a
result, and publishes a completion trigger.

`AgFields.run_wepp_ag_fields()` reads
`<run>/ag_fields/sub_fields/fields.parquet`. Each row includes an agricultural
`field_id`, a unique `sub_field_id`, and parent watershed identifiers. It creates
and runs `p<sub_field_id>.run`; WEPP consequently writes
`H<sub_field_id>.*.dat` under `<run>/wepp/ag_fields/output/`. An individual
sub-field lies inside a parent TOPAZ hillslope, but it is not itself a TOPAZ
hillslope.

WEPPpy's ordinary aggregate facade is
`wepppy/wepp/interchange/hill_interchange.py::run_wepp_hillslope_interchange`.
It invokes six family facades, which call the required
`wepppyo3.wepp_interchange` bulk writers. The Rust source lives under
`/home/workdir/wepppyo3/wepp_interchange/src/`; the PyO3 registrations are in
`lib.rs`, the ordinary schemas are in `schema.rs`, and family parsers/writers are
in `hill_pass.rs`, `hill_ebe.rs`, `hill_element.rs`, `hill_loss.rs`,
`hill_soil.rs`, and `hill_wat.rs`. Each ordinary writer parses the numeric token
from its filename and emits it as `wepp_id`.

The deployable Python package is
`/home/workdir/wepppyo3/release/linux/py312/wepppyo3/`. WEPPpy has no production
Python parser fallback. Source code, release package, startup preflight, and
restarted processes therefore form one paired release. Do not restart services
with a mismatched Python API and shared object.

The designated acceptance run is
`/wc1/runs/sa/sacral-self-discipline`, corresponding to the browser project
`sacral-self-discipline/disturbed9002_wbt`. On 2026-07-16 its source mapping had
6,626 unique sub-fields across 2,169 fields. Each of the six target raw families
had exactly 6,626 files and there was no AgFields interchange directory. The
project also contains completed AgFields watershed scheme evidence, which is a
protected artifact and must remain unchanged.

## Plan of Work

### Milestone 1: Freeze ordinary goldens and prove one isolated native writer

Before editing Rust, capture small deterministic outputs from the canonical
pre-change release for all six ordinary families. Record the release shared
object's path, hash, public exports, schemas, metadata, row order, row-group
counts, writer summaries, and selected values. Use the existing WEPPpyo3 fixtures
where possible and extract only a small sanitized AgFields fixture from the
acceptance run: at least two sub-fields in one agricultural field and one
sub-field in a different field, with their six corresponding raw reports and a
minimal source mapping.

Prototype the dedicated API with PASS because PASS has both legacy ASCII and HBP
paths. Add a shared internal AgFields source descriptor/validation helper, an
AgFields PASS schema derived from the ordinary measurement fields, and a new
PyO3 entrypoint named
`ag_fields_hillslope_pass_files_to_parquet(sources, output_path,
version_major, version_minor, cli_calendar_path=None,
pass_family=None, compression="snappy")`. `sources` is a Python list of
three-tuples `(path, field_id, sub_field_id)` and maps to
`Vec<(String, i32, i32)>` at the PyO3 boundary.

The implementation must reuse the ordinary PASS parser and HBP decoder without
changing the ordinary public function. It may introduce internal generic
record-batch transformation, but ordinary tests and the captured golden must
remain exact. Rust validates positive/in-range ids, unique `sub_field_id`, and
filename equality. The AgFields schema replaces the ordinary first identity
column with `field_id` and `sub_field_id`; all later fields, types, metadata,
values, row order, and row-group behavior match PASS.

Milestone 1 passes when the new PASS API succeeds for legacy ASCII and HBP
fixtures, all invalid descriptor cases fail explicitly, late-source failure does
not publish a target, and the ordinary PASS API remains logically and, where
deterministic, byte-for-byte identical.

### Milestone 2: Extend the isolated native contract to all six families

Add the following sibling PyO3 functions with the same coupled source contract
and family-specific optional arguments as their ordinary counterparts:

- `ag_fields_hillslope_ebe_files_to_parquet`
- `ag_fields_hillslope_element_files_to_parquet`
- `ag_fields_hillslope_loss_files_to_parquet`
- `ag_fields_hillslope_soil_files_to_parquet`
- `ag_fields_hillslope_wat_files_to_parquet`

Keep the ordinary public registrations and release exports unchanged except for
adding the new names. Reuse shared identity validation and record-batch
transformation rather than forking scientific parsing. Give each new output
`dataset_kind=ag_fields_hillslope` and `ag_fields_schema_version=1` metadata.
Add exact AgFields schema tests, empty-output tests, row-group/source-order tests,
value parity with ordinary parsing after removing/replacing the identity column,
and descriptor rejection tests for every family.

Run the entire `wepp_interchange_rust` suite, not only the new tests. Then update
the release-tree `__init__.py` exports and Python tests against a locally built
artifact. Do not yet change WEPPpy's global required-symbol set or restart the
stack.

Milestone 2 passes when every old native test and golden is unchanged, all new
APIs pass their exact schemas and identity tests, and the release-tree import
exposes all six new names from the expected build.

### Milestone 3: Build a failure-atomic WEPPpy AgFields orchestrator

Create `wepppy/wepp/interchange/ag_fields_interchange.py` with a public function
whose final signature is:

    run_wepp_ag_fields_interchange(
        wepp_output_dir: Path | str,
        subfields_parquet_path: Path | str,
        *,
        start_year: int | None = None,
    ) -> Path

The module must not load a NoDb controller or infer parent TOPAZ/WEPP identity.
It reads only the explicit mapping path and raw output directory supplied by the
RQ-owned caller. Validate required source columns, integer range, nulls,
uniqueness, and exact set equality for all six file families. Sort descriptors
numerically by `sub_field_id` and couple each path with its exact ids.

Preflight the six dedicated native symbols through the existing required-native
boundary. Write all native targets to one unique sibling stage, validate each
schema's dataset kind, schema version, exact field list, non-null identity, and
distinct identity coverage, then write an AgFields bundle manifest last. Publish
the completed directory with a recoverable backup-and-replace sequence. On any
failure, restore the prior complete directory if publication started, remove or
retain the failed unique stage according to the diagnostic contract, and always
preserve raw reports.

Add `run_wepp_ag_fields_interchange` to the lazy public exports in
`wepppy/wepp/interchange/__init__.py`. Add the six dedicated native symbols to
the paired required-API preflight only after the canonical release artifact that
contains them is ready to install. Update the Features Export catalog so
AgFields PASS and WAT sources expose and join `sub_field_id`/`field_id`, not the
ambiguous ordinary identity assumptions.

Do not call the general `run_interchange_migration(..., "ag_fields")` unchanged:
its ordinary facade and `totalwatsed3` call have watershed identity assumptions
outside this package's output contract.

Milestone 3 passes with focused tests for positive publication, missing/extra or
cross-family ids, malformed mappings, every injected family failure, previous
bundle preservation, rerun replacement, stale dataset-kind rejection, and no
mutation outside the final/staging paths.

### Milestone 4: Wire stage 4 and preserve its terminal contract

In `wepppy/rq/ag_fields_rq.py::run_ag_fields_wepp_rq`, call the specialized
orchestrator immediately after `ag_fields.run_wepp_ag_fields()` returns and
before `prep.timestamp(TaskEnum.run_ag_fields)`. Pass
`ag_fields.ag_field_wepp_output_dir`, `ag_fields.subfields_parquet_path`, and the
calendar start year from the run's climate controller. Preserve `run_count` in
the result and add only useful relative interchange provenance. Publish an
explicit interchange phase/status message without adding a new RQ job.

Update `tests/rq/test_ag_fields_rq.py` to assert the exact success order:
preflight invalidation, WEPP, interchange, timestamp, result, completion. Inject
an interchange failure and assert the timestamp and success trigger are absent,
the error is published through the existing boundary, and the exception is
re-raised. Confirm the route payload, job id, UI job key, and queue topology are
unchanged.

Update the AgFields prerequisite/output description in
`wepppy/rq/job-dependencies-catalog.md`. Run `wctl check-rq-graph`; no graph diff
is expected because no enqueue site or edge changes. If the checker reports a
semantic edge change, stop and reconcile it rather than accepting unexpected
generated drift.

Update `wepppy/nodb/mods/ag_fields/README.md`,
`docs/dev-notes/wepp_interchange.spec.md`, the Features Export specification,
WEPPpyo3's `README.md` or module registry as appropriate, and
`/home/workdir/wepppyo3/docs/release-provenance.md`. Document the dataset kind,
the absence of sub-field TOPAZ/parent-WEPP identity, RQ success boundary,
publication contract, and paired deployment.

Milestone 4 passes when targeted RQ, orchestrator, catalog, schema snapshot, doc,
stub, and graph checks pass and the ordinary WEPPpy schema snapshot files remain
unchanged.

### Milestone 5: Validate the full corpus before enabling the RQ hook in services

Before restarting the stack, inventory protected files and free space in
`/wc1/runs/sa/sacral-self-discipline`. Preserve hashes for baseline
`wepp/output`, AgFields watershed scheme manifests/evidence, NoDb files,
`fields.parquet`, and existing raw sub-field outputs. Ensure no active AgFields
job owns the run.

Using the candidate canonical release through an explicit `PYTHONPATH`, run the
specialized orchestrator directly on the existing 6,626-sub-field corpus. Capture
wall time, peak resident memory, input/output allocated and apparent sizes, row
counts, row-group counts, and failure/retry behavior. Acceptance requires all
six files, exact schemas/metadata, 6,626 distinct `(field_id, sub_field_id)`
pairs in each family, a full two-way anti-join of zero rows against
`fields.parquet`, no null identities, no missing/extra source ids, a valid final
manifest, and no stage/backup debris. All protected files must remain
byte-identical.

Do not assume the candidate is operationally safe merely because it is Rust.
The recent native-only validation used a one-hillslope smoke, while this corpus
contains 39,756 target files and about 13.5 GiB apparent input. If peak memory,
runtime, NFS errors, or output layout are unacceptable, leave the RQ hook
undeployed, update this plan with evidence, and optimize within the owned native
path before continuing.

Milestone 5 passes only with recorded full-corpus evidence and successful rerun
publication that preserves the prior complete bundle until replacement.

### Milestone 6: Deploy the pair, restart forest, and prove the actual RQ path

Record the old and new native shared-object hashes. Install the candidate
`wepp_interchange_rust.so` into the canonical release using a same-directory
temporary file and atomic rename; do not overwrite the loaded artifact in place.
Update release provenance and confirm its mode. Run host import/signature smoke
against the canonical release.

Restart or force-recreate all local forest Python services that import the native
module, including web, query-engine, rq-engine, workers, batch workers, and
scheduler, using the repository's `wctl`/compose conventions. Verify each
service's startup preflight resolves the canonical release origin and the same
new SHA, and verify workers return idle before submission.

Submit the actual authenticated AgFields stage-4 route for
`sacral-self-discipline/disturbed9002_wbt`, poll the job tree/status surface, and
record job ids without credentials. Confirm the job does not stamp success until
the six-file bundle is published, all full-corpus identity/protected-file checks
still pass, and no queue child was added. Capture relevant logs, resource peaks,
terminal payload, and output paths in a package artifact.

If startup or RQ acceptance fails, atomically restore the prior native artifact
and paired WEPPpy code, restart all importers, and verify the prior SHA/origin.
Raw outputs must remain available so conversion can be retried without rerunning
WEPP after the fault is repaired.

Milestone 6 and the package pass only after targeted and full gates, generated
evidence, independent code review, and independent QA review have no unresolved
high or medium findings.

## Concrete Steps

At every milestone, first inspect both worktrees and preserve unrelated changes:

    cd /home/workdir/wepppy
    git status --short
    git -C /home/workdir/wepppyo3 status --short

Capture the pre-change native artifact and API before Rust edits:

    cd /home/workdir/wepppyo3
    sha256sum release/linux/py312/wepppyo3/wepp_interchange/wepp_interchange_rust.so
    PYTHONPATH=release/linux/py312 /usr/bin/python3.12 -c \
      "import inspect, wepppyo3.wepp_interchange as m; print(m.__file__); print(sorted(n for n in dir(m) if 'hillslope' in n and 'parquet' in n))"

Use the narrow native iteration loop:

    cd /home/workdir/wepppyo3
    cargo fmt --check -p wepp_interchange_rust
    cargo check -p wepp_interchange_rust
    cargo test -p wepp_interchange_rust
    PYTHONPATH=release/linux/py312 /home/workdir/wepppy/.venv/bin/pytest -q tests/wepp_interchange

Build the candidate with the canonical Python ABI only after source tests pass:

    cd /home/workdir/wepppyo3
    PYO3_PYTHON=/usr/bin/python3.12 \
      PYTHON_SYS_EXECUTABLE=/usr/bin/python3.12 \
      cargo build -p wepp_interchange_rust --release

Follow `/home/workdir/wepppyo3/README.md` for the exact candidate-to-release
copy. Stage the shared object in the release directory and rename atomically.
Then verify the new exports through the canonical release path.

Use the focused WEPPpy iteration loop:

    cd /home/workdir/wepppy
    wctl run-pytest tests/wepp/interchange --maxfail=1
    wctl run-pytest tests/rq/test_ag_fields_rq.py --maxfail=1
    wctl run-pytest tests/nodb/mods/test_ag_fields_backend_contract.py --maxfail=1
    wctl check-test-stubs
    wctl check-rq-graph
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

Use the following documentation checks for changed WEPPpy Markdown:

    cd /home/workdir/wepppy
    wctl doc-lint --path docs/work-packages/20260716_agfields_subfield_interchange
    wctl doc-lint --path docs/dev-notes/wepp_interchange.spec.md
    wctl doc-lint --path wepppy/nodb/mods/ag_fields/README.md

Preview American-English normalization before applying it:

    diff -u <changed-file> <(uk2us <changed-file>)

For WEPPpyo3 docs, follow its `AGENTS.md`: run `git diff --check`, preview
`uk2us`, and validate relative links with the documented helper.

Before handoff or deployment, run broad gates:

    cd /home/workdir/wepppyo3
    cargo test
    PYTHONPATH=release/linux/py312 /home/workdir/wepppy/.venv/bin/pytest -q tests

    cd /home/workdir/wepppy
    wctl run-pytest tests --maxfail=1
    git diff --check
    git -C /home/workdir/wepppyo3 diff --check

Before full-corpus use, record:

    df -h /wc1/runs/sa/sacral-self-discipline
    find /wc1/runs/sa/sacral-self-discipline/wepp/ag_fields/output \
      -maxdepth 1 -type f -name 'H*.dat' -printf '%f\n' \
      | sed -E 's/^H[0-9]+\.//' | sort | uniq -c

Run direct acceptance with `/usr/bin/time -v` around a small checked driver that
only calls `run_wepp_ag_fields_interchange` on the explicit run paths. Store the
driver and its concise results under this package's `artifacts/`; do not place
credentials or huge generated data in git.

Use the existing forest operational conventions and user-authorized restart for
deployment. Record exact `wctl` commands and service names in the tracker because
the local compose configuration may change. Use authenticated RQ submission and
polling patterns from `wepppy/microservices/rq_engine/AGENTS.md`; never record
tokens.

## Validation and Acceptance

Native acceptance has two independent dimensions. Ordinary acceptance proves
that all six existing public functions and schemas are unchanged through exact
snapshots, goldens, full crate tests, and release-tree Python tests. AgFields
acceptance proves the six new functions emit `field_id` and `sub_field_id`, omit
fake `wepp_id`/`topaz_id`, preserve all measurement values, and reject every
mapping mismatch explicitly.

WEPPpy acceptance proves the six-file bundle is failure-atomic, the Features
Export catalog joins on correct identity, ordinary snapshot fixtures do not
change, and RQ success occurs only after publication. `wctl check-rq-graph` must
remain clean with no new edge.

Generated acceptance is mandatory. On the supplied run, every family must have
6,626 distinct identities matching `fields.parquet` exactly; there must be no
null, missing, extra, duplicate, or mismatched identities. Record row and
row-group counts rather than assuming they are identical across families.
Protected baseline and watershed artifacts must remain byte-identical.

Operational acceptance requires bounded resource behavior at full scale,
canonical release origin and identical SHA across restarted importers, idle
workers before submission, an actual terminal-success RQ job, and a successful
retry/republication. Unit tests alone do not close the package.

## Idempotence and Recovery

Source discovery and validation are read-only. The orchestrator owns only a
unique stage, recoverable backup, and final
`wepp/ag_fields/output/interchange` directory. It never deletes raw reports.
Repeated conversion with identical inputs produces a complete replacement and
does not accumulate stage/backup debris.

Native per-file writers must use their existing failure-atomic target behavior.
The WEPPpy bundle layer must preserve a prior complete generation until all six
new targets and the manifest have passed validation. A failed stage must not
cause an RQ timestamp or completion trigger.

Release installation uses same-directory staging plus atomic rename. Preserve
the old shared object's hash and a recoverable copy until restarted services and
the actual RQ acceptance pass. Rollback is paired: restore both the prior native
artifact/API and WEPPpy caller, restart all importers, verify prior origin/SHA,
and leave the raw model outputs intact.

Do not use a Python parser fallback to restore availability. The repository's
native-only contract requires an explicit paired rollback or explicit failure.

## Artifacts and Notes

Keep concise, reviewable evidence under
`docs/work-packages/20260716_agfields_subfield_interchange/artifacts/`:

- pre-change ordinary writer schemas/golden summary and native SHA;
- schema compatibility plan;
- sanitized minimal fixture provenance, without copying large or sensitive run
  data unnecessarily;
- targeted and full validation transcripts;
- full-corpus benchmark and identity/protected-file summary;
- forest RQ acceptance with job ids, terminal payload, origins, and hashes;
- independent code-review and QA-review findings/dispositions.

Do not commit the full generated Parquet bundle, raw 13.5 GiB corpus, tokens, or
service secrets.

## Interfaces and Dependencies

No external dependency is added. Continue using Rust/PyO3, Arrow/Parquet support
already present in `wepp_interchange`, PyArrow/DuckDB already used by WEPPpy,
the existing required-native boundary, run-scoped paths, RQ status machinery,
and canonical release workflow.

At completion, the six new public native functions named in Milestones 1 and 2
must accept coupled source tuples and the same output/version/calendar/family
options as their ordinary siblings. The six existing functions must retain their
current public contracts.

At completion,
`wepppy.wepp.interchange.run_wepp_ag_fields_interchange` must have the explicit
path-based signature in Milestone 3 and return the published interchange
directory. `run_ag_fields_wepp_rq` remains the only RQ job for stage 4 and calls
the function synchronously before success.

The AgFields output schemas are a new dataset kind. They use `field_id` and
`sub_field_id` as required `int32` identity, followed by the ordinary family's
measurement/date fields. They contain neither a sub-field `topaz_id` nor a
parent `wepp_id` masquerading as row identity. The Features Export contract must
consume `sub_field_id` accordingly.

Revision note (2026-07-16): Initial plan created after parallel WEPPpy,
WEPPpyo3, and independent regression reconnaissance. Dedicated APIs were chosen
over optional changes to existing writers to minimize the ordinary interchange
blast radius.
