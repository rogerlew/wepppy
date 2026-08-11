# Restore checked forks for runs with no Omni child workspace

This ExecPlan is a living document maintained in accordance with
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.

## Purpose / Big Picture

A user can request a fork that omits Omni scenario and contrast children even
when the source has never materialized those optional children. The fork will
create the required empty destination structure and complete, while still
rejecting symlinks and special files that could escape or corrupt the run tree.

## Progress

- [x] (2026-08-11 00:00 UTC) Captured production job evidence and canonical
  contract discrepancy.
- [x] (2026-08-11 00:00 UTC) Opened SURF-04B-C1 and dispatched independent
  correctness, QA, and security pre-reviews.
- [x] (2026-08-11 00:09 UTC) Added and ran a direct missing-`_pups`
  regression before implementation; it failed with the production
  `FileNotFoundError` at `_open_fork_chain`.
- [x] (2026-08-11 00:10 UTC) Implemented descriptor-relative safe ancestor
  creation without relaxing strict traversal helpers.
- [x] (2026-08-11 00:12 UTC) Added the complete absent/empty/populated/hostile
  state matrix and an orchestration regression that keeps the directory reset
  helper real while mocking unrelated controller work.
- [x] (2026-08-11 00:08 UTC) Amended affected user/developer and
  review-governance documentation before production implementation.
- [x] (2026-08-11 00:49 UTC) Ran focused and repository-wide validation,
  dispositioned all final reviews, and documented unrelated monolithic/sharded
  isolation blockers with isolated-test evidence.
- [x] (2026-08-11 00:50 UTC) Closed the package; prompt ready for archival.

## Surprises & Discoveries

- Observation: the 85-test focused suite passed because the only direct reset
  test begins with an existing `_pups/omni` hierarchy and higher-level reset
  tests mock the directory helper.
  Evidence: `tests/rq/test_project_rq_fork.py` and the independent QA review.
- Observation: `Omni.__init__` creates root `omni/` but does not create
  `_pups/omni`; absence is therefore a normal fresh-controller state.
  Evidence: `wepppy/nodb/mods/omni/omni.py` and the production source tree.
- Observation: the new direct incident regression failed before the production
  patch with `FileNotFoundError: [Errno 2] No such file or directory: '_pups'`.
  Evidence: the 2026-08-11 00:09 UTC targeted `wctl run-pytest` transcript
  recorded in `tracker.md`.
- Observation: final correctness review identified that a composed smoke test
  still mocked `_reset_forked_omni` and that socket behavior was claimed but not
  directly tested.
  Evidence: the test now keeps `_reset_forked_omni` real, stubs only unrelated
  controller/Redis/cache collaborators, and covers Unix-socket ancestors; the
  focused suite passes 102 tests.
- Observation: the first full-suite attempt stopped in pytest fixture setup,
  before a test assertion, because its shared default `/tmp` base could not
  allocate a numbered child directory after ten attempts.
  Evidence: 169 passed and 13 skipped before the `OSError`; the rerun uses a
  dedicated directory created by `mktemp` and supplied through `--basetemp`.

## Decision Log

- Decision: classify as a conformance fix, not a behavior amendment.
  Rationale: SURF-04B already requires the final empty structure, idempotence,
  and validity of every boolean combination; only implementation/test evidence
  is wrong.
  Date/Author: 2026-08-11 / Codex.
- Decision: create only missing ancestors, then open them with the existing
  no-follow real-directory helper; never replace an existing ancestor.
  Rationale: this preserves valid absence and hostile-entry containment at the
  same time.
  Date/Author: 2026-08-11 / Codex.

## Outcomes & Retrospective

The implementation and focused evidence are complete. Valid absence now
converges to the contracted empty destination hierarchy, while hostile existing
entries still fail closed. Governance now requires correctness/UX valid-state
evidence separately from security containment evidence. Correctness, QA, and
security reviews pass with no unresolved findings. Repository-wide validation
was attempted through both canonical runners; unrelated cross-module cwd and
integration opt-in leakage prevented a clean aggregate result, while isolated
reported tests behaved correctly. No production action was taken.

## Context and Orientation

`wepppy/rq/project_rq.py::_reset_forked_omni` resets the copied Omni controller
and calls `wepppy/rq/project_rq_fork.py::_reset_fork_omni_directories`. At the
incident revision, the latter opened `_pups/omni` as an existing chain, so a
missing `_pups` raised `FileNotFoundError` after copy and metadata reset had
already begun. The fixed helper creates only missing reset ancestors through
held directory descriptors, verifies them with a no-follow directory open, and
then replaces only `scenarios`, `contrasts`, and root `omni` with empty real
directories.

The unchanged canonical contract is the accepted SURF-04B decision in
`docs/work-packages/20260806_fork_skip_omni_reset/artifacts/2026-08-06_contract_decision.md`.
This package must not change UI fields, request parsing, queue wiring, Omni
model semantics, or partial-destination policy.

## Plan of Work

First add direct tests in `tests/rq/test_project_rq_fork.py` that demonstrate the
production failure with no `_pups`, creation under an existing `_pups`,
idempotence, preservation of unrelated siblings, reset of populated targets,
and refusal of symlink/special ancestors. Add one narrow fork orchestration test
that leaves the directory helper real so mocks cannot hide this boundary.

Then add a small descriptor-relative ensure helper beside `_open_fork_chain` in
`wepppy/rq/project_rq_fork.py`. It may call `os.mkdir` only for a missing child,
must tolerate a concurrent creator only by reopening and verifying the final
entry, and must return a descriptor opened with the existing
`O_DIRECTORY | O_NOFOLLOW` policy. Update `_reset_fork_omni_directories` to use
it only for `_pups` and `_pups/omni`. Keep leaf replacement behavior unchanged.

Finally update the originating package retrospective, user/developer forking
documentation, contract-first/hardening/work-package review guidance, and the
security review template so valid-state and noninterference evidence are
release gates. Run validation and obtain independent final reviews.

## Concrete Steps

From `/home/workdir/wepppy`:

1. Run the new incident regression before implementation and expect the
   missing-`_pups` case to fail with `FileNotFoundError`.
2. Apply the minimal helper and run
   `wctl run-pytest tests/rq/test_project_rq_fork.py`.
3. Run `wctl run-pytest tests --maxfail=1`.
4. Run `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`.
5. Run scoped `wctl doc-lint --path` checks for every changed Markdown file.

## Validation and Acceptance

Acceptance requires all direct valid layouts to produce real non-symlink empty
targets and preserve unrelated siblings. Every hostile existing ancestor must
raise without touching an external sentinel. The checked orchestration test
must reach the success trigger with no `_pups` fixture. Existing tests and the
full suite must remain green. Correctness, QA, and security artifacts must have
no unresolved medium/high findings.

## Idempotence and Recovery

The reset may be repeated: missing ancestors are created once, verified on
later runs, and the exact three reset targets become empty each time. Existing
ancestors are never replaced. Test files use `tmp_path`; no cleanup outside the
fixture is required. No production mutation or retry is part of this plan.

## Artifacts and Notes

The package will retain correctness, QA, and security review artifacts plus
focused/full validation summaries. Production job IDs and the exact traceback
are recorded in `package.md`; no tokens or user content are included.

## Interfaces and Dependencies

No public API changes. The internal helper accepts a parent directory
descriptor and child name, creates the child only if absent, verifies it with
the existing `_open_fork_dir`, and returns the opened descriptor. Use only the
Python standard library and existing module helpers.

Plan revision note (2026-08-11): initial incident-remediation plan created from
wepp1 evidence and the unchanged SURF-04B contract. At 00:14 UTC the plan was
updated with pre-patch failure evidence, completed implementation steps, and
precise orchestration-mocking scope after QA review.

Plan closure note (2026-08-11 00:50 UTC): implementation, focused validation,
governance, and three independent review gates completed. Repository-wide
monolithic/sharded blockers and isolated-test evidence were recorded before
package closure; the prompt is archived with this outcome.
