# Correctness review: ESDAC source sufficiency

## Verdict

**Independent code and generated-artifact review: pass.** No unresolved high or medium findings. The required broad regression gate remains in progress at this sign-off and must be dispositioned by the executing agent before package closeout. Release recommendation: ship with the documented validation/deployment conditions; no claim of production deployment or repaired production run.

Reviewer: independent `esdac_correctness` agent, 2026-11-06 UTC. Candidate is the working tree based on `f77469e41b6e83b0f4ffbf7e6f827a3638a9bf80`, bound by the three final source hashes in `availability-sufficiency-summary.json` and `incident-sufficiency-summary.json`. Authority is `docs/schemas/esdac-soil-source-contract.md`, ADR-0139, and the operator's instruction to build from sufficient available data. Security triage is none: no new authentication, authorization, or external execution boundary.

## User outcome

The user can obtain valid soil files when descriptive labels are absent, and when the known modeled total depth leaves no positive-thickness subsoil interval. Missing physical evidence needed by an emitted material remains an error. Batch publication retains diagnostic reports, shares equivalent soils, preserves distinct soil contents under disambiguated keys, and does not publish partial new outputs on failure.

## Failure-class coverage

The shared failed assumption was that every category in a descriptive key, and every potential subsoil field, is mandatory physical evidence. The review covers repository-owned ESDAC source admission, serialization, batch publication, direct diagnostic readers and disturbed consumers; it does not claim universal European availability.

| Consumer or variant | Dependency | Final disposition |
| --- | --- | --- |
| Direct ESDAC builder | Source validator and real serializer | Corrected; populated, absent, blank and partial metadata tested |
| Shallow/equal-depth construction | Existing representative depth maps and conditional subsoil sampling | Corrected; emitted material checks retained |
| Batched hillslope builder | Key grouping and atomic publisher | Corrected; original 35-location replay passes |
| Existing-file rebuild | Stable artifact identity | Actual incident retry and legacy valid/degraded reuse pass |
| Distinct profiles with rounded-key collision | Hash suffix and report mapping | Two distinct real serialized profiles retain different keys; returned/report mappings agree |
| Diagnostic search | Direct `ESDAC.rats` access | Eager populated-table contract preserved |
| Disturbed single-OFE/MOFE | Quality report, per-location keys and output validation | Runtime tests pass; actual incident downstream artifacts and single-material fixture conversions pass |
| Mandatory physical inputs | Depth/CEC, STU, conductivity and output validators | Rejection remains for missing/invalid information needed by emitted material |
| Production deployment/original project | Deployed code and run artifacts | Outside local code-delivery scope; unchanged and unrepaired |

## Valid-state matrix

| State | Required behavior | Direct evidence |
| --- | --- | --- |
| Optional metadata absent/blank | Warn, preserve raw evidence, build from valid physical data | Validator/serializer matrix and real-raster incident |
| Usable class code with missing pixel/description | Retain the class and its physical branch | Forest codes 5/22 and partial depth-description tests |
| Fully populated valid source | Preserve numerical inputs and successful keys | All 446 baseline successes retain parsed physical content; legacy retry tests |
| Mapped total depth below/equal texture transition | Emit top material only through known total depth; do not require unused subsoil | Less/equal cases, missing sub CEC/STU, and 76 actual study locations |
| Mapped total depth beyond texture transition | Require usable top and subsoil data | Deeper-profile missing-subsoil test and prior successful controls |
| Invalid emitted top material | Reject with field-qualified diagnostics | Explicit shallow-profile invalid top density regression |
| Malformed/missing physical class | Reject without leaking incidental dictionary errors | Source validation and depth tuple regressions |
| Equivalent soils/retry | Keep common legacy key and preserve existing bytes | Actual two-hillslope incident retry plus full 35-location replay retry |
| Different artifacts sharing rounded key | Preserve both, update report and dominant mapping before commit | Actual serialized collision regression plus publication tests |
| Unsupported alternate provider shape | Outside supported `query()` tuple-of-strings contract | Explicit limitation in canonical contract; see residual risks |

## Findings and resolutions

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| COR-01 | High | First actual batch replay still rejected equivalent soils because full bytes included per-build timestamps; rounded keys also cannot represent distinct contents safely. | Stable identity excludes volatile dates/additive warning comments; content suffixes preserve different artifacts; report mappings updated before publication. Actual replay/retry and serialized collision tests pass. |
| COR-02 | Medium | Treating any partial metadata tuple as wholly missing discarded known forest code 5 and changed its physical branch. | Component-wise normalization retains usable codes; missing descriptions/pixels warn independently. Forest 5/22 tests pass. |
| COR-03 | Medium | Initial lazy optional-RAT loading broke the diagnostic sampler's direct `rats` reader. | Populated tables remain eager; only errors are deferred to location-specific handling. |
| COR-04 | Medium | Reordered source comments and newly added warnings changed otherwise equivalent legacy artifacts on rebuild. | Historical order preserved; additive warning comments excluded from identity. Real serializer valid/degraded legacy reuse tests pass. |
| COR-05 | Medium | Initial subsoil decision and required tuple validation disagreed, allowing a `None` map lookup for partial depth metadata. | Both boundaries retain usable depth codes; missing descriptions warn and are normalized before serialization. Partial-depth regression passes. |
| COR-06 | Medium | Eager subsoil CEC RAT failure could abort a profile that did not emit subsoil. | Subsoil CEC lookup failures are deferred; they are fatal when needed and warnings when unused. Conditional constructor/build regression passes. |

The expanded depth rule follows existing **representative mapped depths**, not exact measured horizon boundaries. The bundled SGDPE legend describes the texture-transition and impermeable-layer classes. If mapped total depth is at or above the mapped transition, there is no positive-thickness subsoil interval. The implementation preserves the known modeled total depth and available top material; it does not invent a missing lower material. The 200 mm normalization may split that one material into two serialized horizons.

## Generated artifact evidence chain

| Stage | Retained evidence | Independent result |
| --- | --- | --- |
| Original intent/failure | Operator request and `incident_soil_quality.json` | All 35 failures identified |
| Sampling frame/source context | `availability-manifest.json` | Same 1,000 unique valid-anchor locations for old/new builders |
| Direct builder outputs | `availability-baseline.tar.gz`, `availability-sufficiency.tar.gz` | All referenced artifacts checked against recorded hashes |
| Model-consumed physical content | Parsed OFE/horizon objects in results | All 446 previously successful profiles numerically identical |
| Conditional single material | 76 accepted study records | Final depth equals mapped IL depth; 200 mm boundary exists; both rows preserve identical material properties |
| Batch publication and retry | `incident-sufficiency.tar.gz`, corresponding summary | 35 accepted, 0 rejected, 2 base soils; retry preserves bytes and mappings |
| Downstream disturbed inputs | 35 incident `.sol` artifacts and `downstream_readback.json` | All retained hashes match; parser/validator readback passes |
| Current candidate identity | Final study and incident source hashes | All three hashes match current files; final study `source_unchanged=true` |
| Full watershed/native execution | Outside this soil-builder package | N/A; no model-result claim |
| Live original project | Deployment/recovery separate | No production repair claim |

The reviewer independently recomputed outcomes from all final study records:

| Outcome | Previous builder | Final builder |
| --- | ---: | ---: |
| Valid | 147 | 136 |
| Degraded, usable | 299 | 597 |
| Rejected | 554 | 267 |
| Total accepted | 446 | 733 |

There are **287 recovered locations, zero regressions**, and zero numerical changes among the 446 shared successes. The geographic frame extends from approximately 35.01 to 71.02 degrees north and -10.32 to 71.22 degrees east. The 73.3% figure describes this stratified valid-anchor sample, not area-weighted European coverage. Diagnostic counts overlap and reflect stopping-stage validation; they are not an exhaustive census of every missing field in every rejected profile.

The earlier metadata-only checkpoint remains historical evidence (`availability-final.tar.gz`, `metadata-comparison.json`) and is not the final result. Its broader source-hash check was false because an unused batch module changed; final sufficiency evidence supersedes that checkpoint and has all three source hashes unchanged.

## Tests and review checks

The final focused checkpoint passed **122 tests** in 65.70 seconds, including real-raster incident retry, valid/degraded legacy artifact reuse, conditional source sampling, shallow/empty-subsoil downstream conversion and physical rejection. A subsequently added actual divergent rounded-key serializer test passed separately. The initial broad run was interrupted after source changed (532 passed, 28 skipped); the executing agent is running the final broader validation separately. This review does not claim a completed broad gate.

- Canonical user intent and field sufficiency are explicit; old tests are not behavioral authority.
- Missing/partial/known/unsupported states and less/equal/greater depth relationships have distinct coverage.
- Actual serializers, batch publication, retries and consumer parsing were exercised; mocks do not replace the failing boundary.
- Source hashes, generated bytes and parsed semantics substantiate the final candidate result.
- Implementation/local validation remain distinct from deployment and original-run recovery.
- No claim of exhaustive geographic availability or all model-output correctness is made.

## Artifact observability and residual risks

The existing `soils/soil_quality.json` remains the project diagnostic surface; source warnings also appear in soil comments. No new hidden project records or authorization exclusions are introduced. Study archives retain input manifests, failures, generated outputs and provenance. No archive/browser mechanism changed; live original-project recovery remains a separate operational action.

The live source reader returns string class codes. Alternate providers supplying non-string short codes are explicitly unsupported; pure-validator versus builder normalization is not promised for those shapes. Remaining 267 sampled failures require physical/provider evidence beyond this bounded correction. Native model outcomes, deployment parity and original-run recovery are not established by these soil-builder artifacts.

Independent reviewer sign-off: `esdac_correctness`, 2026-11-06 UTC. Code/generated-artifact gate passes; broad regression disposition remains the executor's final closure condition.
