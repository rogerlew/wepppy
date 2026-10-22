# Reissue WEPP 261021 with detailed scientific release notes

This living plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture


Replace the undeployed 261021 binary pair in WEPPpy with validated native
physical-water repairs and explain every shipped defect/fix, the watershed
audit and its limits in an illustrated technical report. Source is
`/workdir/wepp-forest-release-20261009`, default branch
`wepp_260430_negmeltfix_comparator`, d354e3c99. Coordination/vendor repository
is `/home/workdir/wepppy`. Compare source changes against 261010 source 7471bb5;
retain original 261021 a87925df9 as the superseded edition. No deployment,
default switch, MC authority change or full physical closure is implied.

## Progress


- [x] Operator authorized same-name reissue; branch/source verified and old artifacts archived.
- [x] M1 canonical dated build and exact executable-equivalence assessment.
- [x] M2 native full suite, watchlist, smokes, provenance and artifact-policy gates.
- [x] M3 complete sidecars/changelogs; paired vendoring and WEPPpy validation.
- [x] M4 detailed change register, defect figures, audit narrative and compiled PDF.
- [x] M5 scientific/implementation/disclosure reviews; final artifact hashes and handoff.

## Surprises & Discoveries


Fresh binaries match the validated candidate in all 26 allocated ELF sections
(excluding GNU build ID), independently verified. Both smokes, 12-case watchlist
and artifact policy pass; full native suite passes 527 tests with two existing warnings (718.13 s).

The first 261021 fixed calendar defects only; the new source adds bounded soil,
source, publication and retained-state repairs. Cedar demonstrates small annual
flood changes but material relative low-flow differences. Signed soil/routing
withdrawal remains open. Do not present a reissue as universal conservation.

## Decision Log


2026-10-21 — User explicitly supersedes the old no-overwrite scope for the
undeployed261021 pair. Keep historical hashes and notes, preserve closed packages,
and identify the new sidecars as artifact revision 2. No silent same-name pairing:
matching SHA/source identity and full hillslope regeneration are required.

2026-10-21 — Use existing native release tooling; preserve banner, capacities,
ASCII PASS v3 and reader declarations. Detailed release-note policy permits
independently written equations and defect diagrams, not raw legacy source.
Public PDF handoff remains distinct from preparing the review edition.

## Outcomes & Retrospective


Reissue and approved report publication are complete. Source d354e3c99 is
vendored as artifact revision 2; old identities are retained. Fresh native 527,
watchlist 12, post-vendor 21, host/container smokes and provenance pass. Segmented
WEPPpy coverage accounts for all 11173 nodes (11052 unique passes/122 skips).
The combined feature-access Redis failure is retained; isolated 52 and final 258
pass without application/auth changes. The 24-page/nine-figure report is owner
approved, frozen and published with verified local HTTP navigation/download.
The physical-water package remains open for signed acceptance/clipping.
Final release commits/push follow these completed gates; no deploy/default switch.

## Context and Orientation


Native `tools/build_wepp_dated_release.sh` builds profiles sequentially and
writes release binaries/sidecars. `wepp_runner/AGENTS.md` defines WEPPpy gates.
Native `docs/release-notes/AUTHORING.md` defines detailed technical coverage,
TeX/PDF review and publication boundaries. Report target is
`docs/release-notes/wepp_261021/` in native source. Existing public261010 PDFs
remain untouched. Experiment root is `/workdir/wepp-261021-rerelease-20261021`.

## Milestones and concrete steps


M1: archive previous261021 artifacts, then in native checkout run
`TARGET_TAG=261021 COMPILER=/usr/bin/gfortran tools/build_wepp_dated_release.sh`.
Record compiler, source and binary hashes. Restore only profile includes altered
by sequential builds to committed watershed profile; no capacity changes.
Compare stripped executables to the validated d354e3c99 candidate used for Cedar.
Executable identity permits carrying forward its same-build replay evidence;
otherwise rerun representative generated artifacts on the release pair.

M2: run full native pytest with WEPP_GUARDED_BINARY set to the newly built
release; both host smokes, 12-case watchlist, artifact policy and ELF checks.
Keep the 100-year timeout unchanged. All gates must pass before vendoring.

M3: finalize sidecars with revision 2, superseded identities, current source,
unchanged features/reader contracts, actual gate evidence and limitations.
Update native changelog, release notes/validation and WEPPpy binary lifecycle.
Stage complete binary/sidecar files before replacing both profiles; use atomic
sidecar replacement. Then run WEPPpy provenance, host/container smokes and
`wctl run-pytest tests/wepp_runner/test_run_hillslope_retries.py tests/wepp/test_wepp_runner_outputs.py tests/nodb/test_wepp_binary_policy.py`.
Run substantive pre-handoff `wctl run-pytest tests --maxfail=1`; preserve failures
and isolate confirmed environmental/order problems without changing application
behavior. Source default inventories are unchanged by same-name replacement.

M4: reconcile change-register.csv against7471bb5..d354e3c99; describe calendar,
EOF/keys, groundwater area, hourly remainder, flat sources, local/deferred
sources, MC publication and retained-state/reference/fixed-point repairs,
working-flux alias, audit Dp/ET/Q/QOFE/lateral conventions and unresolved exchange.
Distinguish schema2 HBP investigation and CLIGEN checks from shipped ASCII code.
Generate reproducible labeled defect figures and include Cedar adverse cases.
Use verified primary citations and retained quantitative evidence. Compile
TeX twice without shell escape; check text, references, overflows, metadata and
rendered pages. Do not copy unapproved drafts to public static paths.

M5: independent implementation/scientific review plus disclosure inspection;
resolve factual/coverage problems, retain review identities and residual limits.
Verify artifact hashes, docs lint and source-scoped diff checks. Commit bounded
release artifacts/docs; push per native release checklist after gates. Do not
rewrite remote tags or deploy. Handoff exact binaries/source, gates, report PDF
and any remaining public-PDF approval requirement after presenting the artifact.

## Validation and acceptance


Release pair must execute correctly with matching fresh PASS files, retain
ASCII schema3 and Gregorian dates, match reviewed source and pass native gates.
WEPPpy must discover and execute the reissued pair with unchanged defaults.
Report must cover every shipped change and display actual defect/audit figures;
no fabricated experiments or physical closure claims. Preserve old release
hashes and unfinished scientific work. Existing 527 native tests and Cedar evidence
are baseline expectations, not substitutes for the release's final gate run.

## Recovery and interfaces


Rollback by restoring both original binaries and sidecars from the retained
superseded archive (also in Git history), then regenerating outputs with that
paired identity. Do not reuse mixed-generation passes. No new dependency,
service, endpoint or output schema. Build artifacts/logs stay under the evidence
root; compact receipts and reviewed report source remain tracked.

Initial plan authored2026-10-21 for the explicit same-name reissue instruction.

2026-10-21 — Final review edition has 24 pages/nine original figures; independent
review finds no numerical/scientific blocker. Fresh native 527 and post-vendor
21 scoped tests pass; both profiles pass host/container smoke and provenance.
Broad WEPPpy suite remains running. PDF owner publication approval is distinct
from completing the requested report preparation.

2026-10-21 — Owner explicitly approved completed report publication. Final
revision 1 changes only publication-status/editorial labels; scientific content
and nine figures match the reviewed edition. Paired PDF/public manifest are
vendored and local HTTP download/navigation/hash checks pass.

2026-10-21 — Broad WEPPpy run was intentionally interrupted after 2434 passes/
48 skips (661.49s) in the slow 230-case soil block. Collected 11173 nodes; retain
completed-module coverage, run soil in four wctl shards and resume remaining
modules with per-node report logs. Initial report path was outside the container
mount and failed before executing tests; retry uses the mounted pytest cache.
No application/environment persistence changes or raised test limits.
