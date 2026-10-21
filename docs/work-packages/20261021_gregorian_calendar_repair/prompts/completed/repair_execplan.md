# Repair the WEPP execution calendar

This living plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Implement the user's authorized repair of century drift and EOF reuse, diagnosed
in `20261021_ascii_pass_century_investigation`. Continuous climate, hillslope,
PASS and watershed dates must follow Gregorian dates with one consumed record
per simulated day. Demonstrate regenerated 200-year outputs and century tests.
This is a behavioral correction, not a modernization scaffold. No release or
live deployment is implied by locally validated source and candidate binaries.

## Progress

- [x] (2026-10-21) Read source instructions, repair design and retained diagnosis.
- [x] Establish calendar contract/ADR and preserve preexisting changes.
- [x] Implement shared Gregorian calendar, daily date validation and EOF checks.
- [x] Propagate explicit HBP policy compatibility without changing legacy meaning.
- [x] Validate released ASCII backport and current HBP paths with fresh outputs.
- [x] Run focused/broad native gates, correctness review then QA review (limitations retained).
- [x] Document results, residual risks and handoff status.

## Surprises & Discoveries

Focused real-reader/header tests pass (61); the replacement leap vector also passes, including final partial buffers, malformed
Fortran null/slash input and every ASCII header kind. PS05 passes with both schema
layouts, century boundaries and explicit legacy-policy inspection. Preliminary
ASCII replay caught a master-header format mismatch; the shared production helper
now owns the exact format and positive/negative tests cover it. Final builds and both full 200-year replays pass after that correction.


The current native checkout is HBP-only for production hillslope output. The
reported release is ASCII v3 at native commit 7471bb5. Both source lines require
validation; changing only one would leave an unsupported completion claim.

## Decision Log

2026-10-21: User explicitly authorized the previously identified repair. Use the
current native checkout for maintained implementation and an isolated release
archive for the ASCII backport, retaining a reviewable patch. Preserve earlier
schema-2 exact-date reader changes and all unrelated dirty work. No branch switch.
Use docs-maintainer tooling for documentation and native make/fpm/pytest gates.

## Outcomes & Retrospective

Implementation and source review pass. Full ASCII 200-year recovery, both 400-year
paths, 44-year unchanged-output comparison and observability parity pass. Gregorian
HBP downstream padding correction passes 109 Rust tests and 400-year generated
interchange validation. Full HBP 200-year replay, raw daily audit and downstream audit pass. Both full
project conversions contain 7,596,992 unique daily PASS keys; all date checks pass.
Native broad gates retain missing external fixture and preexisting cache failures.

## Context and Orientation

Native repository: `/workdir/wepp-forest`. Key files: `src/contin.for`,
`src/wshdrv.f90`, `src/wshpas.f90`, `src/stmget.for`, `src/wshred.for`,
`fpm-src/hillslope_binary_pass_{writer,reader,legacy_adapter}.f90`.
The released ASCII source uses `.for` for wshdrv/wshpas and has components v3
in `src/mixpass.for`. Original project is
`/wc1/runs/ch/chemotherapeutic-scope`, 104 hillslopes, years 1–200. Its climate
contains 73,048 Gregorian daily records; old PASS has 73,050. Runtime fails at
requested `(103,365)` versus stored `(102,365)`. Old stmget additionally reuses
saved weather at EOF. Source/policy details and proposed acceptance are in the
closed predecessor's `artifacts/repair-design.md`.

## Plan of Work

Milestone 1 establishes an authoritative Gregorian execution contract and ADR.
Introduce one pure calendar module and wire day counts and date checks into the
production loops/readers. Preserve scientific equations and single-storm behavior.
Track complete climate records explicitly, reject short/malformed daily input,
and keep requested dates independent of parsed values. Validate every ASCII
header, including quiet days, with contextual diagnostics.

Milestone 2 gives new HBP output a distinct Gregorian policy ID. Readers retain
explicit legacy offline access while runtime demands Gregorian compatibility.
Keep exact-date lookup from the prior fix. Validate both schema layouts and
policy rejection; fixed 366 directory slots are capacity, not extra simulation.

Milestone 3 builds both binaries and runs focused malformed-input/century tests.
Use supported project forks for full-context replay, regenerate all hillslopes
and watershed outputs from paired candidate binaries, and audit dates/forcing.
Use an isolated release backport to demonstrate the original ASCII failing path.
Use a compact 400-year case plus 1899/1900 and 1999/2000 boundaries. Compare
unaffected cases and pre-divergence output against matching baseline source.

Milestone 4 runs native gates and mandatory Fortran correctness/QA reviews,
updates authoritative docs/specs and this tracker, and retains small evidence.
Large generated artifacts stay under `/workdir/wepp-gregorian-repair-20261021`.

## Concrete Steps

Build `wepp` then `wepp_hill` sequentially (capacity includes are shared), using
`LDFLAGS="-mcmodel=medium -no-pie -lz"`. Prebuild the matching
`watbal_route_kernels.o` / `_hill.o` for the existing missing make prerequisite.
Use existing native `fpm test`, focused pytest and host-smoke tooling, recording
preexisting fixture/cache failures separately. Execute only isolated run folders.
Retain exact commands, hashes and generated-artifact audits in `artifacts/`.

## Validation and Acceptance

Require 73,048 daily records for years 1–200 and 146,097 for 1–400; exact
climate/PASS/water-balance/event date correspondence, no stale EOF payloads,
explicit malformed/missing/duplicate/out-of-order rejection, schema-1/schema-2
coverage and policy mismatch rejection. Require full configured actual-project
completion and fresh outputs, not only status banners. Regenerate downstream
interchange from corrected outputs. Source fix and local recovery are distinct
from deployment; do not claim the live project recovered without a supported
release and regeneration there.

## Idempotence and Recovery

Preserve preexisting native diff in the work directory. Never overwrite original
project data or vendored releases. Use distinct attempts; retain failed outputs.
Rollback is removal of this repair only, preserving prior fixes and dirty work.

## Artifacts and Notes

Baseline evidence resides in the closed investigation package. New build/test,
replay, review and compatibility evidence belongs here. Update tracker before
handoff; close only after all authorized implementation work is finished.

## Interfaces and Dependencies

Use Fortran modules with explicit interfaces and the existing make/fpm build
paths. No new external dependencies. Calendar-policy evolution is additive:
old IDs retain their meaning; runtime rejects incompatible inputs with guidance
to regenerate. ASCII format stays v3; validate dates rather than reinterpret them.

Revision: completed source/local recovery, 2026-10-21. No deployed release changed.

2026-10-21 downstream extension: generated 400-year HBP interchange contains 303
invalid non-leap day-366 rows because Rust exports schema-2 padding. Repair the
owned converter before closure. Compatibility plan: filter only explicitly tagged
`wepp-gregorian-v1` padding after validating its payload; retain historical-policy
conversion behavior and all columns. Regression plan: schema-2 ordinary/century
non-leap years, leap 400/2000, legacy preservation and corrupted-padding rejection;
rebuild only into an isolated Python package, then regenerate 200/400-year Parquet
and check row counts/dates. Do not replace deployed shared objects.
