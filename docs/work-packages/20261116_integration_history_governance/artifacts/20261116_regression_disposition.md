# Full-suite regression disposition — preexisting RQ test-double mismatch

## Outcome

The required full-suite attempt did not pass. It stopped after **8,790 passed,
383 skipped, 1 failed, and 3 subtests passed**, in **3,161.79 seconds (52m41s)**.
The failure is reproducible from immutable pre-governance source and is unrelated
to the governance implementation. A focused module run identified one additional
failure with the same cause. No RQ application or fixture fix was made here.

Evidence was collected on 2026-11-16 UTC by the delegated correctness reviewer.
Pre-governance comparison commit:
`420e31b97e962dd6ea79694efe89f348c27ef83f`.

## Commands and observed results

| Check | Result | Local evidence |
| --- | --- | --- |
| `wctl run-pytest tests --maxfail=1 -q` | 1 failed, 8790 passed, 383 skipped, 3 subtests passed; 3161.79 seconds | `/tmp/governance-full-pytest.log` |
| `wctl run-pytest tests/rq/test_rq_worker_runid.py::test_handle_job_failure_preserves_rq_exception_string -q --maxfail=1` | Same failure; 9.36 seconds | `/tmp/governance-rq-focused-failure.log` |
| `wctl run-pytest tests/rq/test_rq_worker_runid.py -q` | 2 failed, 5 passed; 9.89 seconds | `/tmp/governance-rq-module-failure.log` |
| Baseline blobs loaded in a separate container Python process | Exact original failure reproduced; all three loaded files match current source byte for byte | `/tmp/governance-rq-baseline-reproduction.log` |

The two failing node IDs are:

```text
tests/rq/test_rq_worker_runid.py::test_handle_job_failure_preserves_rq_exception_string
tests/rq/test_rq_worker_runid.py::test_fork_failure_status_refresh_error_does_not_interrupt_failure_handling
```

## Cause and attribution

`WepppyRqWorker.handle_job_failure` calls `batch_outcome.observe_failure(job)`
after delegating to RQ's failure handler. In `observe_failure`, a job with no batch
root metadata becomes `root = job`, followed by `root.func_name` inspection at
`wepppy/rq/batch_outcome.py:680`.

The first test supplies `_DummyJob` without `func_name`; the second supplies a
`SimpleNamespace` without `func_name`. Both raise `AttributeError` before reaching
their intended assertion. The caught observer-error tuple in `rq_worker.py` does
not include `AttributeError`. The added observer path predates governance:
`f13e4ce6f7507c23099468314e55b77eeed51bd8` introduced the batch-outcome implementation.

These are concrete test-double/consumer contract failures. They do not by
themselves prove failure for a real RQ `Job`, which exposes `func_name`, or justify
adding a broad exception handler. Repair belongs to the batch-outcome/RQ test
contract: use a representative nonbatch job or deliberately isolate the unrelated
observer in focused worker tests, and retain direct observer coverage separately.
No such repair or test weakening is included in this governance package.

## Immutable baseline proof

The pre-governance and current Git blob IDs are identical:

| Path | Blob ID at baseline and current HEAD | Baseline SHA256, also equal to current working bytes |
| --- | --- | --- |
| `wepppy/rq/batch_outcome.py` | `3cf75befe0f3c2642d681f4cf2583ef1e968bd35` | `c9d3ad2369bccb8d5824c6d217936db7460274c37d42c2c9c861913f3481e688` |
| `wepppy/rq/rq_worker.py` | `f1c4d2615b47429ff904ae123361de0e562b0793` | `5dc6634d56781ba5d5a0088a6fff8a12293cf08ae729bafe3a31d50ff76d0e8b` |
| `tests/rq/test_rq_worker_runid.py` | `ee5e75f9b3d613f1f70792f9b86db29c804daacd` | `80b234b749dac997c20b295efc14152e85b6befec4c061c750ea134b36012188` |

The independent reproduction used `wctl exec -T weppcloud /opt/venv/bin/python -`.
Inside that process it extracted each named file with
`git show 420e31b97e962dd6ea79694efe89f348c27ef83f:PATH` into a temporary directory,
computed the hashes above, and loaded those files with
`importlib.util.spec_from_file_location`. It registered the two baseline RQ modules
under their actual module names in that isolated process and loaded the baseline
test file separately. Calling the original
`test_handle_job_failure_preserves_rq_exception_string` with
`pytest.MonkeyPatch.context()` produced:

```text
'_DummyJob' object has no attribute 'func_name'
```

This exercised the unchanged baseline test and failure path, not a rewritten
surrogate. Other dependencies came from the existing container environment;
this was not a rebuild or full-suite run of the entire historical checkout.
Temporary files were removed automatically. No shared source, index, branch,
container mount, or running application state was changed.

## Disposition and remaining validation

Classify both node IDs as **confirmed preexisting failures**, not governance
regressions and not passing tests. The integrator may continue the unexecuted
remainder with only these exact node IDs deselected, retaining the command,
results and exclusions. Such a run supplements the stopped full attempt; it must
not be reported as a green full-suite run. Broader exclusions, production fixes,
and claims of repository-wide correctness are not justified by this evidence.

The full attempt, focused enumeration, and isolated baseline reproduction are
complete. No overlapping RQ tests remained running when the integrator was
notified to start remainder validation.


## Continuation failures and attribution update

The continuation completed with **42 failed, 6,324 passed, 272 skipped, and
2 deselected** (`/tmp/governance-remainder-pytest.log`). Those counts describe
that separate invocation and overlap previously executed RQ tests; they must not
be added to the first run as a count of unique passing tests.

| Group | Failure count | Observed cause | Attribution and disposition |
| --- | --- | --- | --- |
| Specialized culvert admission | 2 | `_CulvertRunner` lacks `locked()` used by `culvert_routes.py:211`. | Confirmed preexisting: test/producer byte-identical to baseline and both exact nodes reproduce independently. No fixture/application fix included. |
| Deployment plan | 7 | Fake wctl rejects `show-compose-files` before plan construction. | Preexisting harness drift before governance execution; aligned fixture and companion print-plan repair validated by 77 passing deployment tests. See separate deployment review. |
| Feature registry runtime | 12 | Workflow-generator import changes shared PyYAML boolean resolvers; registry booleans become strings. | Governance tests newly expose a preexisting generator side effect; this is an in-scope governance regression, not an excused baseline failure. Resolved by isolated resolver dictionaries; coupled 559-test retest passes. |
| Pure controls render | 2 | Same registry boolean validation failure. | Same in-scope resolver regression; resolved in coupled retest. |
| Usersum routes | 16 | Registry or navigation YAML boolean validation fails. | Same in-scope resolver regression; all route tests pass after repair, with dirty generated index preserved. |
| Usersum contracts | 1 | `nav_tree.yaml` collapsible boolean parsed as string. | Same in-scope resolver regression; resolved in coupled retest. |
| Usersum index | 2 | Same navigation-contract failure before expected index assertions. | Same in-scope resolver regression; both index tests pass after repair and existing generated-index WIP is preserved. |

### YAML resolver failure class

New governance wiring tests import `scripts.build_forest_workflows`. Its
`WorkflowLoader` and `WorkflowDumper` inherited the resolver dictionary by
reference, then `_strip_bool_resolver` removed boolean resolvers from the shared
PyYAML classes. Other tests in the same process subsequently read valid YAML
`true`/`false` values as strings and rejected valid feature/navigation contracts.

A direct fresh-process probe loading the immutable generator from baseline
`420e31b97` demonstrates `yaml.safe_load('enabled: true')` changing from `bool`
to `str` after module execution. This establishes that the generator side effect
was preexisting, but the newly added governance test imports caused it to escape
into these downstream tests. The fix gives each workflow subclass a deep copy of
its inherited resolver dictionary before mutation. The same probe against the
fixed generator remains `bool` before and after. Generated workflow check passes
with unchanged serialized output. A new fresh-process regression asserts global
loader/dumper stability plus preserved workflow parsing and roundtrip semantics.
Coupled pytest results are recorded below.

### Specialized admission baseline identity

Both paths are unchanged from `420e31b97`:

| Path | Baseline/current Git blob | Baseline/current working SHA256 |
| --- | --- | --- |
| `tests/rq/test_specialized_admission_contract.py` | `1b66a333fa2de6f07231fcefd728a774c84428bc` | `bdc9b493c8b1baaf0731b7ee17515844eb1deed79449584d87026b71f7b85f0d` |
| `wepppy/microservices/rq_engine/culvert_routes.py` | `5612c3b3cf288d18dbb4d44b5c89efacdd2e92ec` | `6100c8e913ce18cadd718ead98546efb93dd3f10d50fde5f92da593430c20493` |

### Exact continuation failure inventory

```text
tests/rq/test_specialized_admission_contract.py::test_culvert_actual_producer_replaces_deferred_exactly[run_culvert_run_rq]
tests/rq/test_specialized_admission_contract.py::test_culvert_actual_producer_partial_failures[run_culvert_run_rq-enqueue]
tests/scripts/test_deploy_production_plan.py::test_full_plan_builds_each_local_image_and_validates_full_recreate_set
tests/scripts/test_deploy_production_plan.py::test_targeted_modes_have_narrow_recreate_and_acceptance_sets
tests/scripts/test_deploy_production_plan.py::test_plan_rejects_missing_consumer_configuration_before_build
tests/scripts/test_deploy_production_plan.py::test_targeted_cap_does_not_gate_unrelated_browse_configuration
tests/scripts/test_deploy_production_plan.py::test_targeted_batch_plan_has_only_batch_boundary[False]
tests/scripts/test_deploy_production_plan.py::test_targeted_batch_plan_has_only_batch_boundary[True]
tests/scripts/test_deploy_production_plan.py::test_targeted_batch_rejects_inactive_replica
tests/weppcloud/routes/test_feature_registry_runtime.py::test_config_registry_loads_expected_entries
tests/weppcloud/routes/test_feature_registry_runtime.py::test_config_registry_by_id_has_maturity_metadata
tests/weppcloud/routes/test_feature_registry_runtime.py::test_multi_ofe_configs_use_conservative_preview_ceiling
tests/weppcloud/routes/test_feature_registry_runtime.py::test_multi_ofe_override_preserves_non_release_states[stable-preview]
tests/weppcloud/routes/test_feature_registry_runtime.py::test_multi_ofe_override_preserves_non_release_states[preview-preview]
tests/weppcloud/routes/test_feature_registry_runtime.py::test_multi_ofe_override_preserves_non_release_states[experimental-experimental]
tests/weppcloud/routes/test_feature_registry_runtime.py::test_multi_ofe_override_preserves_non_release_states[internal-internal]
tests/weppcloud/routes/test_feature_registry_runtime.py::test_multi_ofe_override_preserves_non_release_states[deprecated-deprecated]
tests/weppcloud/routes/test_feature_registry_runtime.py::test_config_registry_declares_multi_ofe_preview_override_rule
tests/weppcloud/routes/test_feature_registry_runtime.py::test_registry_maps_are_immutable
tests/weppcloud/routes/test_feature_registry_runtime.py::test_schema_accepts_publication_embargo_with_embargo_until_config
tests/weppcloud/routes/test_feature_registry_runtime.py::test_schema_rejects_override_publication_embargo_without_embargo_until
tests/weppcloud/routes/test_pure_controls_render.py::test_interfaces_template_renders_registry_maturity_badges
tests/weppcloud/routes/test_pure_controls_render.py::test_interfaces_template_applies_visible_config_filter
tests/weppcloud/routes/test_usersum_bp.py::test_feature_catalog_public_complete_real_registries[roles0-False-]
tests/weppcloud/routes/test_usersum_bp.py::test_feature_catalog_public_complete_real_registries[roles1-False-?role=internal]
tests/weppcloud/routes/test_usersum_bp.py::test_feature_catalog_public_complete_real_registries[roles2-True-]
tests/weppcloud/routes/test_usersum_bp.py::test_feature_catalog_public_complete_real_registries[roles3-True-?role=user]
tests/weppcloud/routes/test_usersum_bp.py::test_feature_catalog_public_complete_real_registries[roles4-True-?role=internal]
tests/weppcloud/routes/test_usersum_bp.py::test_feature_catalog_links_use_site_prefix
tests/weppcloud/routes/test_usersum_bp.py::test_water_guides_are_user_visible_in_fresh_catalog[latqcc]
tests/weppcloud/routes/test_usersum_bp.py::test_water_guides_are_user_visible_in_fresh_catalog[QOFE]
tests/weppcloud/routes/test_usersum_bp.py::test_water_guides_are_user_visible_in_fresh_catalog[SUBEVENT]
tests/weppcloud/routes/test_usersum_bp.py::test_water_guides_are_user_visible_in_fresh_catalog[deep percolation]
tests/weppcloud/routes/test_usersum_bp.py::test_water_guides_are_user_visible_in_fresh_catalog[ET]
tests/weppcloud/routes/test_usersum_bp.py::test_water_guides_are_user_visible_in_fresh_catalog[H.wat]
tests/weppcloud/routes/test_usersum_bp.py::test_water_guides_are_user_visible_in_fresh_catalog[H.pass]
tests/weppcloud/routes/test_usersum_bp.py::test_automatic_deletion_help_is_discoverable_by_user_task[keep my project]
tests/weppcloud/routes/test_usersum_bp.py::test_automatic_deletion_help_is_discoverable_by_user_task[stop deletion]
tests/weppcloud/routes/test_usersum_bp.py::test_automatic_deletion_help_is_discoverable_by_user_task[how long are projects saved]
tests/weppcloud/routes/test_usersum_docs_contracts.py::test_usersum_contracts_validate_repo_contracts
tests/weppcloud/routes/test_usersum_docs_index.py::test_generated_usersum_index_contains_manifest_documents
tests/weppcloud/routes/test_usersum_docs_index.py::test_generated_usersum_index_includes_vendor_routes_and_breadcrumbs
```


## Repair validation and final disposition

The resolver repair was validated in one process with governance wiring tests
first, followed by every affected downstream module:

```bash
wctl run-pytest tests/tools/test_security_baseline.py \
  tests/tools/test_forest_workflow_bootstrap.py \
  tests/weppcloud/routes/test_feature_registry_runtime.py \
  tests/weppcloud/routes/test_pure_controls_render.py \
  tests/weppcloud/routes/test_usersum_bp.py \
  tests/weppcloud/routes/test_usersum_docs_contracts.py \
  tests/weppcloud/routes/test_usersum_docs_index.py -q --maxfail=3
```

Result: **559 passed**, four dependency deprecation warnings, **41.97 seconds**
(`/tmp/governance-yaml-coupled-tests.log`). This closes the 33 process-pollution
failures, including the generated Usersum index checks, without modifying the
preexisting generated-index WIP. `/usr/bin/python3
scripts/build_forest_workflows.py --check` also passed; workflow output was
unchanged by resolver isolation.

The two exact specialized-admission nodes listed in the inventory were then run
together through `wctl run-pytest`. Both independently reproduced
`AttributeError: '_CulvertRunner' object has no attribute 'locked'` in **12.00
seconds** (`/tmp/governance-culvert-focused-failure.log`). Together with immutable
baseline identity, this establishes two further preexisting fixture/producer
contract failures. No broad exception or weakened production behavior was added.

The CI/security lane repaired the seven deployment-plan fixture failures and
retained a separate [deployment regression review](20261116_deploy_plan_regression.md).
Its stronger read-only-plan test exposed an additional preexisting wepp3 path
that launched a secret-readability container during `--print-plan`; the repair
skips that probe only for plan output. Combined plan/execution validation reports
**77 passed**, followed by **2 passed** for the final gate-failure ordering
assertions. These seven original failures were not caused by the new governance
gate, but repairing their harness and read-only behavior was retained as part of
validating the affected deployment boundary.

Final classification of the observed failures:

- **33 governance-induced test-isolation failures:** repaired and all affected
  modules pass together with the governance importer.
- **7 deployment-plan failures:** repaired and validated in the separate lane.
- **4 confirmed preexisting RQ fixture-contract failures:** two worker `func_name`
  failures and two culvert-runner `locked()` failures remain explicitly unresolved.

The full attempt and continuation remain red historical results. Focused repair
runs establish the changed failure classes; they do not manufacture a green full
suite or waive the four unrelated failures. No more tests were running in this
review lane at handoff. A brief scheduling overlap occurred when the coupled
suite began after the 77-test deployment log completed while the other lane
started its final two fake-deployment assertions; those tests use mocked
executables and did not mutate real service state.
