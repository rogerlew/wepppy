# Implementation correctness review

**Final correctness gate: pass.** Core and generated-input evidence passed;
the related native SBS package closes classification-table/browser acceptance.

Reviewer: independent correctness reviewer. Date: 2026-09-10.
Contract ancestor: `f59d18942`.
Scope: Builder resolver/registry, project-config update compatibility, changed
snapshot/registry/update tests and the named-run repair script. No runtime
edits, test runs or live-project mutations were performed by this reviewer.
The full suite was excluded by the operator.

## Findings

No concrete blocking implementation defect was found in the reviewed diff.
The earlier missing-management-mapping finding is closed in code: registry
writes select existing source-compatible mappings and include the selected
mapping in each landuse component's revision.

One acceptance gap remains pending execution evidence: initialization and SBS
upload alone do not exercise the newly enabled Disturbed event workflow. The
new snapshot matrix proves required burn classes, but does not verify source
class coverage or generated model inputs. Record a disposable Builder run
through no-SBS landuse completion and subsequent soil generation, verifying
the selected mapping and resulting soil file. If WEPP preparation is exercised,
also verify propagation to `wepp/runs/*`; do not regenerate fair-division merely
to produce review evidence. This closes the NoDb downstream-propagation gate
for the intentionally changed normal Disturbed workflow.

## Reviewed behavior

- `config_builder/resolver.py:505` adds `disturbed` once, before optional
  selections. Manifest selections remain untouched. Existing resolver checks
  still reject unknown and duplicate user-selected modules.
- `config_builder/registry.py:552` explicitly covers NLCD/EMAPR, CORINE,
  Australian and C3S sources; unknown sources fail instead of silently receiving
  an incompatible mapping. Ownership, writes and source revision include the
  selected mapping. Existing numerical routines and lookup contents are unchanged.
- `project_config_update.py:864` exempts only the preserved mapping key from
  selected-source equality. The completeness check has the same narrow
  exception. Other source-selection checks remain intact; missing mappings can
  be explicit additive updates and populated values remain untouched.
- Module equality accepts only the historical ordered list or its exact
  required-dependency form. The change does not accept arbitrary subsets,
  duplicates or unrelated additional modules. Existing refresh code preserves
  the actual project's module list.
- `artifacts/repair_fair_division.py` is fixed to the named project. It verifies
  Builder authority, rejects read-only state and custom mappings, hydrates core
  controllers before mutation, and refuses absent-controller/orphan-directory
  or backup states. It reuses existing Disturbed state and applies changes in
  canonical lock scopes. Configuration and manifest digests are checked after
  mutation. Existing generated artifacts are not rebuilt.

## Evidence and residual risk

The implementer reports 138 focused tests, the five-locale/all-exposed-source
mapping matrix, and nine added compatibility cases passing. The named repair
report states unchanged configuration/manifest digests and a valid mapping
lookup; idempotence and authenticated Builder upload/removal evidence were still
in progress at this review. These are implementer reports, not independently
rerun results.

The new historical-value tests start from a current component revision. Add or
record a prior-v3 landuse revision with a missing mapping to exercise the actual
capability-refresh/completeness path, including required acknowledgment. Existing
refresh tests cover that machinery separately but not this combined condition.
The source matrix should also verify source raster class coverage, rather than
only the nine added burn classes. These are targeted coverage needs, not a request
to run the full suite.

The repair uses separate controller transactions, so interruption can leave a
partially enabled project. The operation is idempotent and retains local backups;
its completion and a second invocation must be verified before reporting success.
The script is an operator artifact, not a general migration endpoint. Concurrent
creation or broad fleet repair is outside its scope.

Approve the implementation design. Final package acceptance is contingent on
the pending focused generation, repair-idempotence and browser evidence above.

## Final core implementation disposition

The subsequent focused evidence closes the core implementation conditions:
`/tmp/builder-sbs-final-combined.log` records 178 passing tests, and
`/tmp/builder-sbs-final-compat.log` records all 15 historical/current mapping and
module cases passing. The tests now exercise a historical landuse revision with
an actual capability-refresh acknowledgment. `/tmp/builder-sbs-inputs.log` proves
the no-SBS landuse event, unburned Disturbed soil adjustment and propagation into
both `soils/base-loam-forest.sol` and `wepp/runs/p1.sol` on the disposable Builder
run. The source script is retained as `runtime_inputs.py`.

Approve the Builder core implementation. The browser retry verifies upload,
filename reload and removal, but does not assert completed classification-table
rendering. That discovered UI failure is being closed by the separately reviewed
`20260910_sbs_native_upload` package; do not describe the older browser log as
proof of a completed classification table. Regional sources have mapping/burn-
class checks, not full regional landuse/soil builds.

Repair documentation correction: `NoDbBase.locked()` does not itself rehydrate
durable state. The repair script's comment claiming that refresh should be
corrected. The stale-write gate rejects an intervening incompatible file write;
the quiescent named-run repair and repeat must not be represented as a general
concurrent migration procedure. No broad repair or full suite is authorized.

The repair comment is corrected in the final source. The named repair's second
invocation reports all nine controllers, `mapping=disturbed`, `has_sbs=false` and
unchanged configuration/manifest digests (`/tmp/builder-sbs-repair-repeat.log`).
The generated-input script now also writes landuse parquet so the disposable
project remains complete for subsequent browser reopening. Final classification
rendering evidence remains tracked by the native SBS package.

## Final acceptance

Approve the completed Builder implementation and named repair. The subsequent
[native SBS proxy workflow](../../20260910_sbs_native_upload/artifacts/proxy_browser.log)
on a Builder-created project proves completed classification-table/map display,
filename update, failure retention, recovery and reload. Its always-present
filename display and text-safe update also close the first-upload display gap.
The earlier Builder browser record proves removal separately.

Retained Builder evidence is available in [focused_tests.log](focused_tests.log),
[generated_inputs.log](generated_inputs.log), [repair.log](repair.log) and
[browser_upload_remove.log](browser_upload_remove.log). No unresolved correctness
finding remains. Regional mapping tests do not constitute full regional model
validation, and this scoped repair is not a fleet migration. No full Python suite
or production deployment was performed for this package.
