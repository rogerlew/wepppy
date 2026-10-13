# Correctness and User-Experience Review — CBEXEC-01

## Metadata

- Reviewer: independent `contract_correctness` agent; final assessment 2026-10-13 01:00 UTC.
- Scope: paired release capabilities, native metadata refresh, Builder registry/graph/resolver/controller, existing-project policy, run-page choices, parser/RQ admission and discovery metadata. No implementation edits by this reviewer.
- Context: WEPPpy implementation `3c114719b`, following accepted contract checkpoint `b4c950ced`; native default-branch implementation `917265bb5`.
- Authority: `docs/schemas/wepp-executable-selection-contract.md`, particularly “Release declarations” and “Builder and existing projects”; amended project-owned, run-input and Single User-Defined contracts.
- Related reviews: `2026-10-12_contract_security_review.md` and `2026-10-12_security_review.md`. Security reports no unresolved implementation findings.

## User Outcome

Users can explicitly select compatible installed releases, including 261010, for new or existing Builder projects. MOFE and uploaded native inputs require their separate declared capabilities. Default 260803 and saved project configuration remain unchanged. An unavailable saved executable remains visible as legacy state; explicit incompatible changes fail before persistence or enqueue. Invalid release metadata produces an explicit diagnostic rather than inventing support.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Sidecars absent | Yes, legacy | Ordinary Single-OFE choices remain; no inferred optional support | Actual temporary-file reader tests pass |
| No declared MOFE support | Yes | Ordinary creation works, geometry identity retained, no MOFE tuples | Actual graph validation and historical structure-payload parity test pass |
| Populated matching declarations | Yes | Eligible choices track both role sidecars and actual hashes | Actual sidecar tests and four installed release comparisons pass |
| Old Builder graph omits 261010 | Yes | New compatible choice persists without config/manifest migration | Real materialized old project, locked parser and detached reload test pass |
| Saved upload executable lacks new declarations | Yes | Omission and exact current value preserve existing behavior | Actual parser/persistence regression passes |
| Schema-v1 geometry restrictions | Yes | Expand only binary population; preserve backend/representation restrictions | Direct shared-policy test and reported explicit persisted-v1 parser regression pass |
| MOFE-only release plus separate upload-only release | Yes | Upload toggle resolves a visible valid tuple without emptying selectors | Actual Builder DOM/controller Jest regression passes |
| No certified upload release | Yes | Preserve recoverable controls; server rejects unsupported creation | Builder DOM recovery test passes; live empty-provider error case not exercised |
| Malformed flags, mismatched roles/source, stale hashes, hostile IDs | No | Explicit rejection before unsupported selection or path resolution | Real sidecar and parser rejection tests pass |

These cover the reported regressions and principal state dimensions, not every combination of locale, project age and executable.

## User-Reachable Error Policy

| Condition | Classification | Result and rationale |
| --- | --- | --- |
| Missing optional declaration | Expected | Filter feature-dependent new choices, preserve ordinary and unchanged legacy behavior |
| Unsupported explicit executable or scalar blank | Expected validation | Existing canonical validation response; reject before changing NoDb |
| Unknown/path-like Builder executable | Expected validation | Field-specific `wepp_binary` error |
| Sidecar changes after Builder description | Expected conflict | Registry revision changes; existing stale-schema workflow applies |
| Corrupt or contradictory release metadata | Exceptional installation state | Explicit failure; no silent fallback |

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Evidence | Result |
| --- | --- | --- | --- |
| User intent | Explicit newer release and compatible geometry | `browser-validation.json`: authenticated Builder default 260803, explicit 261010/MOFE creation, upload-toggle validation | Pass |
| Reloaded state | 261010 saved; original config and manifest bytes preserved | Real old-project parser test; `selected-execution-validation.json` and driver: production grouped handler saves 260803 then 261010, detached reload and both hashes preserved | Pass |
| Release provenance | Only two new declarations change; all original metadata and executable bytes preserved | Independent comparison of four sidecars against `b4c950ced`, actual SHA readback, native/vendor byte equality; `sidecar-remint.json` | Pass |
| Prepared native input | Source formats and OFE counts preserved through actual preparation | `validate_native_inputs.py`, `native-input-validation.json`: both releases, five soil formats, 1/2/32 OFEs | Retained 30-case pass |
| Execution output | Real selected release consumes prepared MOFE inputs | `selected-execution-validation.json`: default RQ worker runs real `run_hillslope`, two OFEs, matching 261010 identity, finite 10,081-byte output, UID 1000/GID 993, mode 0644 | Bounded hillslope pass |
| User-facing result | Choices, schema, persisted selection and normal result access agree | `browser-validation.json`, `browser-artifact-readback.json`: matching options/schema, hostile API 400 and unchanged reload, authenticated prepared/output downloads with matching hashes and runner identity | Pass |
| Archive/restore | Selection, original config and prepared/output bytes survive normal archive workflow | `archive-restore-validation.json`: canonical authenticated jobs, downloaded ZIP hash, restored four-file hashes and 261010 selector | Pass |

The independent review reran `wctl run-pytest tests/nodb/test_wepp_binary_policy.py tests/wepp_runner/test_binary_capabilities.py --maxfail=1`: **30 passed**, 2 warnings, 24.00 seconds. The first attempt was interrupted by the authorized service refresh (exit 137, no pytest result); it is not counted as validation. Actual Builder Jest: **23 passed**. No mocks replace the parser, lock, detached reload, sidecar bytes or DOM dependency controller in those respective tests. The old-project fixture limits provider discovery only while constructing its historical config; normal installed release policy runs afterward.

Validation receipts: final targeted 209 including template renders; final policy/schema/registry 149; final complete runner group 59; full Jest 972 across 118 suites; successful Builder schema stubtest; native full suite 171 before the final source-identity addition and final native generator 9/9 after that change. The earlier API/parser run had 344 passes plus one test-fixture failure, subsequently closed by the targeted run; it is not counted as an earlier complete pass. Repository npm lint retains the unchanged `climate.test.js:300` conditional-expect failure and is not a passing gate.

The broad Python command stopped with **1 failed, 4,838 passed, 51 skipped**, 1,938 warnings in 2,184.27 seconds. `test_model_tuple_matrix_covers_every_advertised_value_without_cross_product` constructed a graph without declaring MOFE support while asserting the 260803 MOFE tuple. The bounded test-only correction supplies `wepp_binary_capabilities={"wepp_260803": ("mofe_supported",)}`; all existing assertions remain unchanged. This fixture correction conforms to CBEXEC-01 and does not weaken zero-declaration behavior, covered separately. The first full-module retry reached 70 passes and exposed a second stale assertion requiring explicit schema-v1 rejection. Its correction asserts both no inferred v2/v3 graph (`None`) and preservation of the v1 coarse climate restriction. Both test corrections are approved; runtime is unchanged. The final entire module passed **75 tests**, 2 warnings in 15.75 seconds (`/tmp/cbexec-locale-final2.log`). The original broad command is not a clean pass.

The first remaining-suite command explicitly named 402 modules. It stopped with **1 failed, 3,108 passed, 69 skipped**, 3,517 warnings in 439.86 seconds at `test_derive_flow_stack_with_real_wbt_supports_blc_controls`, raising `WbtConditioningDiagnosticsError` for inconsistent diagnostics. The reviewer confirmed `_require_wbt_integration` opts this native test in when its filename is an invocation argument; ordinary `pytest tests` skips it unless the explicit environment flag is enabled. Thus the continuation accidentally enlarged the normal broad gate. There are no terrain implementation or test changes against `b4c950ced`. This is a retained observed failure of optional native validation, not a corrected defect or a clean pass; no unrelated terrain fix is included.

The corrected continuation uses `pytest tests --ignore=<completed module> ... --maxfail=1`, preserving the normal broad invocation/skip policy. Independent comparison against the 10,827-node, 694-module collection proves it ignores exactly the first 504 completed modules and retains all 190 modules starting with the WBT integration module. The initial 504-file exclusion form was interrupted during collection after 240.74 seconds; it supplies no passing-test evidence. The equivalent compact form uses 47 directory/file exclusions. The reviewer independently verified that it selects exactly the same 190 modules and 2,796 nodes. Its completed receipt (`/tmp/cbexec-tail3-pytest.log`) is **2,792 passed, 4 skipped**, 59 warnings in 295.83 seconds. No outstanding test is excluded solely because it failed.

The final disposition accepts these overlapping segments as completed normal broad-suite coverage, with the two contract-conformance test corrections passing and no outstanding CBEXEC failure. They are not summed into a unique pass count and are not represented as one clean full-suite command. The accidentally enabled optional WBT failure and pre-existing npm lint failure remain unresolved, disclosed limitations. No runtime changed after `3c114719b`; the two approved locale test corrections are the only later executable-test changes relevant to this disposition.

The retained execution driver and verifier were inspected. They invoke the actual grouped payload handler and preparation code, enqueue the existing runner on the normal default worker, parse prepared soil and output, inspect actual runner stderr, and recheck saved state and original config hashes. Inputs are a reproducible fixture copied into the disposable browser-created project; this is not a full watershed simulation or a production project rerun. No executable bytes changed, so this bounded acceptance does not require inventing a full-watershed success claim. When users change releases, the existing requirement to rerun hillslopes and watershed together still applies.

## Review Checks and QA Assessment

- Canonical intent and the uploaded-input expansion assumption are explicit; default, geometry, exclusions and source formats are preserved.
- Old graph parsing remains independent of live sidecars. Structural geometry identity and actual executable tuple admission remain distinct, with hostile TOPAZ/MOFE rejection covered.
- Shared selection policy avoids independent release-name allowlists across UI, parser and RQ. Existing lock/save boundaries remain in use; no queue wiring, permission or execution topology changes were added.
- The findings below were concrete compatibility or provenance defects; the corrected tests exercise their failure boundaries rather than merely asserting implementation tokens.
- Runtime metadata presentation tests stub `_load_runtime_state`; the retained live response independently closes that gap for the normal new MOFE project. It contains both Single-OFE backend populations, exactly the two declared WBT/MOFE releases, and a live executable revision. Metadata-only revision tests separately cover feature and binary changes.
- The final `_effective_model_binaries` fallback preserves `graph.wepp_binaries` ordering when live tuples are absent. This restores the original metadata order for unaffected paths and does not change live selection or admission. Final scoped retest: 149 passed.
- The binary-identity cache now includes `st_ctime_ns` alongside device, inode, size and mtime. The retained failing-before regression changes actual executable bytes in place, preserves size and restores mtime; the old cache wrongly trusted the sidecar. The one-line correction forces a new hash and rejects the stale declaration. The final 59-test runner group passes. This preserves existing runner trace fields and does not claim transactional protection against concurrent operator writes.
- Complexity is bounded to one release helper and one project policy. Repeated live sidecar reads favor freshness; no measured performance defect was identified in this review.
- No numerical-stability guarantee follows from executable capability declarations or the native fixture matrix.

## Findings

| ID | Severity | Surface and finding | Correction/evidence | Status |
| --- | --- | --- | --- | --- |
| CBEXEC-I01 | Medium | `single_input_policy.py`: second upload guard rejected unchanged legacy choices, including preparation | Require reader certification only for explicit changed selection; actual omission/current parser regression passes | Resolved |
| CBEXEC-I02 | Medium | `schema_defaults_routes.py`: only current geometry tuples were emitted alongside full axes/defaults | Generate live tuples across stored geometry; current-field enum remains filtered; live browser response verifies full tuples and distinct executable revision | Resolved |
| CBEXEC-I03 | Medium | `wepp_binary_policy.py`: scalar blank bypassed admission and could persist empty executable | Only omission/current bypass; real parser rejects scalar blank without changing NoDb; blank list preserves prior normalization | Resolved |
| CBEXEC-I04 | Medium | Project policy: schema-v1 geometry restrictions were skipped | Validate coarse v1 backend/representation axes and WBT/MOFE rule; `capability_authority` returns documented `None` for v1 | Resolved |
| CBEXEC-I05 | Medium | `config_builder.js`: upload toggle could empty backend, representation and executable selectors | Choose a compatible tuple before dependency filtering; retain controls for no-certified-upload case; both actual DOM regressions pass | Resolved |
| CBEXEC-I06 | Low | Native generator refresh omitted `source_repo` from immutable identity comparison | Include source repository in comparison; mismatch regression included in reported final 9-test native generator run | Resolved |
| CBEXEC-I07 | Medium | `_collect_binary_identity`: in-place same-size executable change with restored mtime reused a stale cached hash | Include ctime in cache key; actual-file regression fails before correction and passes in final complete runner group | Resolved |

## Verdict

- Gate status: **pass for feature correctness, artifact observability and reviewed segmented broad-regression coverage**.
- Unresolved implementation findings: High 0; Medium 0; Low 0. All seven findings are closed.
- Recommendation: **ship with disclosed validation limitations**. No additional CBEXEC correction or acceptance test is requested. The original broad command was not clean; approved fixture corrections and the complete remaining-module continuation close its CBEXEC coverage. Optional native WBT validation and pre-existing npm lint remain failed and outside this feature correction. Production deployment still requires its own authorization and operational rollout checks.
- Highest supported claim: focused correctness and live selection/save/preparation/default-worker hillslope acceptance, authenticated artifact readback and canonical archive/restore pass. Production is unchanged. No full watershed simulation, deployment, existing-run repair or general model-stability claim is made.
- Reviewer sign-off: final correctness/QA approval for runtime `3c114719b` and native `917265bb5`, plus the two reviewed locale test corrections, 2026-10-13 01:00 UTC. No unresolved correctness findings or feature-evidence conditions remain. Final forest service refresh/readback is the package owner's operational closeout.

## Artifact Observability Gate

The comparable existing WEPP workflow owns `config.cfg`, `config-manifest.json`, `wepp.nodb`, prepared `wepp/runs` inputs, executable identity and normal outputs. No new hidden per-project artifact location is introduced. Native sidecars are deployment provenance and retained in the two source repositories. Real writer/readback tests, source preservation and the live selected-runner chain are retained. Authenticated normal project downloads return matching prepared-soil/output SHA-256 and expose the expected runner identity. Canonical archive and restore jobs succeed, restore the selected 261010 release, and preserve config, manifest, prepared-soil and output hashes through authenticated downloads. This reviewer independently verified the downloaded ZIP hash, those four member hashes within the ZIP and the corresponding restored filesystem hashes. The gate passes for this bounded artifact inventory; no hidden artifact exception is used.
