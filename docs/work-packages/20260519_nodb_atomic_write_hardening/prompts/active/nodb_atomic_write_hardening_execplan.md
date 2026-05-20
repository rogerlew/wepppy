# ExecPlan: NoDb Atomic Write Replace Hardening

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, NoDb readers will no longer observe empty or partially written JSON payloads while a writer persists state. The user-visible impact is fewer transient `JSONDecodeError` failures in concurrent RQ workloads, specifically the Omni contrast completion path that currently reads shared `omni.nodb` near sibling write completion.

Operators can verify behavior by running the new targeted boundary tests and observing that concurrent write/read coverage passes while stale-writer safeguards remain intact.

## Progress

- [x] (2026-05-20 03:42 UTC) Created work package scaffold and backlog entry.
- [x] (2026-05-20 03:42 UTC) Captured incident signature, scope boundaries, and success criteria.
- [x] (2026-05-20 03:48 UTC) Completed initial `reviewer` pass and integrated documentation findings.
- [x] (2026-05-20 03:48 UTC) Elevated package to high operational risk and added iterative review/disposition-until-verified gates.
- [x] (2026-05-20 04:30 UTC) Added iterative review rollup artifact and revalidated docs lint.
- [x] (2026-05-20 05:05 UTC) Implemented atomic write/replace persistence in `NoDbBase.dump()` with mode-safe behavior and signature-safe failure handling.
- [x] (2026-05-20 05:11 UTC) Added/extended boundary regressions for read safety, legacy deficiency characterization, and atomic failure paths.
- [x] (2026-05-20 05:20 UTC) Ran targeted validation plus full-suite sanity (`tests --maxfail=1`) and documented unrelated Ron baseline blocker/waiver.
- [x] (2026-05-20 05:19 UTC) Completed iterative `reviewer` + `qa_reviewer` cycles to zero unresolved High/Medium findings.

## Surprises & Discoveries

- Observation: `NoDbBase.dump()` currently writes with `open(..., "w")`, which truncates the target file before writing payload bytes.
  Evidence: `wepppy/nodb/base.py` current dump write block around `open(self._nodb, "w")`.
- Observation: Existing boundary tests already cover stale-cache signature and stale-writer rejection, providing strong scaffolding for atomic write migration tests.
  Evidence: `tests/nodb/test_base_boundary_characterization.py` (`test_getinstance_ignores_stale_cache_signature_and_rehydrates_from_disk`, `test_dump_forces_monotonic_signature_after_second_same_size_rewrite`).
- Observation: `os.replace` failure can poison in-memory `_nodb_mtime/_nodb_size` if signatures are assigned before commit; staging signatures in locals avoids false stale-write rejection on retry.
  Evidence: Reviewer finding + new regression `test_dump_replace_failure_preserves_signature_and_allows_retry`.
- Observation: Atomic temp-file swaps can drift file mode semantics unless both rewrite-preservation and first-create umask behavior are handled explicitly.
  Evidence: Reviewer/QA findings + new regressions `test_dump_atomic_replace_preserves_existing_file_mode` and `test_dump_atomic_replace_initial_create_uses_umask_mode`.

## Decision Log

- Decision: Keep this package limited to atomic write replacement and defer decode-retry layers.
  Rationale: User selected suggestion `1`; focused scope reduces regression risk and avoids coupling multiple reliability strategies.
  Date/Author: 2026-05-20 03:42 UTC / Codex.

## Outcomes & Retrospective

Implemented and validated.

- NoDb writes now avoid reader-visible truncate windows by writing to a temp file and atomically replacing the destination.
- Failure paths were hardened to preserve in-memory signatures on replace failure, clean up temp files, preserve expected mode semantics, and treat post-commit directory-fsync failures as durability warnings instead of stale-write rejections.
- Race characterization now includes both positive atomic-read behavior and negative legacy truncate-window behavior (`JSONDecodeError`), giving clear evidence of architectural deficiency in the legacy path.
- Final iterative review loop outcome: both `reviewer` and `qa_reviewer` reported zero unresolved High/Medium findings.
- Remaining unrelated baseline blocker is outside package scope: `tests/nodb/test_ron_fetch_dem_copernicus.py` (`Ron._cellsize`).

## Context and Orientation

`wepppy/nodb/base.py` defines `NoDbBase`, the shared persistence base used by run-scoped controllers such as `Omni`. `NoDbBase.dump()` is the core write path for `.nodb` files and currently performs in-place truncate/write semantics. Concurrent readers (`getInstance`, `load_detached`) call `_decode_jsonpickle` after reading the file text. If a read lands after truncate and before full payload write, JSON decode can fail with `JSONDecodeError`.

The immediate incident manifestation was in Omni contrast dependency update flow:
- `wepppy/nodb/mods/omni/omni_state_contrast_mixin.py::_update_contrast_dependency_tree`
- `type(self).getInstance(self.wd)` during concurrent contrast completions.

Key test anchor:
- `tests/nodb/test_base_boundary_characterization.py`

## Plan of Work

Milestone 1 updates `NoDbBase.dump()` to write serialized payload to a sibling temporary file in the same directory, fsync the temp file, atomically replace the destination via `os.replace`, then fsync the parent directory so the rename is durable. Signature tracking (`_nodb_mtime`, `_nodb_size`) must continue to reflect the final destination file and preserve stale-writer rejection behavior.

Milestone 2 adds regression coverage for reader safety during writes and verifies existing stale-writer/signature tests remain valid. Tests should prove behavior by contract (no empty/partial reader payload), not by brittle timing assumptions.

Milestone 3 executes focused validation plus pre-handoff full-suite sanity (`wctl run-pytest tests --maxfail=1` unless an explicit blocker/waiver is recorded), captures output in the tracker, and records independent `reviewer` + `qa_reviewer` findings/dispositions under package artifacts.

Milestone 4 runs iterative review closure loops: if either reviewer reports High/Medium findings, remediate, rerun validation, update dispositions, and rerun both reviews. Repeat until both reviewer tracks report zero unresolved High/Medium findings.

## Concrete Steps

Work from `/workdir/wepppy`.

1. Edit `wepppy/nodb/base.py` in `NoDbBase.dump()`:
   - Replace in-place truncate/write with temp-file write + fsync + `os.replace`.
   - Keep post-write signature updates aligned to final destination file.
   - Preserve lock and stale-writer contract checks.
2. Update/add tests in `tests/nodb/test_base_boundary_characterization.py` (or a narrow companion file) to cover atomic write read safety.
3. Run targeted validation:
   - `wctl run-pytest tests/nodb/test_base_boundary_characterization.py --maxfail=1`
   - Include any additional targeted test path added for this package.
4. Run pre-handoff full-suite sanity:
   - `wctl run-pytest tests --maxfail=1`
   - If blocked by unrelated baseline failures, capture failure signature and explicit waiver rationale in tracker before handoff.
5. Run doc lint for package docs and tracker updates:
   - `wctl doc-lint --path docs/work-packages/20260519_nodb_atomic_write_hardening`
   - `wctl doc-lint --path PROJECT_TRACKER.md`
6. Dispatch independent `reviewer` and `qa_reviewer` agents; record disposition(s) in `artifacts/`.
7. If either review returns High/Medium findings:
   - remediate findings,
   - rerun validation commands from steps 3-4,
   - append updated disposition evidence,
   - rerun both review agents.
8. Exit the loop only when both reviewers report zero unresolved High/Medium findings.

## Validation and Acceptance

Acceptance is complete when:

- NoDb write path no longer truncates and writes in place.
- New/updated tests demonstrate reader-safety during writes and pass.
- Existing stale-writer/signature boundary tests still pass.
- Pre-handoff full-suite sanity passes, or an explicit blocker/waiver is recorded.
- Package docs and independent review artifacts are updated with commands and outcomes.
- Final iterative review round reports zero unresolved High/Medium findings across `reviewer` and `qa_reviewer`.

Expected validation commands:

- `wctl run-pytest tests/nodb/test_base_boundary_characterization.py --maxfail=1`
- Any additional targeted suite added for this package (record exact command in tracker when introduced).
- `wctl run-pytest tests --maxfail=1` (or documented blocker/waiver if unrelated baseline failures prevent a clean run).

## Idempotence and Recovery

The change is internal and additive to persistence semantics. If implementation causes regressions, revert only this package’s NoDb write-path changes and rerun the targeted boundary suite to restore baseline behavior. Keep file operations in the same directory as the destination so `os.replace` remains atomic on the same filesystem.

## Artifacts and Notes

- Package root: `docs/work-packages/20260519_nodb_atomic_write_hardening/`
- Review disposition artifact target:
  `docs/work-packages/20260519_nodb_atomic_write_hardening/artifacts/20260520_reviewer_disposition.md`
- QA disposition artifact target:
  `docs/work-packages/20260519_nodb_atomic_write_hardening/artifacts/20260520_qa_reviewer_disposition.md`
- Iterative review rollup artifact target:
  `docs/work-packages/20260519_nodb_atomic_write_hardening/artifacts/20260520_iterative_review_rollup.md`

## Interfaces and Dependencies

No external dependency changes are planned. This package modifies only NoDb persistence internals and related tests. Public API/route contracts are unchanged.
