# Enable and verify PRISM downstream consumers

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Allow historic PRISM runs to acquire OpenET monthly ET and use AgFields crop
rotations. Verify calendar alignment and inheritance of actual prepared forcing.

## Progress

- [x] 2026-10-08: Confirmed both missing mode-16 allowlist entries.
- [x] 2026-10-09 02:24 UTC: Two independent PASS reviews; checkpoint 18076eaa9.
- [x] 2026-10-09 02:27 UTC: Two allowlist additions; 182 focused tests and 3 parent-reference tests pass.
- [x] 2026-10-09 02:34 UTC: Six native runs, six readiness checks and 432 monthly joins pass.
- [x] 2026-10-09 UTC: Full suite 10,491 passed/126 skipped; 106 source files match the archive.
- [ ] Deferred external follow-up: renew the expired Climate Engine token and repeat production acquisition. Operator accepted this gap for commit/push.
- [x] 2026-10-09 UTC: User/operator docs, two correctness reviews and limitations recorded.

## Surprises & Discoveries

Climate Engine returned HTTP 401 for all six attempted series. Its configured
credential is distinct from the working direct OpenET key. Direct API evidence
will be labeled separately, without changing production providers. A management
synthesis test fixture failed native WEPP plant-height validation; the probe
uses the existing one-year corn-no-till management instead, without changing it.
AgFields references the parent climate by relative path rather than copying it.

## Decision Log

- 2026-10-09: Operator confirmed the Climate Engine token is expired and authorized
  commit/push with renewal and acquisition recheck deferred. No credential or
  provider changes are included.

- 2026-10-08: Preserve existing year handling, feature access and parent sampling;
  scope is source eligibility, not new ET or agricultural parameterization.

## Outcomes & Retrospective

Eligibility is implemented. Six native AgFields runs and six actual readiness/
schedule checks pass. Direct OpenET alignment passes: all 216 observations match both spatial methods.
Full validation passes: 10,491 tests passed and 126 skipped. Forest RQ services
were refreshed with all workers idle; health and worker climate validation pass.
Production Climate Engine acquisition remains unverified because its token is
expired; the operator accepted this known external follow-up for commit/push.

## Context and Orientation

`wepppy/nodb/mods/openet/openet_ts.py` validates climate before monthly acquisition.
`wepppy/nodb/mods/ag_fields/ag_fields.py` computes readiness and writes subfield
WEPP runs referencing parent CLI files. Mode 16 is historic PRISM. Spatial method
1 revises centroid forcing; method 2 chooses a native cell per hillslope.
The existing forest run `/wc1/runs/ch/chemotherapeutic-scope` has validated
2019–2021 forcing and WEPP outputs, with both methods archived under
`archives/prism-integration-mode{1,2}-2019-2021`. Preserve that run's final state.

## Plan of Work

Ratify `docs/schemas/prism-downstream-eligibility-contract.md`; record two reviewer
dispositions and commit only new checkpoint files. Add Prism800m to the two
sets. Extend OpenET validation/acquisition tests and AgFields readiness/runner
tests to cover calendars, leap years, invalid states and parent file references.
Use bounded forest artifact probes and existing production parsers/controllers;
do not modify feature grants or replace the completed parent run. Record actual
coverage and any external API limitations without claiming full workflow coverage.

## Concrete Steps

From repository root run `wctl run-pytest tests/nodb/mods/openet
 tests/nodb/mods/test_ag_fields_backend_contract.py
 tests/nodb/mods/test_ag_fields_wepp_runner.py` (one command). Extend route checks
as needed. Use `wctl exec -T weppcloud python` for real artifact probes and
`wctl doc-lint --path <changed-document>` for documentation. Broaden validation
only in proportion to the actual changes and unresolved risks.

## Validation and Acceptance

Mode 16 accepts valid 2019–2021 bounds, existing invalid states still fail, and
both spatial methods retain 1096 daily dates including February 29, 2020.
Generated subfield runs reference their assigned parent's CLI. OpenET samples
join to real WEPP months by hillslope and date; report missing months explicitly.

## Idempotence and Recovery

Keep probes in isolated scratch directories and secrets outside tracked files.
Do not change the source run or its archives. Reverting the two allowlist entries
restores prior eligibility without schema rollback. No deployment is required
for artifact/controller probes; any service restart first checks worker activity.

## Artifacts and Notes

Retain review, test and alignment evidence under this package's artifacts directory.

## Interfaces and Dependencies

Use existing Climate, OpenET_TS, AgFields and WEPP parsers. Add no dependencies.
Revision note: initial bounded follow-up plan created 2026-10-08.

Revision note: full regression and independent artifact audit completed; the
only remaining milestone requires a valid Climate Engine credential.
