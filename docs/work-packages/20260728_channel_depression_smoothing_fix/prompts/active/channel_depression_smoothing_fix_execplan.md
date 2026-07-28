# Restore Channel Depression Smoothing Selection Propagation

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
remain current.

## Purpose / Big Picture

After this fix, a user can choose Fill, Breach, or Breach (Least Cost), build
channels, reload the run, and see the same selection because the browser sends
and the worker persists the chosen token. The production symptom is observable
as `wbt_fill_or_breach: null`; acceptance changes that value to the selected
token without altering channel algorithms or defaults.

## Progress

- [x] (2026-07-28 06:00 UTC) Confirmed the production run state, worker
  arguments, logs, and rendered-template/controller name mismatch.
- [x] (2026-07-28 06:10 UTC) Recorded the bounded REM-05 contract decision and
  implementation boundary.
- [ ] Register GOV-00A-M1E/REM-05, obtain two independent checkpoint reviews,
  disposition findings, and commit the documentation-only ancestor.
- [ ] Apply the one-field template conformance fix and actual-template
  regression test.
- [ ] Run focused frontend and documentation validation.
- [ ] Complete independent final security/correctness reviews and close REM-05.
- [ ] Push all local commits, gate production queues, pull and deploy on wepp1,
  and verify service and rendered contract.

## Surprises & Discoveries

- Observation: Existing JavaScript fixtures already use the intended DOM
  id/name split, so controller tests passed while production markup emitted the
  wrong name.
  Evidence: both channel Jest fixtures render
  `id="input_wbt_fill_or_breach" name="wbt_fill_or_breach"`, while the Pure
  template omits the macro's `field_name` argument.

- Observation: The production worker received `None` exactly as the browser
  payload indicated.
  Evidence: both `fetch_dem_and_build_channels_rq` and child
  `build_channels_rq` job arguments contain `None` in the smoothing position.

## Decision Log

- Decision: Register a finite REM-05 borrower of DOM-05 rather than execute the
  planned full DOM-05 package.
  Rationale: The production defect is one field-name mismatch; map
  orchestration, upload, route, queue, and complete channel audit work remain
  dependency-gated and out of scope.
  Date/Author: 2026-07-28 / Operator direction, recorded by Codex.

- Decision: Preserve the DOM id and set only the macro's submitted
  `field_name`.
  Rationale: Existing controller selectors and tests depend on the id, while
  the canonical request and worker contract use `wbt_fill_or_breach`.
  Date/Author: 2026-07-28 / Codex.

## Outcomes & Retrospective

Pending implementation and deployment.

## Context and Orientation

`wepppy/weppcloud/templates/controls/channel_delineation_pure.htm` renders the
selector with the shared `select_field` macro. That macro uses its field id as
the submitted name unless `field_name` is supplied. Both
`wepppy/weppcloud/controllers_js/channel_delineation.js` and `channel_gl.js`
serialize forms and read `raw.wbt_fill_or_breach`. The rq-engine route passes
that value to `wepppy/rq/project_rq.py`, where `build_channels_rq` persists a
non-null override before calling `Watershed.build_channels`.

DOM-05 is the planned full owner. REM-05 borrows only the smoothing selector's
render/serialize/persist/reload path and leaves DOM-05 planned and unverified.

## Plan of Work

First register REM-05 and GOV-00A-M1E in the parent authority documents. Obtain
one independent governance/correctness review and one independent
security/operations review. Resolve all findings and commit only documentation
as a standalone ancestor.

Then add `field_name="wbt_fill_or_breach"` to the existing macro invocation.
Extend the actual-template pytest fixture with the minimal Watershed attributes
needed to render the channel template and assert the exact id/name/data-hook
contract plus selected hydration from a representative persisted value. Add
focused worker characterization for non-null assignment before build, null
compatibility, and post-assignment build failure semantics. Update the Channel
Delineation Usersum guide to state that a successful build persists the
selection for reload.

Run focused pytest, all JavaScript lint/tests because the paired controller
contract is involved, documentation lint, and diff checks. Complete independent
final reviews, close the package records, commit, and push all local commits.

On wepp1, verify host identity and repository state, run the RQ deploy gate,
pull the pushed revision, deploy using the canonical production script, and
verify the WEPPcloud container is healthy and the rendered selector has the
canonical submitted name.

## Concrete Steps

Work from `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py
    wctl run-pytest tests/rq/test_project_rq_mutation_guards.py
    wctl run-npm lint
    wctl run-npm test
    wctl doc-lint --path \
      docs/work-packages/20260728_channel_depression_smoothing_fix
    wctl doc-lint --path \
      wepppy/weppcloud/routes/usersum/weppcloud/controls/channel-delineation.md
    git diff --check

Before deployment on wepp1:

    hostname
    pwd
    cd /workdir/wepppy
    wctl rq-info --detailed
    git pull --ff-only
    scripts/deploy-production.sh

## Validation and Acceptance

The actual-template test must prove the selector renders id
`input_wbt_fill_or_breach`, name `wbt_fill_or_breach`, and the existing data
hook. JavaScript tests must continue to prove the selected token reaches the
request payload. Documentation lint and diff checks must pass.

Production acceptance requires the deployed WEPPcloud service to be healthy and
the deployed Channel Delineation template source/markup to contain the corrected
name. Automated tests prove a Fill selection carries
`"wbt_fill_or_breach":"fill"` and persists through the existing worker path.
Production verification is read-only: do not submit or rebuild the named user
run without separate authorization.

## Idempotence and Recovery

The source fix and tests are repeatable. The production pull must be
fast-forward-only. Record the pre-deploy wepp1 revision. Abort if queues are
active, the repository is dirty/diverged, the pull is not a fast-forward, the
build fails, or WEPPcloud is unhealthy.

The deployment script is the canonical retry path. If the new revision causes
the targeted service failure, revert the REM-05 implementation commit on the
publishing checkout, push that explicit revert, gate queues again, and rerun the
canonical deployment script. Verify the container is healthy, its running
revision matches the revert, and the prior markup is restored. Do not use
`git reset --hard`, manually replace source trees, restart unrelated services,
or mutate the user's run.

## Artifacts and Notes

Checkpoint and final reviews live under this package's `artifacts/` directory.
The production incident evidence is summarized in the contract decision without
copying run data beyond the affected field and job identifiers.

## Interfaces and Dependencies

Use the existing Pure `select_field` macro's `field_name` argument. Add no
dependency, route, queue edge, enum, parser alias, or persistence field. The
canonical RQ response, CSRF, and NoDb persistence contracts remain unchanged.

Revision note (2026-07-28): Created for the operator-authorized REM-05
production restoration and deployment.
