# Execute: NoDb Atomic Write Replace Hardening (High-Risk)

Execute this work package end-to-end:

- Package: `/workdir/wepppy/docs/work-packages/20260519_nodb_atomic_write_hardening/`
- Active ExecPlan: `/workdir/wepppy/docs/work-packages/20260519_nodb_atomic_write_hardening/prompts/active/nodb_atomic_write_hardening_execplan.md`

Required outcomes:
1. `NoDbBase.dump()` no longer uses in-place truncate/write and instead persists through atomic temp-file + replace semantics.
2. Stale-writer and lock-ownership safeguards remain intact.
3. Regression tests cover read-safety during writes (no empty/partial payload visibility).
4. Validation evidence includes targeted NoDb boundary tests and pre-handoff full-suite sanity (or documented blocker/waiver).
5. Iterative review closure is complete: `reviewer` and `qa_reviewer` both report zero unresolved High/Medium findings in the final round.

Implementation scope:
- Primary code path:
  - `wepppy/nodb/base.py`
- Primary tests:
  - `tests/nodb/test_base_boundary_characterization.py`
  - Additional narrowly scoped `tests/nodb/*` files only if required by the atomic-write change.
- Package lifecycle docs:
  - `docs/work-packages/20260519_nodb_atomic_write_hardening/package.md`
  - `docs/work-packages/20260519_nodb_atomic_write_hardening/tracker.md`
  - `docs/work-packages/20260519_nodb_atomic_write_hardening/prompts/active/nodb_atomic_write_hardening_execplan.md`
  - `PROJECT_TRACKER.md`
- Review artifacts:
  - `docs/work-packages/20260519_nodb_atomic_write_hardening/artifacts/20260520_reviewer_disposition.md`
  - `docs/work-packages/20260519_nodb_atomic_write_hardening/artifacts/20260520_qa_reviewer_disposition.md`
  - `docs/work-packages/20260519_nodb_atomic_write_hardening/artifacts/20260520_iterative_review_rollup.md`

Execution constraints:
- Keep scope limited to suggestion `1` (atomic write replacement only).
- Do not add decode retry/backoff logic in this package.
- Do not add caller-layer Omni retry logic in this package.
- Preserve existing public contracts and NoDb stale-write/lock semantics.
- Do not add silent fallback wrappers that mask dependency failures.

Iterative review/disposition loop (mandatory):
1. Implement next scoped patch.
2. Run validation gates.
3. Run `reviewer` and `qa_reviewer`.
4. Record findings and disposition updates in artifacts + tracker.
5. If either reviewer reports unresolved High/Medium findings:
   - remediate findings,
   - rerun validation gates,
   - rerun both reviewers,
   - update rollup artifact with the new round.
6. Exit only when both reviewers report zero unresolved High/Medium findings.

Validation commands:
- `wctl run-pytest tests/nodb/test_base_boundary_characterization.py --maxfail=1`
- Run any additional targeted pytest command for newly touched test modules.
- `wctl run-pytest tests --maxfail=1`
- If full-suite fails due to unrelated baseline failure, record exact failure signature and explicit waiver rationale in `tracker.md` and rollup artifact.
- `wctl doc-lint --path docs/work-packages/20260519_nodb_atomic_write_hardening --path PROJECT_TRACKER.md`
- `git diff --check`

Package lifecycle updates required:
- Keep ExecPlan living sections current (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`).
- Update `tracker.md` with UTC-stamped progress notes for each implementation/review round.
- Keep `artifacts/20260520_iterative_review_rollup.md` current per round.
- Update `package.md` closure notes at completion.
- Move package state in `PROJECT_TRACKER.md` when status changes.

Finish with a concise closure summary:
- changed files
- behavior delta
- validation commands + results
- iterative review rounds and final finding counts
- residual risks/follow-ups
