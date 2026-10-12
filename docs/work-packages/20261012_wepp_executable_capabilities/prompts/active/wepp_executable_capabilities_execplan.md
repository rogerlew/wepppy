# Let Config Builder projects select current compatible WEPP releases

This living plan follows docs/prompt_templates/codex_exec_plans.md. It implements CBEXEC-01 in the existing WEPPpy master and wepp-forest default branches. Operator instructions authorize executable flexibility, sidecar capability declarations, reminting 260803/261010 and vendoring. Existing session commit authority applies. Production deployment and automatic model reruns are excluded.

## Purpose / Big Picture

A user can create a MOFE project with 261010 and change an existing Builder project's WEPP executable to a newly installed compatible release without recreating or refreshing project configuration. MOFE means multiple overland-flow elements per hillslope. Explicit release-sidecar capabilities replace release-name pins; creation-time config remains provenance for the original choice.

## Progress

- [x] Trace registry, graph validation, run-page selector, input parsing, RQ admission and schemas; locate default-branch native worktree.
- [ ] Ratify canonical amendments with two independent contract reviews and standalone ancestor commit.
- [ ] Update native generator/remint four sidecars; validate metadata preservation and binary hashes, vendor identical sidecars.
- [ ] Wire shared live executable policy through Builder, run controls, submission and schemas; preserve stored graph readability.
- [ ] Complete targeted, broad and live artifact validation plus independent correctness/security review; retain handoff.

## Surprises & Discoveries

Builder already discovers current installed binaries. Its MOFE profile and graph validator still require exactly 260803. Existing projects render and validate against saved binary axes/tuples. Single-file upload projects have an additional native-reader pin. The main wepp-forest checkout is dirty on an unrelated branch; its existing default-branch worktree is clean and matches remote HEAD. The default generator has no metadata-refresh mode and would overwrite build provenance if simply rerun.

## Decision Log

2026-10-12, operator/Codex: keep default executable 260803 and saved choices unchanged; enable explicit selection of compatible installed releases. Store MOFE support in release sidecars as requested, rather than infer it from date-shaped names. Include upload-project flexibility with its own capability declaration and native-reader acceptance (optional narrower-scope question unanswered at drafting). Keep geometry, input-format and feature exclusions unchanged. No Fortran rebuild is needed for a metadata-only remint.

## Outcomes & Retrospective

Pending implementation. No capability or runtime claim is yet validated.

## Context and Orientation

wepp-forest tools/generate_wepp_release_sidecar.py and tools/build_wepp_dated_release.sh own minting; release/wepp_260803*.json and release/wepp_261010*.json identify unchanged executable bytes. WEPPpy wepp_runner owns installed executable discovery and paired-role selection. wepppy/nodb/config_builder/{registry,resolver}.py compose configs; locales/capability_graph.py validates persisted graphs; single_input_policy.py gates uploaded sources. routes/run_0/run_0_bp.py renders the run selector, core/wepp_input_parser.py persists the choice, and rq_engine/{wepp_run_payload,schema_defaults_routes}.py enforce and describe submission. Builder JS currently forces upload projects to260803.

## Plan of Work

M0 updates current contracts before implementation, records operator approval and high security scope, obtains two independent reviews and commits their accepted checkpoint. M1 adds strict explicit boolean sidecar capabilities and metadata-refresh mode, tests preservation/mismatch rejection, remints both roles of both existing releases on the default branch, records hashes and vendors metadata only. M2 shares live provider capability decisions without rewriting project config; updates graph construction and historical graph validation, removes binary-name pins and updates UI/API descriptions consistently. New selections must be installed provider IDs; unknown/path-like values fail before mutation. M3 proves real selection/save/reload on a disposable old Builder project, creates a261010 MOFE config, exercises actual prepared inputs and native multi-OFE output, runs required regression suites and records remaining limitations. Independent reviews must verify valid older projects still work and invalid selections cannot become executable paths.

## Concrete Steps

Run forest generator tests with its default-branch Python environment. Use wctl run-pytest for affected runner, Builder, capability, upload, route and RQ tests, then wctl run-pytest tests --maxfail=1. Run wctl run-npm test and lint after controller changes; rebuild through wctl exec weppcloud python /workdir/wepppy/wepppy/weppcloud/controllers_js/build_controllers_js.py. Use wctl doc-lint for changed docs. Keep long-suite logs in /tmp and retain concise results under artifacts. Inspect installed controller/worker health before and after authorized forest refreshes.

## Validation and Acceptance

Sidecar remint changes declared capability fields only and preserves SHA, source branch/commit, build time, PASS flags and prior validation. Reject malformed booleans, role disagreements and binary/sidecar hash mismatches. Missing capability is unknown, not inferred from names; single-OFE legacy availability is preserved. Test both old graph shapes and newly generated tuples without consulting current releases while parsing saved config. New live choices appear in browser and schema; selecting261010 survives NoDb reload and reaches runner identity under normal development service credentials. Native uploaded soil-format coverage is required before declaring upload support. No scientific stability guarantee is inferred from feature support.

## Compatibility, Idempotence and Recovery

No config migration or automatic default change. Read legacy graph tuples and preserve original config/manifests/hashes. Runtime executable selection remains in wepp.nodb and follows existing lock/cache handling. Old already-selected executables lacking declarations remain displayed as current legacy state; do not silently replace them. Explicit unsupported new choices fail. Remint verifies immutable identity first and can repeat deterministically. Roll back paired UI/policy and sidecars together; do not mutate production runs.

## Artifacts and Notes

Retain contract review, native-remint receipt, focused/full test results, browser and real output receipts, and final correctness/security artifacts. Do not retain credentials. Native/default and WEPPpy revision pairs belong in final handoff.

## Interfaces and Dependencies

Use the existing installed executable provider and paired-role resolver. A bounded shared helper returns boolean release capabilities and compatible IDs; no filesystem path is accepted from browser input. Saved project capabilities remain authoritative for non-binary axes and backend/representation geometry. Sidecar metadata and effective compatibility must participate in live registry identity and schema freshness.
