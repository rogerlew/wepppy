# SA-01 independent contract security review

## Findings

No unresolved findings.

| ID | Severity | Evidence and consequence | Disposition |
| --- | --- | --- | --- |
| SA-CSEC-01 | Low | The initial decision record said there was no new remote input, although SA-01 adds two numeric request fields. That wording understated the validation boundary. | Resolved by author and independently read back: the decision now identifies two numeric fields on existing transport, with no new endpoint, upload/path input or privilege. |

## Verdict and scope

**Contract gate: pass.** Unresolved high/medium/low findings: **0/0/0**. This approves the proposed bounded contract for checkpointing; it does not certify implementation, scientific stability, a rebuilt native artifact or deployment.

Reviewer: independent `final_security_evidence` agent, dedicated security reviewer role, 2026-10-12. Reviewed WEPPpy base `298e434d3c2ac81b3100f2d9d318255153ea2294` and native base `bd630941e9f5d45b926291429ccc87c7cc92bae7`. Inspection was read-only apart from this review artifact; no accounts, runtime files, native binaries or run data were changed.

Reviewed authorities: [SA-01](../../../schemas/soil-anisotropy-contract.md), [WEPP input amendment](../../../schemas/wepp-run-input-contract.md#soil-anisotropy-sa-01), [Single User-Defined exception](../../../schemas/single-user-defined-inputs-contract.md#optional-mofe-anisotropy-exception-sa-01), [ADR-0088](../../../adrs/ADR-0088-soil-anisotropy-overrides.md), package, active plan and [decision record](2026-10-12_contract_decision.md). Existing NoDb, CSRF, response, artifact-observability and native release boundaries remain applicable.

## Security triage and authority

**Low impact is justified:** the new input surface consists of two bounded numeric fields through existing authorized run submission. There is no new path, upload transport, remote fetch, subprocess, queue topology or privilege. Rust receives already parsed in-memory values; Python retains run orchestration and persistence. Reusing the existing owned extension introduces no new dependency. A mandatory high-impact security gate is not indicated by this proposed scope; implementation must repeat triage if it widens those boundaries.

The requested upper/lower ranges, 50 cm boundary, MOFE/hourly eligibility, warning, Rust kernel and one-read/one-write preparation are within the recorded operator request. Bottom-depth classification without splitting is explicitly an implementation assumption, not separately claimed operator ratification or scientific validation. Any correction must amend the contract/ADR before divergent implementation. Forest build/validation authority does not authorize production deployment or pushing repositories.

## Noninterference and failure boundaries

| State or boundary | Contract assessment |
| --- | --- |
| Absent, omitted or cleared settings | Legacy absent attributes read None; omission preserves saved state; explicit blank/null clears. Neither override is enabled by default. Existing `kslast` omission and unrelated parser behavior remain unchanged. |
| Populated eligible settings | MOFE and effective hourly/deep-seepage enablement are both required. Upper [1,100] and lower [1,10] are inclusive finite bounds on overrides, not retroactive limits on original source ratios. The warning does not silently clamp valid requests. |
| Inactive or read-only state | Disabling eligibility retains stored values but prevents application. Explicit clearing remains safe when ineligible; ordinary authorization/read-only protections still apply. A failed routine-toggle request cannot enable editing. Preparation rechecks effective hourly state, including its explicit override path. |
| Invalid requests or stored active values | Reject booleans, duplicates/malformed values, nonfinite numbers and out-of-range values before other parser mutations. Revalidate active saved values before artifact generation. Required implementation evidence must prove invalid paired fields leave both overrides and unrelated persisted settings unchanged. |
| Depth and format compatibility | Apply after existing extension/clipping, using <=500 mm versus >500 mm without splitting. Positive finite nondecreasing depths preserve historical repeated terminal depths. Formats 7778 and 9001/9002/9003/9005 are covered; uploaded 7777/2006 cannot silently migrate or reinterpret profile anisotropy. Unset classes preserve admitted zero and other original ratios. |
| Native and file failure | Validate the entire nested input before applying returned values; preserve OFE/horizon shape and all non-target fields. Unsupported active formats or invalid values fail before writing that prepared soil. No native-unavailable numerical fallback is allowed. Existing preparation failure reporting remains authoritative; this does not promise a new transaction across all hillslopes or unrelated files. |
| Shared source read | Validation and parsing must consume one source snapshot without dropping existing SUDI size, structural, finite-number, format or immutable-source checks. Symbolic resolution reuses the snapshot and existing formulas/rounding. Source bytes remain unchanged; generated artifacts stay in ordinary browsable/archivable paths. |

Read-only source inspection confirms the two stated duplicate-read paths in `WeppSoilUtil.__init__` and `prep_soil`/`prep_multi_ofe_hillslope`. The existing preparation functions write the modified soil once. The proposed scope addresses those reads without authorizing a parser rewrite, input-policy relaxation or new mutation of original soils.

## Required implementation evidence and residual risk

Retain direct Rust validation and real locked parser/reload tests, including valid/invalid paired fields, omitted/cleared/inactive states, source zero, existing clipping duplicates and unsupported uploaded formats. Read the actual `wepp/runs/p*.sol` for every OFE; compare non-target fields and original hashes, and instrument real source opens/destination writes for ordinary, symbolic and uploaded-native paths. Exercise visible failed/completed artifacts and normal browse/archive behavior under the established runtime boundary.

Bind native source, build command/toolchain, release-object hash and actual forest import path; verify the rebuilt function through the real Python preparation callsite. Replace and roll back the Python/native pair together. Tests substituting the native function, writer or persistence boundary cannot establish conformance.

Residual risk is primarily model stability and compatibility, not broader access: accepted ratios may destabilize a simulation, and shared parser or stale native-artifact mistakes can alter generated inputs. The warning, unchanged defaults, complete value/format validation, actual artifact comparisons and paired release provenance address these within the proposed scope. No runtime acceptance or production-readiness claim is made by this contract review.
