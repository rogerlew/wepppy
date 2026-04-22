# 20260422 MOFE NSCEN Cull ExecPlan

## Objective
Fix MOFE management synthesis so generated `.man` files only include yearly scenarios that are actually referenced, preventing WEPP hillslope failures from invalid yearly counts (`nmscen > 20`).

## Scope
- Add regression fixtures for incidents:
  - `/geodata/wc1/runs/pa/patrician-ambivalence/wepp/runs/p386.{man,slp,err}`
  - `/geodata/wc1/runs/co/congealed-inspector/wepp/runs/p1802.{man,slp,err}`
- Patch MOFE synthesis to cull orphan yearlies, preserve deterministic order, and reindex references contiguously.
- Add explicit guard for true referenced yearly count exceeding WEPP hillslope limit (20).
- Add regression/unit/guard tests.
- Run requested targeted pytest commands.
- Perform self-review with disposition table.

## Milestones
1. Collect incident artifacts and add test fixtures with provenance README.
2. Reproduce/characterize `nscen` inflation from fixture content.
3. Implement yearly-reference compaction and overflow guard in synthesis path.
4. Add regression and unit tests.
5. Run validations and fix any breakage.
6. Self-review diff, capture dispositions, and handoff.

## Progress
- [x] M0: Loaded root and nearest `AGENTS.md` guidance (`wepppy/wepp/management`, `tests`).
- [x] M1: Created this ExecPlan file.
- [x] M1: Verified incident artifacts exist on `wepp1` at provided `/geodata/wc1/runs/...` paths.
- [x] M1: Copied incident artifacts into `tests/wepp/management/fixtures/mofe_nscen_overflow/` with provenance README.
- [x] M2: Confirmed fixture signature:
  - `p386.man`: `nofe=19`, `nscen=21`, referenced yearlies `19`, orphan yearlies `2`.
  - `p1802.man`: `nofe=19`, `nscen=25`, referenced yearlies `19`, orphan yearlies `6`.
- [x] M3: Implemented deterministic yearly compaction + explicit WEPP `nmscen<=20` guard in MOFE synthesis.
- [x] M4: Added tests:
  - fixture-based regression compaction (`p386`, `p1802`)
  - direct synthesis compaction unit test (orphan year in source stack)
  - guard-path failure test for referenced yearly scenarios `>20`
- [x] M5: Ran validations:
  - `wctl run-pytest tests/wepp/management/test_multiple_ofe.py` -> `5 passed`
  - `wctl run-pytest tests/wepp/management -k mofe` -> `4 passed, 9 deselected`
- [x] M6: Completed self-review and dispositions.

## Surprises & Discoveries
- Local mirror under `/wc1/runs` on host `forest` does not contain the two named incident run IDs.
- SSH access to `wepp1` is available, and the exact incident files are present there.
- Incident `.err` files capture the exact hillslope parser failure:
  - `*** nmscen read as   21.  Must be between    1 and   20 ***` (`p386`)
  - `*** nmscen read as   25.  Must be between    1 and   20 ***` (`p1802`)

## Decision Log
- 2026-04-22: Use direct `ssh/scp` reads from `wepp1` to build fixtures from the exact incident files rather than substituting with local mirror artifacts.
- 2026-04-22: Compact yearlies by keeping only names referenced from `man.loops[*].years[*][*].manindx`, preserving existing yearly-section order for deterministic serialization.
- 2026-04-22: Fail fast with `ValueError` when true referenced yearly scenarios exceed the WEPP hillslope limit of 20, instead of writing invalid `.man`.

## Outcomes & Retrospective
- MOFE synthesis now removes orphan yearly scenarios before serialization.
- Yearly references serialize against a contiguous referenced set (`nscen == len(referenced yearlies)`).
- Guardrail now prevents silently writing managements that WEPP hillslope will reject for `nmscen > 20`.
- Regression coverage now includes real production fixtures for both cited incidents.

## Deferred Follow-Up: True `>20` Referenced Yearlies
- Status: deferred (not in this patch set).
- Current behavior is intentional fail-fast when true referenced yearly scenarios exceed WEPP hillslope limit (`20`).
- Future work package should evaluate binary-level limit augmentation in `wepp-forest`, including at minimum:
  - `src/includes_hill/pntype.inc` (`ntype`, `ntype2`)
  - `src/includes_hill/pmxpln.inc` (`mxplan`)
  - `src/infile.for` / `src/readin.for` input-bound assumptions tied to `ntype`
- Risk factors to analyze before changing limits:
  - `ntype` is reused across many parser/input categories, so increasing it changes more than `nmscen`.
  - Common-block and fixed-array sizing side effects may alter memory/runtime characteristics.
  - Downstream contract drift risk between `wepppy` management generation and vendored WEPP binaries.
  - Need output-parity and performance validation for existing baselines plus synthetic `>20` yearly rotations.
- Recommendation: keep current synthesis compaction + guard as the safe default; track `>20` support as a separate, explicitly scoped binary/workflow initiative.

## Review Disposition
- **Medium** — Single-stack synth path bypassed yearly compaction/guard and could still emit invalid yearly sections.  
  - File/line: `wepppy/wepp/management/utils/multi_ofe.py:121`  
  - Disposition: `fixed`  
  - Resolution: Route single-stack writes through `_compact_yearly_scenarios()` and `setroot()` before serialization.
- No remaining unresolved findings from self-review after the fix above.
