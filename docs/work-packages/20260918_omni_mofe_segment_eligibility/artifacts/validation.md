# Validation and review

Baseline: 37 focused tests passed before edits. New candidate regression failed
before implementation (missing candidate method). After implementation: 72 passed
across Omni selection, Treatments, MOFE soil modification and MOFE artifact tests.

Commands:

    wctl run-pytest tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_treatments_build.py tests/nodb/mods/disturbed/test_modify_soils_mofe.py tests/nodb/test_mofe_scenario_artifacts.py --maxfail=1
    wctl check-test-stubs
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref df504d8f6

Stubs and broad-exception enforcement passed; no new broad catch. Documentation
lint passed for package, canonical contract and Omni README/ENDUSER.

Artifact test `test_omni_mixed_segments_reach_combined_and_prepared_inputs` runs
the real Omni mode selection, treatment application, MOFE management synthesis
and WEPP management preparation. It parses `landuse/hill_101.mofe.man` and
`wepp/runs/p1.man`: the bare first OFE retains cover; the second changes from
forest to thinning/prescribed fire, or receives increased burned ground cover
for mulch. Assignment order and target keys are checked. Soils/controller
persistence are isolated in this test; the separate existing MOFE soil suite
passes. This is input-propagation evidence, not full-model output parity.

MOFE-specific orchestration tests verify channel exclusion, slope and burn masks,
all-ineligible no-op, and treatment of an eligible OFE under a bare scalar class
for all three scenario types. Missing/empty/malformed map and unknown management
failures are exercised; integer/string hill identifiers are covered.

Independent correctness review `eligibility_contract_review1`: no blocking
findings. Minor recommendations to qualify historical canonical PASS status
and add MOFE filter/channel evidence were both implemented.

Broad suite: interrupted (exit 137) by the user-requested local Forest restart;
no complete-suite pass claimed. Actual-project Forest release gate: pending
results from the authorized dispatch recorded in `forest_dispatch.md`.
No production deployment was performed.
