# Add Omni thinning 30% and 50%


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture


Users can choose 30%, 40%, 50%, or 65% target canopy in Omni thinning with the
same four ground covers. New rows still default to 40%. Existing runs continue
to load and rebuild. Deliver code and local input-artifact validation, not deployment.

## Progress


- [x] (2026-09-20 19:32 UTC) Scope, compatibility plan and canonical amendment drafted.
- [x] Review and commit contract checkpoint `e56d610e1`.
- [x] Implement assets, catalogs and selector; 188 focused tests pass.
- [x] (2026-09-20 20:06 UTC) Gates, independent review and local delivery complete.

## Surprises & Discoveries


Five catalogs contain thinning entries; AU, EU and revegetation contain only 40%.
C3S already includes 40% and 65%.
Saved summaries reference legacy filenames directly. Keep those files untouched.
The existing canopy override also changes LAI (plant leaf area); do not use it.

## Decision Log


2026-09-20: Operator chose eight new static variants over a shared template.
This minimizes runtime change and preserves existing numerical behavior. New
records cover only 30/50 in each applicable catalog; do not repair regional 65%
availability as unrelated work. Default stays 40%, ground default stays 93%.

## Context and Orientation


`wepppy/weppcloud/controllers_js/omni.js` builds selects. `wepppy/wepp/management/data/`
contains mapping JSON and UnDisturbed management files. Omni resolves a string
such as thinning_30_93 through Treatments to a numeric mapping key. Both ordinary
and multi-OFE (multiple slope segments) landuse use those files. No parser or
worker change is needed. Contract is `docs/ui-docs/contracts/omni-thinning-contract.md`.

## Plan of Work


First obtain two independent read-only reviews and commit the documentation-only
checkpoint. Then copy each Thinning_40_{ground}.man for canopy 30 and 50, replacing
only its numeric canopy token. Add records with unused keys to disturbed,
c3s-disturbed, au-disturbed, eu-corine-disturbed and revegetation JSON. Extend the
existing CSV export where applicable. Add select options in ascending order and
explicit 40% default without changing other controls. Update user/module docs.

## Concrete Steps


From repository root, inspect diffs, run `wctl run-npm lint`, `wctl run-npm test`,
`python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`, focused
`wctl run-pytest tests/wepp/management tests/nodb/test_mofe_scenario_artifacts.py`,
and `wctl run-pytest tests --maxfail=1`. Lint touched docs with `wctl doc-lint --path`.
Do not start containers if unavailable; record exact blocked gates.

## Validation and Acceptance


Confirm dropdown values/default and hydration for new and legacy choices. Parse
all eight new managements through real mappings and verify canopy fraction,
matching rill/interrill ground fractions, and unchanged remaining parameters.
Read back serialized single-OFE and generated/prepared MOFE inputs. Existing
mapping records and legacy file bytes must match starting revision. Local
fixture evidence supports locally validated status only, not live execution.

## Idempotence and Recovery


Edits are additive except selector/docs changes. Never rewrite existing project
state. Revert only package changes if validation fails; preserve diagnostic logs.
Do not remove new assets from an installation already holding runs using them.

## Artifacts and Notes


Retain review reports and concise test logs under package artifacts. Update tracker
and this plan after milestones. Move this plan to completed at code-delivery closeout.

## Interfaces and Dependencies


Keep percent-string payload fields canopy_cover and ground_cover, scenario names,
NoDb serialization, treatment masks and soil rules unchanged. No dependency added.

## Outcomes & Retrospective


Implementation and focused artifacts validated. Broad-suite snapshot required
eight additive expected classes. File-level continuation unexpectedly opts native
WBT integration tests in; directory-level continuation preserves original broad
suite behavior. No unrelated runtime fix is in scope.

## Archive and inspection evidence

Archived/restored runs are supported states: preserve new/legacy selections and
management bytes at existing landuse and prepared-input paths. Exercise the
canonical project archive/restore implementation with these files and compare
restored bytes. Run existing browse/download coverage. Live browser/download
acceptance remains explicitly unverified unless exercised; operator owns that
pre-deployment gate. Local code-delivery closure must state this limitation.

## Final outcome

Eight additive thinning variants and the selector are implemented. Legacy assets
and records are unchanged. 188 focused, 911 frontend and 38 browse/download
checks pass. Broad coverage completed with 9,169 passes and 99 skips across
initial/continuation runs after an existing catalog snapshot update. All reviews
approved. Local code delivery is complete; no deployment/live model claims.

Revision note 2026-09-20: closed after generated-input and full collected-suite
evidence. Retained continuation discovery so future runs preserve opt-in semantics.
