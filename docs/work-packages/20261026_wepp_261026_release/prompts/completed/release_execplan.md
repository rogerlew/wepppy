# Release WEPP 261026 with late-return metadata repair

## Purpose

Deliver a selectable paired 261026 release that routes previously untyped late
soil-return events through the established effective-support convention. Provide
reviewed scientific release notes derived from 261010, with inherited 261021
changes and fresh 261026 evidence clearly distinguished. No default switch or
production deployment is authorized. This is the completed plan for this release;
older physical-water and ablation plans retain their separate scope/history.

## Progress

- [x] Read release, native, documentation and test guidance; verify default branch.
- [x] Record ADR and durable source contract; promote exact reviewed U1 patch.
- [x] Add committed executable regression resources and source checkpoint.
- [x] Complete second whole watershed, production-equivalent replay and native gates.
- [x] Build paired 261026 from committed default-branch source; verify identities.
- [x] Vendor pair/sidecars and run compatibility, provenance, smoke and broad gates.
- [x] Re-version261010 report, add 261021/261026 coverage, review/render and freeze PDF.
- [x] Complete publication/navigation validation and release records/commits.

## Surprises & Discoveries

The following entries retain the chronological investigation; final outcomes below
supersede intermediate pending statuses.

2026-10-26: source checkpoint b73e93b19 and test/replay checkpoint d2f227244
are committed on the native default branch. Seven candidate regressions pass;
12 watchlist cases and both dated-profile smokes pass. Complete normalized ELF
files match reviewed U1 after removing debug/build-ID data only. Unpinned
Homebrew compiler caused channel-test SIGSEGV; required system compiler passes
all seven channel tests. Full pinned native suite is running. Retain failures.


The existing portable experiment passes 491 hills/211 channels for nine years.
Fresh same-host exact parity holds outside two SRC3 records. Archived production
versus host output differs in small values; paired H1 container tests attribute
that witness to runtime context. Do not relax parity tolerance. Second project
has only H394 source-level evidence so far and requires a complete paired replay.

2026-10-26: native 534 tests pass with system compiler; post-vendor compatibility
89 passed/1 skipped, both host/container smokes and provenance pass. Second
actual dated pair completes 491 hills/211 channels/3,288 days in production
worker container; three SRC3 changes only, 2,946 non-PASS files and legacy PASS
streams exact. Sixteen final Parquet files are finite; H.pass and watershed
PASS each contain 1,614,408 rows. Replay harness now mirrors `.out` promotion
and version-manifest ordering; initial omitted steps are retained as failures.

2026-10-26: broad canonical suite reached 2,460 passes/48 skips, then was
intentionally interrupted inside the slow Rosetta matrix. Complete 11,940-node
inventory is being accounted across four remaining soil-case segments and one
remainder segment. No exclusions or numeric tolerances were introduced.

## Decision Log

2026-10-26 — Owner approves narrow release with existing limitation after gates.
Retain midnight effective support rather than resurrect previously rejected
literal-hour forcing. No source timing, rainfall duration, peak/erosion, schema,
capacity, banner or default change. New tag 261026 preserves older versions.

2026-10-26 — Use canonical native checkout /workdir/wepp-forest-release-20261009,
branch resolved from origin/HEAD (wepp_260430_negmeltfix_comparator). Leave dirty
/workdir/wepp-forest HBP checkout and unrelated WEPPpy work unchanged. Commit
portable resources and model changes before recording release source identity.

## Context and work

Reviewed U1 patches are under native docs/ablation/20261026_redoubled-catmint_zero-duration/artifacts/diffs.
They change cmixprod.inc, mixpeak.for, contin.for, wshpas.for and mixpass.for:
reset a separate late-source flag daily; capture terminal hourly weights after
existing late WATBAL only when preceding runoff/duration and rain/melt/irrigation
are zero, continuous hourly mode, no contour and no existing MIX source; serialize
native runvol directly as return-only SRC3. MIXRETURN stays unchanged. Preserve
non-target outputs and test daily reset, invalid operands, source integration,
multi-OFE area, ordinary wet/dry controls and complete calendars.

Before source edits add ADR 0107 and native physical-water-routing contract section
with exact scope/rationale. Add regression which regenerates portable fixture
with candidate, asserts intended SRC3 and exact baseline non-target outputs when
paired binary available, and compiles native helpers against current source.
Retain diagnostic source patches and bad-baseline evidence. Commit source,
fixtures/tests and required docs on current default branch, no branch switching.

Run missing second full watershed in isolated wc1 storage, with all fresh passes
from the same candidate. Use same-context paired baseline for exact non-target
comparison; additionally exercise real container runtime and downstream parsing.
Capture original-run hashes and never modify originals. Validate all calendar
keys, source classification, volume/precision bounds, channel/output completeness
and finite fields; do not infer physical timing or universal conservation.

Run full native pytest, watchlist, both smokes, artifact policy and runtime
provenance. Build with TARGET_TAG=261026 COMPILER=/usr/bin/gfortran
 tools/build_wepp_dated_release.sh, sequential profiles. Sidecars must identify
committed default-branch source, capabilities, PASS v3, calendar and actual gates.
Use exact executable comparison or replay actual releases to link gate evidence.
Vendor paired sidecars atomically with finalized metadata, then binaries into
WEPPpy wepp_runner/bin. Required checks: tools/check_wepp_binary_provenance.sh,
host/container smokes, targeted runner/output and PASS v3/selection compatibility,
wctl run-pytest tests --maxfail=1. Retain any broad-suite environment failure;
resolve or explicitly account all nodes by reproducible segmented runs.

Copy 261010 report authoring assets into new native docs/release-notes/wepp_261026.
Rewrite identity, release scope, executive summary and operations; add substantive
261021 inherited repairs and261026 mechanism/evidence/limitations. Historical
Topanga/Cedar results remain labeled their actual builds, never relabeled as new
simulation. Keep source-free publication policy: no legacy listings/diffs/private
paths in served PDF/manifest. Scientific, implementation and disclosure reviews
cover final edition; compile without shell escape, inspect extracted text and
rendered pages, freeze hashes. Owner's current request authorizes the revised
release-note deliverable; retain exact approval scope and separate deployment.

## Validation and recovery

Use existing dependencies/tooling. Keep every gate log under package artifacts
or compact native incident records; full run trees stay in isolated wc1 storage.
If a gate fails, preserve its evidence and fix only within scope; no widened
tolerance/timeout, silent fallback, missing-node exclusion or fabricated pass.
Rollback is selecting prior paired binary and regenerating outputs, never mixing
passes. Do not change old report editions, source branches or unrelated work.

## Outcomes & Retrospective

Completed 2026-10-26. Native source b73e93b19 and release/artifact commit
8d89b0c194 are published on the verified default branch. Both binary profiles and
sidecars are vendored; native 534 tests, watchlist 12, compatibility 89 (one skip)
and selection 40 pass. All 11,941 collected WEPPpy nodes are accounted for:
11,791 passes, 150 test skips and one additional collection-module skip; no
unresolved failures. Retained failures document compiler context, stale expected
release lists, browser cache configuration and replay harness lifecycle ordering.

Both reported watersheds complete. Same-context parity holds outside intended
SRC3 records; all 16 downstream Parquet artifacts are finite. The 49-page,
13-figure cumulative report passes final science/implementation/disclosure
reviews, source freeze and downloaded-hash validation. PDF SHA256 is
57320794cd53e86cb0d4ce699f635042f5d52b306ca279cfaee33cf1220e3d2c.
See ../../artifacts/validation.md for gate scope and ../../artifacts/coverage-summary.json
for complete test accounting. ADR-0107 and the native physical-water-routing
contract retain the normative decision and rationale beyond this closed package.

The smallest source-metadata repair resolves both incidents without a new duration
rule. Midnight effective support remains an explicit limitation; actual subdaily
timing and universal conservation were not established. Production deployment,
default changes and unrelated work were excluded from this release.
