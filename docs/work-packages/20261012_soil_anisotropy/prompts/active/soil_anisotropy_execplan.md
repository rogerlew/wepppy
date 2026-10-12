# Add depth-specific soil anisotropy without another file pass

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md. Execute this package, not the earlier Portland package. The user authorized the feature and Rust implementation; existing session commit authority supports the required contract ancestor. Production deployment and push are excluded.

## Purpose / Big Picture

Users preparing MOFE models with hourly water balance/deep seepage can optionally override anisotropy for horizons above and below a 50 cm boundary. Blank settings preserve existing model inputs. UI and server enforce upper 1–100 and lower 1–10, with a numerical-instability warning above 10. Real generated soil files must demonstrate the values.

## Progress

- [x] Inspect Python soil preparation and sibling wepppyo3 repository.
- [x] M0: Finalize horizon semantics, canonical contract/ADR and two independent reviews; commit standalone checkpoint.
- [x] M1: Add and test Rust in-memory anisotropy kernel, rebuild affected native extension.
- [x] M2: Wire saved inputs, eligibility, single-read preparation and UI; add regression tests.
- [x] M3a: Validate generated files, source/read-write parity, live browser/API controls and independent implementation review.
- [x] M3b: Execute broad Python gate, investigate its unrelated timing failure, complete remaining coverage and retain final evidence with limitations.

## Surprises & Discoveries

Current advanced soil preparation is Python `WeppSoilUtil`, not Rust. Both `prep_soil` and `prep_multi_ofe_hillslope` mutate one object and write once, but symbolic values cause a second parse. Preserved uploaded native soils also read once for validation and again for parsing. Existing generated defaults use a different shallow-layer cutoff; the new optional 500 mm override must not change unset defaults.

A forest service restart exposed the required native startup SHA pin: the new binary was rejected until `docker/wepppyo3-interchange-preflight.py` was paired with its hash. The affected idle services were restored after updating the pin. This is part of the release, not a bypass. A template regression check also exposed an existing Jinja loop-scope bug dropping `extra_control_class`; the numeric macro now preserves that documented argument so project read-only applies. Independent review caught and closed upload error translation and concurrent read-only/hourly-toggle issues.

The full suite caught omitted supported-input catalog entries even though the runtime parser already accepted the fields. Both keys are now declared and the existing contract test passes. The disposable forest fixture has bounded synthetic terrain/climate descriptors, not a complete watershed: real invalid-input HTTP checks therefore use the shared prep-only handler; the Run request is intercepted only for serialization. Existing READONLY changes enqueue manifest jobs, so browser validation must wait for completion before reversing them.

## Decision Log

2026-10-12, operator/Codex: add optional controls with the requested ranges and MOFE/hourly eligibility. Keep defaults unchanged. Reuse the owned native extension and apply a narrow in-memory operation instead of porting the entire parser. Eliminate evidenced duplicate source reads without moving historical parameter formulas into a new implementation. Bottom-depth classification is the stated implementation assumption; no operator correction was received during discovery. It avoids changing layer geometry.

## Outcomes & Retrospective

Runtime candidate `e6004b118` and native `822b6fe` are implemented on forest. Contract ancestor `a94028e78` has both required reviews; final code/browser review has no open SA-01 findings. Actual generated two-OFE soils have 25/25/3 at 100/500/800 mm, unchanged source bytes and one source read/one destination write. Browser/API/download acceptance passes. Test-only commit `2da8e9298` additionally verifies crossing horizons without splitting (two passes after broad collection). The broad Python command recorded 10,461 passes/126 skips and one unchanged run-catalog latency failure (58.39 ms added p95 against 50 ms); the entire failed module and remaining files then passed (207 cases). The failure cause is unproven and the original gate is not represented as clean. Forest acceptance is complete with documented lint/typing/isolation limitations; no production deployment or push.

An additional bounded job executed the existing soil-preparation worker on forest's actual default RQ queue. Final output bytes equal direct preparation, and normal worker ownership/permissions and unchanged source are retained in `artifacts/rq-native-validation.json`. No new production enqueue site, queue dependency or model execution was introduced.

## Context and Orientation

WEPPpy `/home/workdir/wepppy` owns `wepppy/nodb/core/wepp_input_parser.py`, the `Wepp` facade/properties and task argument assembly in `wepp.py`, soil parser/writer in `wepppy/wepp/soils/utils/wepp_soil_util.py`, and the `wepp_pure_advanced_options/clip_soils_depth.htm` template plus `controllers_js/wepp.js`. `run_wepp_ui` controls the existing hourly WEPP marker. Native code lives in sibling `/home/workdir/wepppyo3`, crate `wepp_interchange`, deployed from `release/linux/py312/wepppyo3/wepp_interchange/`. Both repositories stay on their current branches; preserve unrelated edits.

## Plan of Work

M0 records SA-01 in docs/schemas/soil-anisotropy-contract.md and reconciles wepp-run-input and single-user-defined-inputs contracts. ADR-0088 records parameter provenance. Two independent read-only reviewers assess the checkpoint before its commit.

M1 adds a PyO3 function in the existing interchange crate accepting nested depths, original optional anisotropy, and optional upper/lower values. Rust validates all inputs and returns matching nested values; it never opens soil files. Unit tests cover exact boundaries and errors. Build for Python3.12 through existing release mechanics, atomically replace the shared object, record hashes and import the function from the real forest runtime.

M2 validates requests before mutating the locked Wepp object, adds omission-safe properties, and passes effective eligible overrides to MOFE preparation. Preserve existing preparation-time hourly override semantics. Apply native values after depth edits and before the sole write. Share source text between native validation and parsing and resolve symbolic values from the same source snapshot in memory with unchanged formulas/rounding. Add paired UI numeric fields and successful-toggle-driven eligibility. Test actual Jinja, controller interaction, locked persistence, original input preservation and actual generated outputs.

M3 exercises a disposable development run under normal identities, reads prepared soils and proves original hashes plus source-open/destination-write counts. Run focused Rust/Python/Jest checks, build controllers, then required broad tests. Retain existing baseline lint failures without claiming a pass. Review correctness and risks independently, update this plan/tracker and user/operator/native provenance docs. Do not claim deployed or scientifically stability-validated from unit tests.

## Concrete Steps

From wepppy use `wctl run-pytest` for affected NoDb/soil/template tests, `wctl run-npm test`, `wctl run-npm lint`, `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`, and `wctl run-pytest tests --maxfail=1`. Run docs lint and changed exception checks. From wepppyo3 run `cargo test -p wepp_interchange_rust`, format affected sources and build the module with the documented Python3.12 interpreter; atomic copy only after successful build. Record exact commands/results as executed.

## Validation and Acceptance

Persist upper 25 / lower 3, reload, prepare a real MOFE soil with depths 100/500/800 mm and read 25/25/3 from every OFE. Clear a field and verify original ratios return on rebuild, without changing source bytes. Ineligible UI cannot edit; API rejects active overrides; saved inactive values do not apply. Validate 100/10 endpoints, out-of-range and nonfinite failures, empty fields, a crossing layer, clipping and native-format preservation. Instrument the actual file boundary to prove one source open and one destination write per preparation; mocks of the writer alone do not count. Normal project browse can retrieve the resulting files.

## Idempotence and Recovery

Rebuild from immutable selected soils, never incrementally modify a previously prepared destination. Blank values restore source behavior on the next prep. Preserve state when controls are disabled. Roll back code and its matching native extension together; no run migration or source rewrite is necessary. Work only on disposable validation copies and do not alter production runs.

## Artifacts and Notes

Retain reviews, source/build hashes, test receipts, generated files and comparisons under this package's artifacts. Do not retain credentials. Native and Python commits must identify each other in handoff notes.

## Interfaces and Dependencies

No new dependencies. `wepppyo3.wepp_interchange` exposes the narrow Rust transform; `WeppSoilUtil` owns parsed objects and existing serialization. The `Wepp` facade owns saved override values and eligibility. Existing authorization/CSRF/RQ responses and NoDb persistence remain unchanged.
