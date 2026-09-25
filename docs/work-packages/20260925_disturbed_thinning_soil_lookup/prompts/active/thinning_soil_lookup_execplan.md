# Correct thinning soil lookup and verify mulch

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Thinning scenarios must consume their existing Disturbed soil lookup parameters.
The reported wepp1 choice-feminist `thinning_30_90/wepp/runs/p10.sol` contains
forest conductivity and erodibility because its variant class misses the generic
thinning row. Fix any `thinning` prefix, and prove mulch retains fire severity.

## Progress

- [x] 2026-09-25 UTC: diagnose, scope and draft canonical contract/ADR/package.
- [ ] Review and commit contract checkpoint before implementation.
- [ ] Demonstrate failing soil regressions; implement minimal soil lookup selection fix.
- [ ] Validate generated and prepared soils, mulch matrix and broad suite.
- [ ] Complete independent correctness/QA review and document release limitations.

## Surprises & Discoveries

The shared helper leaves thinning variants unchanged; both soil generation paths
use it. A separate management-parameter path has its own thinning normalization,
which did not protect soil generation. MOFE 9002 fallback inserts zero recovery
metadata; missed conductivity and erodibility replacements have physical impact.
Fortran 9002 ignores recovery metadata; do not confuse that with no impact.

## Decision Log

2026-09-25, operator/Codex: use case-sensitive startswith thinning, preserve
suffix-based mulch burned classes. This matches explicit operator intent and
avoids duplicating lookup rows. No production deployment or repair is inferred.

## Outcomes & Retrospective

Pending execution. Completion must distinguish local validation from release,
deployment and repair. Management tests alone did not establish soil correctness.

## Context and Orientation

`wepppy/nodb/mods/disturbed/disturbed.py:lookup_disturbed_class` supplies lookup
keys to `modify_soil` and `_modify_mofe_soils_impl`. MOFE means multiple overland
flow elements on a hillslope. The latter converts component soil files then uses
`SoilMultipleOfeSynth`; WEPP preparation consumes the resulting combined file.
The lookup CSV is keyed by vegetation/disturbance and texture. Mulch is represented
as burned base class plus `-mulch_15`, `-mulch_30` or `-mulch_60`.

## Plan of Work

Milestone 1: finish two independent read-only contract reviews, disposition findings,
commit only contract/ADR/checkpoint/package docs as an ancestor. The user explicitly
requested execution; continue through the remaining milestones autonomously.

Milestone 2: add resolver and artifact regressions under
`tests/nodb/mods/disturbed/`. Run the new thinning cases before changing code.
Insert the prefix rule in both existing soil lookup sites without refactoring other
branches. Preserve None and empty behavior and supported mulch suffixes.

Milestone 3: read actual converted, combined and prepared soils. Verify current
catalog thinning and a custom prefix, all nine burned vegetation/severity bases
for all three mulch levels, and meaningful format coverage. Reuse fixtures and
actual writer/prepare functions; doubles may isolate unrelated controllers only.
Run focused suites then `wctl run-pytest tests --maxfail=1`. Record any environmental
blockers precisely. Inspect the actual-project validation workflow and record
its result or remaining release gate without touching the production source run.

Milestone 4: independent correctness/QA review; close findings. Update user/operator
and developer docs, package/tracker and PROJECT_TRACKER. Move this plan to completed
with an honest outcome when code-delivery scope is complete.

## Concrete Steps

Work in `/home/workdir/wepppy`, current branch. Read tests/AGENTS.md and nearest
NoDb guidance. Use `wctl run-pytest tests/nodb/mods/disturbed -q` for focused
validation, then the broad suite. Run doc-lint on changed Markdown and broad
exception enforcement for changed Python. Preserve unrelated dirty files.

## Validation and Acceptance

For the incident loam row, expect `kr=4e-5`, upper-200-mm conductivity 40 mm/h,
and 9002 metadata 1.3/0.3 in all generated and prepared OFEs. Mulch must equal
its burned base soil row; verify parameter equality rather than forced output
differences. Keep supported misses and explicit soil overrides unchanged.
Locally validated is the maximum claim until isolated actual-project evidence
for the exact candidate exists. Model outputs and production repair remain
unverified until supported rebuild/rerun and report readback.

## Idempotence and Recovery

Tests use temporary directories. Do not hand-edit production derived files.
Repeated modifiers may reuse existing keys; supported rebuild must reset derived
soil state. Revert the bounded soil lookup commit to roll back code, with separate
input/result rebuild if deployed. No schema migration or new infrastructure.

## Artifacts and Notes

Retain focused/broad results and independent review dispositions in `artifacts/`.
Record hashes and semantic values for any actual-project evidence. Do not retain
large unrelated data or secrets.

## Interfaces and Dependencies

Preserve the existing Optional[str] resolver signature and every public API.
No added dependencies. Reuse WeppSoilUtil and SoilMultipleOfeSynth.
