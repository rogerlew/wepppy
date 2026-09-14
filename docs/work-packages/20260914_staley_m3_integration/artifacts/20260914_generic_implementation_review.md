# Generic local preparation and terrain increment

Date: 2026-09-14. Contract ancestor: `7328a0004`; scientific ancestor:
`89d673c38`. Status: local implementation under review, not production acceptance.

Final bounded checkpoints: replay contract `0792c7e59`, local implementation
`4b4e77733`. Both independent bounded reviews approve; production acceptance is
still open. Latest gates: 520 module tests, 41 results tests and 13 analytical/
mixed-source M3 tests pass. Stub completeness and six-file broad-exception delta
checks pass; package/module documentation lint reports no errors or warnings.
The full Python sweep passed 8,537 tests, skipped 103, in 953.04 seconds.
It collected before the latest M3/result additions; focused gates cover those.

## Evidence

Two independent local basin fixtures derive different MUKEY sets and native
THICK windows from the same generic catalog/source layout. No named-run branch,
network call, shared soil-builder edit or shared SQLite write was introduced.
Real owned WBT tests cover raw outlet relief, truncation, area mismatch and
equal-area wrong membership. The latter failed the initial implementation;
owned Watershed now verifies exact membership before terrain is declared valid.

Focused runs: 17 passed initially; independent corrected terrain/source review
19 passed; source/M1 regression 68 passed; source/terrain/initial M3 composition/
rainfall 49 passed. An incorrect rainfall test filename caused an initial
zero-collection command failure; corrected commands use
`test_postfire_debris_flow_rainfall.py`. Initial M3 tests also exposed an incorrect
test call signature; corrected rerun passed both composition cases.

## Review disposition

Correctness reviewer closes malformed MUKEYs (including outside-domain labels),
catalog/native-schema admission, and exact basin membership. Security reviewer
reproduced receipt parse/hash separation, late artifact stat baselines, unbounded
metadata retention, pathname rename escape, and post-callback NoDb failure after
commit. Corrections have been implemented; the security reviewer approves the
bounded local primitive. This approval excludes authoritative production binding.

File promotion now uses existing explicit locks without saving NoDb state. It
returns `status=committed` and named warnings for expected postcommit cleanup
errors, while precommit failures preserve the prior manifest. Tests cover no
save/notify, ownership loss, unlock cleanup, stale inputs, failed atomic rename,
artifact hash races and descriptor-based containment.

The latest source-promotion gate passes 16 tests. Expanded M3 cases cover zero
support, thickness above 254 cm (S greater than one), and re-pinned corrupt mask
or F values. The combined M1/M3 composition gate passes 61 tests. Retained native
membership, aligned SBS and unconditional authoritative domain extend the fixed
M3 inventory to twelve paths so archive readers can verify geometry, exact
support and F even with unavailable terrain. Both independent reviewers approve
the contract refinement; correctness review approves the local composition and
reader after twelve analytical cases and negative soil-hash/count probes.
Tests initially attempted an exclusive-create writer to rewrite
a fixture manifest; corrected fixture mutation now exercises reader rejection.

## Open gates

Production must resolve and bind authoritative Ron/Watershed sources through
promotion; project containment alone does not establish basin authority. M3
composition and version-2 reader have bounded approval; mixed-source regression
now passes and full production validation remains due. Worker/results/publication wiring,
browser/RQ/live multi-basin acceptance and full-suite completion remain open.
The completed full sweep started before the latest M3 test additions; retain
focused results separately. Live acquisition remains separately gated and has
not occurred.
