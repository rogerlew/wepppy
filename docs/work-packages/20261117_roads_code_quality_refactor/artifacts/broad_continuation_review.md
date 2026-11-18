# Qualified broad-suite continuation review

Date: 2026-11-17 UTC. Reviewer and external continuation-runner author:
`roads_final_qa`. Source freeze: `bfea39f736fd95d98391271e267d579471253ccc`.

## Disposition

**Accept the continuation method with the explicit qualification below. Runtime
completion is still pending.** The three attempted full-suite sanity commands
remain retained, including their failures. The proposed continuation reruns the
entire failed Geneva module and every following collected item, preserving order.
It does not skip a known failure or convert it to an expected failure. The earlier
completed prefix and the continuation can provide composite coverage of the
collection, once inventory and terminal outcomes reconcile.

This is not an uninterrupted all-green suite. The earlier prefix's node order is
reconstructed retrospectively: the original quiet run retained progress, counts
and the first failure, but no per-node report file. A fresh process reruns session
fixtures; cross-boundary session-state and ordering interactions are not tested
as one continuous run. Keep this limitation in final validation and handoff text.

## Prior run and boundary reconciliation

`/tmp/roads-refactor-validation/broad-final-v3.log` reports 3,341 passed,
155 skipped and one failure in 1,768.48 seconds, plus three passed subtests.
Independent parsing of quiet progress finds 3,341 pass markers, **154 runtime
skip markers**, and the failure. The remaining skip is collection-time; it is
not an executed item. Therefore the first failure must occupy zero-based item
index **3,495**, not 3,496. A summary-count-only selection would be incorrect.

The failed node is
`tests/nodb/mods/geneva/test_geneva_cache_freshness.py::test_canonical_archive_preserves_geneva_failed_and_accepted_work`.
The immutable-baseline reproduction retains the same inherited vector-retention
configuration/`RecordingRedis.eval` failure. The module is rerun from its first
item, including cases that already passed before the failure. Final aggregate
counts must exclude this overlap rather than adding the two raw pass totals.

## Bounded fixture corrections

Reviewed diffs clear only `VECTOR_UPLOAD_RUN_FILESYSTEM_ID` and
`VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT` within three individual archive-provenance
tests, adding the ordinary `monkeypatch` fixture argument where absent. Archive,
restore, data and provenance assertions are unchanged. No production source,
Redis stub, suite-wide environment or skip/expected-failure policy changed.

| Test module | Reviewed SHA-256 |
| --- | --- |
| `tests/nodb/mods/geneva/test_geneva_cache_freshness.py` | `58dafcbb9f0aad1849683e8e974554d4364d6ca60c6531440a4d3ee143eb6593` |
| `tests/nodb/test_cli_parquet_lineage.py` | `4132bd669065517144bd5a1886e27c5bd113fa668546c81744672fb7991a6510` |
| `tests/wepp/reports/test_report_cache_freshness.py` | `20be12834dc9af40e258ff1f450d58d7452739cc34ed5771edead119679686d8` |

The Geneva module passed 12 tests; the other two complete modules passed 76.
Their baseline reproductions and consumer assessment are retained in
[archive_fixture_failure_class.md](archive_fixture_failure_class.md) and
`archive_fixture_receipt.json`. Four separate Redis-snapshot archive tests remain
environment-skipped; they were not speculatively repaired or counted as executed.
These three fixes are acceptable with no medium/high finding and all three
modules must appear in the selected continuation, not the retained prefix.

## Runner and source qualification

The external runner is
`/tmp/roads-refactor-validation/run_broad_continuation.py`, SHA-256
`601bbb978e8994385292023196a366380457b353ce1bac010b95802aa952d4ac`.
It is launched only through the existing guarded candidate `wctl` helper, with
the same runtime and environment and a fresh basetemp. Local prelaunch checks
validated syntax, prior progress and the source-delta inventory. No continuation
runtime result is claimed by those checks.

The runner collects the full suite before selecting its suffix. It rejects
duplicate node IDs, collection errors, a mismatched collection-skip count, a
changed first-failure index, or an unexpected source delta. It records full,
deselected and selected ordered IDs, collection skips, each test-file hash,
interpreter/plugin identity, original log hash and its own source hash.
The start is the first Geneva-module item; no selected item is reordered.

The source snapshot covers tracked/unignored Python and stub files, applicable
configuration and dependency files under production, tests and tooling, plus root
configuration. The prelaunch host snapshot contains 2,836 fingerprints, including
two explicitly represented symlinks. Start/end snapshots detect changes during
execution. The source delta from the prior broad revision `43cb4e78f` is limited
to the three reviewed tests, the accepted staleness ledger and the independently
verified two-newline constants cleanup. The runner checks the exact accepted
ledger hash and constants bytes/AST. Its source remains frozen during execution.

All setup/call/teardown reports are retained, including failures, skips,
expected-failure flags and subtest context. Final summary retains pytest's exit
status, qualified exit status, source/script drift, missing teardowns and any
outcomes outside the selection. It cannot qualify a zero exit status with missing
items, source drift or failed/incomplete outcomes. Existing evidence paths are
never overwritten; a collection failure must be preserved before any new attempt.

## Required final reconciliation

Before accepting composite broad coverage, verify the ordered full inventory is
exactly the deselected prefix followed by the selected suffix. Derive prefix
outcomes from only the corresponding portion of the retained progress string;
exclude the rerun Geneva overlap and the original failed outcome. Confirm every
selected item has a completed terminal report, with no unresolved failure,
collection error, unexpected source drift or unexecuted tail. Report collection
skips, runtime skips, expected failures and subtests separately from passed items.
Retain the runner and inventory/report/source hashes with the final receipt.

Any further fixture correction requires its own baseline/changed-path assessment
and affected-module rerun. A production behavior change or changed prefix test
invalidates reuse of that evidence until its affected coverage is rerun. Preserve
all prior failed logs and describe the resulting evidence as qualified composite
coverage. The current native/project acceptance and unchanged scientific source
remain independent of this broad-suite qualification.

## Environment correction and second-run qualification

The first continuation stopped with 569 passed, three runtime skips, one
collection skip and an Omni clone failure; 11,047 selected items had not run.
Its start/end source fingerprints match. The retained reports correctly mark
this attempt failed, not complete coverage.

[Controlled environment evidence](validation_environment_scope.md) subsequently
shows the Omni test passes on both baseline and candidate under inherited
`dev-wc1`, `/wc1`, and fails on both with the driver's global `/tmp` override.
That override accidentally classified unrelated temporary fixtures as managed
retention storage. This is a validation-driver scope error, not a reason to edit
Omni production behavior or its test. Earlier archive-stub reproductions under
the override do not establish failures under canonical configuration.

The two-line Roads upload-fixture correction at `90dcd1039` is accepted:
`roads_client` explicitly supplies ID `roads-route-test` and its own `tmp_path`
root, using its existing ledger/lease doubles and scoped monkeypatch restoration.
Reviewed source SHA-256 is
`e496dc623eb197c6b15ed09e9b1f99ec50e1a86619309e0f07eb229068677fca`.
Canonical route validation passes 37 tests, one skipped; the full Roads focused
selection passes 413, one skipped. Scientific production source is unchanged.

A second external runner is prepared with distinct `v2` receipt names, a fresh
basetemp and no global root override. It retains and asserts canonical filesystem
ID/root values before and after execution and requires the same full ordered
15,104-item collection as the first attempt. It restarts at Geneva, repeating the
short failed continuation prefix. The original runner and receipts remain intact.
This second run is held pending the canonical environment-sensitive prefix audit
and a new source freeze; prepared code alone is not runtime qualification.

The audit selects 14 prefix modules, 537 nodes, by direct references to vector
upload/retention or archive/fork runtime. This is bounded impact coverage, not an
exhaustive dynamic dependency proof. The initial canonical audit exposed an Ag
Fields upload fixture's missing local configuration. Any additional prefix-fixture
repair requires baseline evidence, independent diff review, and complete canonical
module/node outcomes before its earlier result can be replaced.

Use the final successful canonical run of all 14 modules as replacement evidence
for those 537 prefix nodes. The intended final union is 2,947 retained prefix
nodes, 537 canonical prefix nodes and 11,620 canonical suffix nodes, with no
duplicates or missing items. Retain source hashes and phase outcomes for each
substitute. The remaining prefix used `/tmp` while the canonical runs use `/wc1`;
state this environment variance explicitly alongside the process-boundary
limitation. Even successful composite coverage is not a same-environment,
uninterrupted full-suite pass.

## Canonical prefix approval and v2 launch readiness

The final canonical prefix audit is accepted at source freeze
`5a6e45c463c6c3ce7720325d78c4060e0f96c1e4`: 508 passed and 29 skipped,
537 unique node IDs exactly matching the 14-module selection. All setup, call
and teardown reports reconcile, exit status is zero, and all 17 recorded source
fingerprints match before/after execution and the frozen checkout. The runtime
receipt `prefix-canonical-complete-after.json` has SHA-256
`6bbd6a44b9cb773a9ba75f9cf8fbc35c089427f9a0043c7faebf8228733638ec`;
the package retains the same execution evidence in
[canonical_prefix_execution.json](canonical_prefix_execution.json).

Independent review accepts the four fixture changes with no medium/high finding:
Ag Fields, Omni and batch-upload route fixtures now scope managed upload storage
to their own `tmp_path`, using their existing ledger and lease doubles. The
normalization module adds the equivalent small autouse fixture. Each supplies an
explicit test filesystem ID; monkeypatch restores the caller's environment.
Missing-configuration negative tests still remove or override these values in
the test body. Assertions, production behavior and test node identities are
unchanged. Baseline probes and the complete canonical rerun substantiate this
bounded fixture repair; the earlier global override is not retained.

| Reviewed test file under `tests/microservices/` | SHA-256 |
| --- | --- |
| `test_rq_engine_ag_fields_routes.py` | `75388b1208a51680aa3b397e88e2c1d32781a57378357e566933a3c1ff6bbc35` |
| `test_rq_engine_omni_routes.py` | `8efa9a65742b6164f43587531e126989b4d9fc997f03b3d699fcf23641032245` |
| `test_rq_engine_upload_batch_runner_routes.py` | `29ff5f895733b38e3d438f2701ae8ec904d68bea20ef03271be8775cae2bd301` |
| `test_vector_upload_normalization.py` | `30f49ed8dc496891eaef47d78fecd6c9559915c58ceb8b1cae7eb1165f7edba8` |

The frozen runner `/tmp/roads-refactor-validation/run_broad_continuation_v2.py`
has SHA-256
`ca4c2eada6dea587c522a1b86ac035473c6eabe95842bea09e1ee21d6d68887e`.
Its prelaunch reconciliation passes against that checkout. It checks the exact
canonical receipt digest, complete phase outcomes and current source hashes,
then substitutes all 537 canonical nodes for their prior results. Only the four
reviewed prefix fixture files are added to the changed-source allowlist. The
full ordered collection must equal the first continuation's 15,104-item inventory;
the Geneva start remains index 3,484 and prior failure index 3,495. Distinct `v2`
evidence names and basetemp preserve the first failed attempt. Canonical
`dev-wc1`, `/wc1` values are required and recorded before and after execution;
receipt, source or runner drift prevents qualification of a successful exit.

The remaining 2,947 retrospectively reconstructed v3 prefix items comprise
2,822 passes and 125 runtime skips. Adding the accepted canonical prefix and the
pending 11,620-item suffix yields an exact, nonoverlapping 15,104-item inventory.
Collection skips remain separate. This approves launch, not the pending suffix
outcomes. The mixed-environment and separate-process limitations above still
apply; the 14-module audit is not proof of every dynamic environment dependency.

## Observer interruption and v3 qualification

The v2 observer failed during the `grow` case in
`tests/nodb/test_derived_file_signature.py`. That test deliberately patches
`Path.open` with a read-only adapter. The observer incorrectly opened its output
file from the call-report hook while the patch was active, causing an internal
error before fixture teardown; pytest cache persistence subsequently encountered
the same patch. This is an external validation observer defect. No production or
test change is warranted. Ordinary pytest independently passes the complete
eight-item module without the observer.

The original v2 log and 7,567 persisted phase rows remain intact. Exact phase
reconciliation accepts only the 2,521 items before the derived-signature module:
2,518 passed, three skipped, with every expected setup/call/teardown outcome and
no failed or incomplete item. Full ordered collection indices are 3,484 through
6,004. Two completed tests and one setup report from the interrupted module are
excluded from reused evidence; the entire module must run again.

Since v2 could not reach its closing source snapshot, an independent fresh
guarded container verified all 2,836 source fingerprints against the v2 opening
snapshot. Both manifests have SHA-256
`6d243df4263ff191c414d41974b5e9aab2f7a8f12c3e2bdffef549ed915a9edf`.
The post-exit receipt has SHA-256
`7cd6b643197373bc6c43ae665a0ed53e117282e2eba76e734cd81c21e7db7f4b`.
This is a subsequent source-equivalence check, not a claim that the interrupted
process completed teardown or produced its own final receipt.

The v3 observer keeps report rows in memory while tests run. It writes them at
session end through captured original IO and JSON functions, avoiding filesystem
calls in test call-report hooks. It pins all nine v2 and post-exit evidence files,
requires current source fingerprints to equal the accepted manifest, checks the
same ordered full collection, and validates exact complete v2-prefix phase shapes.
The original v2 evidence, observer-smoke evidence and final v3 evidence use
distinct names; their basetemps are distinct as well. No source delta was needed.

Frozen `/tmp/roads-refactor-validation/run_broad_continuation_v3.py` SHA-256 is
`80f94084f65d170b94688687e748674062d0e2aeb9ce55fb72c14f525fdcc249`.
The same runner's `--observer-smoke` mode collected all 15,104 ordered items and
ran all eight derived-signature tests: eight passed, 24 complete phases, no
runtime skip or failure, with the existing one collection skip recorded
separately. Source, environment, observer and pinned evidence were unchanged;
pytest and qualified exit statuses were both zero. Smoke summary SHA-256 is
`1ef7dd64ff1232016014bcd6a9b60c52525ff2cc68074047991660816d4dcf1d`.
This exercises the previously failing observer/fixture interaction directly.

QA accepts v3 launch with no unresolved source or observer blocker. Its suffix
starts at full index 6,005 and contains 9,099 items. Final composite reconciliation
must combine 2,947 retained original-prefix items, 537 canonical-prefix items,
2,521 completed canonical-v2 items and 9,099 canonical-v3 items, totaling exactly
15,104 unique nodes. The reused 6,005 nodes comprise 5,848 passes and 157 runtime
skips. Final suffix outcomes remain pending. Previous environment and process
boundary limitations still apply, including the additional v2/v3 process boundary;
no uninterrupted full-suite pass is claimed.

## Shared queue isolation and v4 qualification

The v3 recorder completed normally with a failing test outcome in the first
`tests/rq/test_batch_deferred_recovery.py` case. The job was unexpectedly started
after the test enqueued it on the real shared `batch` queue. Read-only inspection
found four active workers consuming that queue in Redis DB 9. Baseline and
pre-fix candidate test bytes are identical; the unsafe shared-queue case was not
rerun, and no worker was stopped. This establishes the queue interference path
without claiming a separate baseline failure reproduction.

The reviewed fixture repair creates a real UUID-named queue on the same Redis
connection. Its factory asserts that production requested `batch` with that
connection, then supplies the private queue. Both tests and their registry
readback use it. The original association predicate also requires origin
`batch`, so a scoped adapter first requires the actual private origin, makes a
shallow Job copy, changes only that unsaved copy's origin and invokes the original
predicate. Function, argument and metadata checks remain active. Actual jobs keep
their private origin for real WATCH, dependency, registry, cancellation and cleanup
operations. No job is saved with a shared-queue origin. The fixture deletes its
private queue at teardown; existing assertions remain intact. This fixture does
not cover literal production queue-name selection.

The preliminary private-queue-only diagnostic failed the original predicate's
origin check and remains retained. Final scoped execution passes both tests
against real Redis in 9.79 seconds; the guarded stub check passes. QA accepts the
bounded final test-only change with no medium/high finding. The exact source
transition for `tests/rq/test_batch_deferred_recovery.py` is
`2ea4b9d244889061dad363cd37ff9169a5d5118de6d8c5e349b4b71499f80355`
to `823469a8b90c95607c1bd6a468dfceaf9cccdeb4dc7f2e0a535e97914aaad5cd`.

The reusable v3 segment contains 2,246 complete items at full indices 6,005
through 8,250: 2,170 passed and 76 runtime skipped. The console's additional skip
is the existing collection skip. Every accepted item has complete successful or
skipped phase reports. The failed module is excluded entirely. Source manifests
match before/after v3, environment values match, and recorder integrity flags are
clear. Original v3 evidence and its failed outcome remain unchanged.

The frozen external v4 runner has SHA-256
`eb388a759bb7df5c4bc2afd4b4f96da8a5a20bde8bd6e060dfa7a907d1175b65`.
Prelaunch reconciliation against all 2,836 current source entries passes. It
pins the complete v3 evidence set, verifies the retained ordered phase outcomes,
and permits only the exact reviewed queue-fixture transition against earlier
source manifests. That module occurs wholly in the selected suffix. The buffered
observer remains unchanged; new `v4` evidence names and basetemp preserve previous
attempts. Launch is accepted; suffix outcomes remain pending.

The final required union is 2,947 original-prefix items, 537 canonical-prefix
items, 2,521 completed v2 items, 2,246 completed v3 items and 6,853 v4 suffix items:
15,104 unique nodes with no overlap or gap. The reused 8,251 items comprise 8,018
passes and 233 runtime skips. v4 restarts the entire batch-deferred module at
index 8,251. Retained mixed-environment limitations still apply, and the additional
v3/v4 process boundary does not revalidate cross-boundary session state. This
remains qualified composite coverage, not an uninterrupted full-suite pass.

## Complete suffix diagnostic with v5

v4 stopped after three passes and 36 runtime skips at the ordinary workspace
deletion case in `tests/rq/test_batch_rq_delete_batch.py`; the additional console
skip is the existing collection skip. Its source and observer integrity checks
passed. No partial v4 outcome will enter the final composite union.

The worker reproduced the same outside-`/wc1` rejection on immutable baseline
using an isolated temporary workspace. The reviewed seven-line module fixture
clears the inherited filesystem ID/root for these ordinary workspaces, which have
no managed retention ledger. The module has no dedicated managed-retention cases.
Existing deletion, cache cleanup, notification and active-job assertions are
unchanged. The complete five-case module passes in 9.79 seconds. QA accepts this
test-only correction with no medium/high finding, at source commit `b653c2952`.
Exact source transition:
`2e29dc63da1d58edbdc1b8fec97926830671e405a354af8c3a390488c8ace531`
to `5c740a42d872ed534e47755b9ef62aa7c0cbcc62338682aa429efcde23ce545f`.

v5 starts at the same full index 8,251 and reruns all 6,853 suffix items with
`--maxfail=0`. This collects the remaining failure inventory in one frozen-source
execution; it does not turn failures into accepted outcomes. A failed pytest
exit, failed phase, missing item or integrity drift prevents acceptance. The
observer, ordered selection and completed-prefix evidence remain unchanged, with
new evidence names and basetemp. The two permitted suffix-file transitions are
the previously accepted private-queue fixture and this ordinary-storage fixture;
all 2,836 current source fingerprints pass prelaunch reconciliation.

Frozen `/tmp/roads-refactor-validation/run_broad_continuation_v5.py` SHA-256 is
`e1baeb2bfcd91c4eb698c8690e65471389e5b2ac6fde353b870264e24b476f2a`.
QA approves this comprehensive diagnostic and requires source to remain frozen
through its closing receipt. All earlier failed attempts remain preserved.

If further failures are confirmed as preexisting fixture defects, replacement
evidence must rerun each complete affected module, retain exact ordered node IDs
and all phase outcomes, and match final source fingerprints. Replacement must
remove all earlier results for those nodes before adding the rerun. Missing
baseline attribution, cross-module effects, cascades, production changes or
unresolved failures require wider validation or an explicit incomplete gate;
they cannot be silently substituted away. The required 15,104-node union and its
mixed-environment/process limitations remain unchanged, with v5 replacing the
entire v4 suffix. No diagnostic runtime result is claimed at launch approval.

## Final accounting

The [final broad disposition](broad_validation_final.md) supersedes the pending
runtime statements above. The complete diagnostic and a reviewed 391-node
whole-module replay account for all 15,104 unique nodes: 14,582 passed, 505 runtime
skipped, nine failed and eight setup errors, plus one separate collection skip.
Broad acceptance remains incomplete. Exact original evidence is compressed with
verified hashes; the management sidecar drift, mixed environments, retrospective
prefix and process boundaries remain explicit limitations.
