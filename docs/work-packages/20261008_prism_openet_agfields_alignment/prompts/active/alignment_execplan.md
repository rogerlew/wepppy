# Enable and verify PRISM downstream consumers

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Allow historic PRISM runs to acquire OpenET monthly ET and use AgFields crop
rotations. Verify calendar alignment and inheritance of actual prepared forcing.

## Progress

- [x] 2026-10-08: Confirmed both missing mode-16 allowlist entries.
- [ ] Ratify the contract with two read-only reviews and an ancestor commit.
- [ ] Add eligibility and regression coverage.
- [ ] Inspect real PRISM/OpenET/AgFields artifacts and run focused validation.
- [ ] Update user documentation and record results/limitations.

## Surprises & Discoveries

OpenET uses Climate Engine credentials, not necessarily the direct OpenET API
key supplied for the earlier study. Inspect credentials without exposing them.
AgFields references the parent climate by relative path rather than copying it.

## Decision Log

- 2026-10-08: Preserve existing year handling, feature access and parent sampling;
  scope is source eligibility, not new ET or agricultural parameterization.

## Outcomes & Retrospective

Pending implementation and artifact checks.

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
