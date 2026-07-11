# Kickoff — Harden `build_ghcn_daily_climate` CLIGEN Invocation (mini work-package)

Dispatched by: operator (via Claude Code handoff, 2026-07-10)
Executor: Codex
Mode: **ExecPlan** — author
`docs/mini-work-packages/20260710_ghcn_cligen_runner_guard_execplan.md`
per `docs/prompt_templates/codex_exec_plans.md` (living document:
keep Progress / Surprises & Discoveries / Decision Log / Outcomes &
Retrospective current), then execute it.

## Repository / branch discipline

- Repository: wepppy, checkout `/workdir/wepppy`, branch **master**,
  push to `origin master`. Note: the working tree currently carries
  unrelated modified files (`docs/ui-docs/...preflight_behavior.md`,
  `docs/work-packages/20260709_ag_fields_runs_page_ui/...`) — leave
  them alone; stage only your own changes.

## The defect (audited 2026-07-10, from the cligen-rs exit-code audit)

`wepppy/climates/cligen/cligen.py::Cligen.build_ghcn_daily_climate`
(≈ lines 1695–1735) is the **one remaining CLIGEN invocation site
that ignores the process exit code**. Commit `51789e11d` ("Guard
observed CLIGEN quality failures and vendor cligen532", closed by
`5f6453016`) hardened `run_observed` and added `_run_cligen_posix`;
this site predates that work and has the full defect set:

1. `p.wait()` with **no returncode check** — failure detection is
   `return _exists(cli_fn)` only, so a crashed CLIGEN that left a
   partial `.cli` reads as success (the exact "silent pass" class
   `51789e11d` was written to kill).
2. **No timeout** — a hung CLIGEN hangs the caller forever
   (`run_observed` got retries/backoff + SIGTERM→SIGKILL for this).
3. `stdin=PIPE` opened and never written/closed before `wait()` — a
   deadlock if the binary ever prompts (all flags are passed, so it
   shouldn't, but the safe shape is `DEVNULL` or the
   `_run_cligen_posix` pattern).
4. **CWD-relative side effects**: `open("cligen.log", "w")` and
   `shutil.copyfile(self.parpath, self.par)` land in whatever the
   process CWD happens to be, not the run directory.
5. Debug `print(cmd)` on stdout.
6. No cleanup of a partial/zero-size `cli_fn` on failure, and a mixed
   return contract (`None` for no-GHCN-id / no-data, else bool).

## Scope

Bring this site to the same standard as its siblings — **prefer
generalizing `_run_cligen_posix`** (it currently requires a `clinp`
stdin file; this site needs no stdin — make stdin optional/devnull)
over adding a third bespoke invocation path. Requirements:

- Nonzero exit → remove any partial `cli_fn` → raise `RuntimeError`
  naming the station/par/prn/cli (mirror `run_observed`'s message
  shape); zero-size/absent `cli_fn` after a zero exit → error, not
  `True`.
- Timeout with process-group termination (reuse the existing
  pattern/constants; whether this site needs `run_observed`-style
  retries is an ExecPlan decision — a single timeout+kill is the
  floor).
- Log to a deterministic location (the `cli_fn` directory or
  `self.wd`), not CWD; same for the par copy; drop the `print`.
- Preserve the documented early-return semantics: `None` when GHCN id
  resolution or data acquisition fails (that part is behavior, not
  defect).

**Contract note (load-bearing):** `build_ghcn_daily_climate` has no
in-repo Python callers (definition + a `climates/cligen/README.md`
mention only — verified 2026-07-10). Raising on process failure is
therefore safe in-repo; record in the ExecPlan Decision Log that
downstream/notebook callers get exceptions instead of `False`, and
update the README sentence if the contract wording changes.

**Out of scope:** any change to the vendored `cligen532` binary, the
`.cli`/`.prn` byte surfaces, or GHCN acquisition logic
(`ghcn_daily.py`). No new dependencies (else the
dependency-evaluation-standard gate applies). No parameterization
changes, so no ADR is required.

## Tests

Unit tests mirroring
`tests/climate/test_cligen_run_observed_retries.py` (fake process +
monkeypatched `find_ghcn_id` / `acquire_ghcn_daily_data` /
`df_to_prn`; no network, no real binary):

- nonzero returncode → `RuntimeError`, partial `cli_fn` removed;
- zero exit but absent/zero-size `cli_fn` → failure, not `True`;
- timeout path → termination escalation and failure;
- success path → `True`, log written to the run directory, no
  stray CWD artifacts;
- the `None` early-returns preserved.

## Gates (AGENTS.md)

- Iteration: `wctl run-pytest tests/climate`
- Pre-handoff: `wctl run-pytest tests --maxfail=1`
- Dead-code gate: `.venv/bin/vulture` (config in `pyproject.toml`)
- Evidence discipline: label Ran vs Static in the ExecPlan; record
  the exact commands and outcomes; no pre-filled results.

## Stop condition

ExecPlan `Status: Complete` with validation outcomes recorded; your
changes committed to `master` and pushed; report the ExecPlan path
and a summary back to the operator. If a decision point cannot be
resolved from this kickoff plus the repo (e.g., an unexpected
downstream caller surfaces), hold with the question in the ExecPlan
rather than guessing.
