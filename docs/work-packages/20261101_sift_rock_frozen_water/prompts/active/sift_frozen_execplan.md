# Repair SIFT rock basis and investigate frozen-water mapping

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md. Maintain Progress, Surprises & Discoveries, Decision Log and Outcomes & Retrospective. Previous studies at234580e22 andd15d1470f are immutable evidence.

## Purpose / Big Picture

Make BC SIFT-generated WEPP soils carry dry fragment mass rather than mislabeled source volume, and determine where the native fine/coarse frozen-water exchange conserves or leaves residual water. The first is a production dimensional repair; the second is observation of unchanged source, not a proposed capacity formula. Completion requires actual emitted/native artifacts for the repair and source-bound full-routine outputs for the campaign.

## Progress

- [x] Read SIFT writer, prior source definitions, test guidance and FRWATC.
- [x] M1: independent contract reviews and ADR checkpoint before repair (6b08f3452).
- [x] M2: failing regression, conversion, actual three-soil builder and three complete native histories validated.
- [x] M3: reviewed complete-FRWATC 29-case campaign executed; 18 normal controls close, threshold findings retained. Independent scientific and implementation result reviews pass.
- [x] M4a: focused/broad verification and independent final reviews. Full suite: 12,634 passed, 423 skipped.
- [x] M4b: 480-member archive verified; final publication checkpoint prepared.

## Context and Orientation

wepppy/locales/canada/bc/soils/sift/sift.py consumes BCSLF COFRAG volume percent and BD fine-earth density in g/cm3, confirmed by official metadata in the prior source study. SiftHorizon.rfg directly returns COFRAG and its serializer writes that into native mass RFG. Existing wepppy/wepp/soils/rock_fragments.py provides the density-explicit conversion with mineral density2.65. Source sentinel-9 becomes None. SiftSoil rejects incomplete horizons through valid; keep this behavior for missing fraction or density. Present invalid fractions/densities must fail explicitly. Existing original JSON and commented summary preserve raw source values.

Native source is /workdir/wepp-forest-release-20261009/src. FRWATC exchanges fine frost-grid liquid/ice with coarse water-balance states in both directions. ST and FRZW are adjusted stocks; total coarse stock is ST+FRZW+THETDR*DG. Fine stock includes SLSIC, SLSW times unfrozen thickness, and NWFRZZ liquid in frozen support. Thresholds and carried shortages mean a coarse algebraic identity alone cannot prove conservative exchange. Prior17expression probes already reject an isolated UL reduction as sufficient; native drainage/capacity changes remain out of scope.

## Plan of Work

M1 specifies the SIFT conversion and None/-9 handling in the canonical rock-fragment-representation contract and ADR-0126. Record operator authority and independent scientific/implementation reviews before committing the contract ancestor. Keep all existing keys, raw JSON values, soil formatting, retention heuristics, native caps and200mm boundary. Add concise generated comments explaining units/density; no migration.

M2 writes deterministic failing tests for valid volume/density, zero/high rock, missing source values and invalid domains. Exercise actual SIFT builder/serializer using declared finite input records, not a fabricated deployed database. Correct rfg, necessary provenance and the confirmed writer blockers: replace undeclared comment formatter and include missing SAT0.75 under the amended ADR. Rebuild fresh fixture soils and execute their complete native input boundary using the retained pinned observer/runtime bundle. Include native mass cap behavior and explicit density/depth limitations. Preserve all inputs, failures, logs and outputs.

M3 declares exact unchanged FRWATC source and recursively required includes, pinned compiler and explicit initialized COMMON operands. Compile the complete routine with a small authored driver, retaining source privately. Review the declaration and driver before invocation. Exercise both directions, no/partial/full frost, frozen-zone liquid, positive/negative changes, dry-reference controls and supports around1mm. Compute independent pre/post fine and coarse stocks with signed residuals and branch ownership. Unexpected residuals remain findings; do not add tolerance/clipping or native code changes to hide them. No complete freeze-energy or coupled hydrology claim follows.

M4 uses wctl run-pytest for focused modules and the full tests --maxfail=1 gate, stub checks, changed-exception enforcement and scoped docs lint. Independent reviews verify production propagation and native interpretation separately. Freeze raw attempts under out/sift-rock-frozen-water-20261101, archive after writers clear, update this plan/tracker and commit on the current branches. No deployment or binary promotion.

## Compatibility and Regression Plan

Additive comments only; no project schema/key changes. Raw COFRAG/BD remain available and existing soils remain historical until explicit rebuild. Missing sentinels preserve incomplete-horizon behavior; invalid present numeric input fails explicitly. Other soil sources, open-water handling,200mm split and native caps remain unchanged. Validate complete generated soil tokens and actual native interpretation; unit tests alone are insufficient.

## Validation and Acceptance

Conversion cases must independently conserve dry mass and agree after serialization with native CPM under observed native density/caps. Whole-routine mapping cases must retain each invocation's pre/post stocks, expected external delta and unassigned residual, including counterexamples. Actual declarations will enumerate fixture domains and fixed numerical comparison bounds before execution. Full tests pass or receive an explicit independently reviewed failure disposition. Artifacts and existing study hashes must remain intact.

## Idempotence and Recovery

All attempts require fresh destinations; retain failed probes. No writes to historical runs or native source. Revert a production repair via its commit; never rewrite old evidence. Native wrappers/includes/objects remain private, with source-free public generators and receipts. No new dependency or infrastructure.

## Surprises & Discoveries

Actual SIFT mineral writer fails on undeclared prettytable in the canonical container; its header also lacks mandatory SAT. Contract/ADR amended for standard-library commented table and explicit established SAT0.75, with separate parser/native gates. No fallback or installed dependency. Full-routine fixtures show omitted sub-millimeter unfrozen support, loss of small frozen-zone liquid on repeated mapping, and ignored sub-micrometer increments. These remain observations, without invented runoff or ET. The first SIFT history verifier falsely flagged decorative report stars; preserve its failure and accept only the independently reviewed read-only v2 result, with all original files unchanged. The exception inventory uses line-number allowlisting: the new import shifted four unchanged handlers; update their coordinates and retain an unsuppressed 4-to-4 comparison.

## Decision Log

2026-11-01: operator approved proceeding with the SIFT repair plus reviewed frozen-water/drainage campaign. Keep independent acceptance because dimensional correction does not establish native physical closure.

## Outcomes & Retrospective

The actual builder emits 0, 33.8 and 89.1 dry mass percent for source volumes 0, 20 and 80 percent at BD 1.3. Focused verification passes 120 tests. The unchanged complete FRWATC campaign finishes all 29 cases, with 18 normal controls within the declared bound and five threshold fixtures showing discrepancies. This validates neither coupled frost dynamics nor a native correction. Three complete 16-year native histories pass independent mass/CPM/SAT/calendar checks. Both scientific and implementation reviews pass. The full suite passes 12,634 tests with 423 skipped. The 480-member archive is verified against its complete raw inventory; final publication captures this closure. Native source-free evidence is committed at add893ad6. The bounded phase is complete; no deployment or native correction is promoted.

## Concrete Steps and Evidence

Commands and exact private-runtime requirements are in artifacts/reproduce.md. Actual builder output is retained under out/sift-rock-frozen-water-20261101/sift-artifacts-v1; native processes under sift-native-v1; corrected read-only acceptance under sift-readback-v2; complete mapping probes under frozen-campaign-v1. Independent reviews bind each source and receipt identity. Focused tests pass 120; full tests finish successfully with 12,634 passed and 423 skipped. Archive creation follows final writer-clear checks.

## Retention and Follow-up

The private archive is /wc1/runs/ro/sift-rock-frozen-water-20261101/sift-rock-frozen-water-checkpoint.tar.gz, SHA-256 ca38bed2a5b4cda826ab35263f3dd973872dedd16354d86d4d502b73c26590c2. All 480 members and the complete raw tree match; prior 495-file and 353-file studies also remain intact. The raw publication snapshot precedes final archive/closure metadata, which are bound by the final Git publication manifest. The recommended follow-up in artifacts/next-study.md first measures threshold recurrence and residual ownership in complete histories; it is not an active physics-change plan.
