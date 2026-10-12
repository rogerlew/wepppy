# SA-01 contract correctness review

Reviewed 2026-10-12 20:16 UTC by independent `contract_correctness` agent.

**Approved for the standalone contract checkpoint.** The three compatibility findings below are resolved in the reviewed amendments. No open high/medium contract finding remains. This is a pre-implementation review, not native-build, generated-artifact, scientific-stability or deployment acceptance. The separate second review and ancestor commit remain required before runtime edits.

Starting revisions verified: WEPPpy `298e434d3c2ac81b3100f2d9d318255153ea2294`; wepppyo3 `bd630941e9f5d45b926291429ccc87c7cc92bae7`. Runtime files were unchanged at review. The reviewer made no runtime edits or project-file mutations; unrelated i-crews documentation was excluded.

## Findings and disposition

| ID | Severity | Evidence and compatibility issue | Disposition |
| --- | --- | --- | --- |
| SA-C01 | Medium | The initial supported-format list omitted 9001, although `wepppy/wepp/soils/utils/wepp_soil_util.py` parses and writes its per-horizon anisotropy and existing tests cover that format. It cannot be treated as lacking a per-horizon field. | Resolved: SA-01 now explicitly includes 9001 with 7778/9002/9003/9005. |
| SA-C02 | Medium | An unspecified strict depth check could reject existing ordinary clipping. Calling the real `WeppSoilUtil.clip_soil_depth(500)` on in-memory depths `[100,500,800]` yielded `[100,500,500]` for ordinary preparation and `[100,500]` for preserved uploads. The current exact-boundary break is preservation-only. | Resolved: SA-01 requires positive finite nondecreasing depths and explicitly preserves repeated terminal depths from ordinary clipping; no incidental clipping correction is authorized. |
| SA-C03 | Medium | Applying new override bounds to original ratios would reject or change valid uploaded anisotropy zero. The existing single-user-defined contract admits nonnegative source ratios. | Resolved: unset depth classes explicitly retain original ratios, including zero, without new override bounds. |

The clipping probe used `wctl exec weppcloud python` and the actual production method on temporary in-memory objects; it wrote no files. The author added regression obligations for these three cases to the decision record.

## Reviewed contract and feasibility

Reviewed [SA-01](../../../schemas/soil-anisotropy-contract.md), [ADR-0088](../../../adrs/ADR-0088-soil-anisotropy-overrides.md), appended WEPP-run-input and single-user-defined-input sections, package, active plan and decision record against current Python preparation, parser/writer, UI routine handling, RQ payload handling and the native interchange export boundary.

- The dimensionless upper `[1,100]` and lower `[1,10]` bounds are inclusive and finite. Bottom depth `<=500 mm` is upper; `>500 mm` is lower. Classification follows minimum extension then maximum clipping in every OFE, without horizon splitting. The recorded bottom-depth assumption is consistent across contract, ADR, plan and tracker; it is not represented as a separately confirmed operator choice.
- Absent legacy attributes, omitted keys, explicit blank/null, saved inactive values and malformed values have distinct outcomes. Validation precedes parser mutation; clearing remains available when otherwise ineligible, while existing run read-only controls remain authoritative. An anisotropy-validation failure must not partially persist either override or unrelated submitted fields.
- MOFE and saved hourly/deep-seepage eligibility govern editing. Preparation must use the effective hourly argument: `None` uses the saved flag, explicit `False` suppresses overrides, and explicit `True` can activate saved overrides while still requiring MOFE. Current `WeppPrepService.prep_hillslopes` selects soil preparation before handling the hourly marker, so propagating effective state into the MOFE task is necessary; inspecting the marker later is insufficient.
- Uploaded 7777/2006/2006.2 retain their native fields/version. Active per-horizon overrides fail before the prepared soil write; blank/inactive overrides preserve their existing path. The SUDI exception is correctly limited to its already-admitted 7778/9002 upload formats and does not accidentally expand upload admission to generated 900x formats.
- A bounded Rust function over parsed nested depths/ratios fits the existing `wepp_interchange` extension. It should validate shape and all active values before returning any replacements. Python keeps persistence, file paths and orchestration. No second file transform, new dependency, numerical fallback or whole-parser port is needed.
- The revised source-snapshot strategy is feasible and lower risk than extracting historical computations into a new implementation. Reparse the already-read text in memory with the existing computation flags when symbolic resolution needs it; preserve original erodibility/conductivity rounding, restrictive-layer derivation and operation order. Uploaded validation and parsing use that same snapshot. This is one source-file read even if it includes a second in-memory parse.
- Existing authorization, CSRF, errors, NoDb locking, source immutability and ordinary artifact visibility remain applicable. No queue, endpoint, privilege or original-soil migration is introduced by the reviewed scope.

## Required implementation evidence and residual risk

Retain real locked save/reload and rebuilt-native import evidence, then read actual prepared `wepp/runs/p*.sol` files. Exercise upper/lower independently, exact 500 mm, crossing and clipping cases, every OFE, preserved zero, 9001, uploaded 7777 incompatibility, inactive malformed saved settings, and explicit preparation-time hourly overrides. Assert source hashes and every unrelated prepared field against the existing path. Measure actual source opens and destination writes for ordinary, symbolic and preserved-upload preparation; a mocked writer is insufficient.

The UI must derive editability from successful saved routine state, preserve values while disabled, and remain read-only when required. Failed toggles, repeated toggles and subsequent reloads need direct controller/browser evidence. Unset/inactive preparation must retain legacy behavior; an unavailable required native kernel must fail explicitly for an active override instead of silently changing formulas or invoking Python numerical substitution.

Scientific suitability and stability of accepted ratios are not established by range checks or this review. Python/native source and deployed extension identity, generated-output parity, real workflow acceptance and rollback pairing remain implementation gates. No performance improvement is claimed without measurements.
