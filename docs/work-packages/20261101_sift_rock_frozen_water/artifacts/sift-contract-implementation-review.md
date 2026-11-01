# Independent SIFT contract implementation review

Reviewer: `/root/rock_contract_impl`, 2026-11-01 Pacific. Starting implementation `d15d1470f`. Status: **one medium compatibility finding to resolve before checkpoint acceptance**. No production edits made by this reviewer.

## Confirmed source and consumer chain

Prior source-bound BC BCSLF metadata establishes COFRAG as volume percent and BD as fine-earth bulk density. The inspected adapter returns raw COFRAG through `_attr_validator`; `SiftHorizon.__str__` emits it as the final7778 mass-RFG token. `SIFT._build_horizons` constructs horizons, derives other traits, then `_build_wepp_soils` checks soil validity and serializes. Reusing the existing reviewed mass/volume converter is the smallest dimensional repair. Source summary explicitly reads `h._d` fields, so retaining them leaves raw JSON/summary provenance intact.

The reviewed contract correctly preserves source None/-9 sentinels as unavailable instead of supplying density, including zero rock with missing density. Missing in either conversion operand takes precedence over validating the other operand; mixed missing/invalid cases must be tested. Present numeric nonfinite/out-of-domain fractions and nonpositive/nonfinite density fail explicitly when conversion is evaluated. The scope does not invent a parser for arbitrary malformed string tokens.

## Medium finding SIFT-C1: open-water branch ordering

`SIFT._build_wepp_soils` currently uses `if soil.valid or soil.is_water`. New validation in rfg can raise before the existing open-water canned serializer is reached. A water row with present BD0 or out-of-domain COFRAG previously reached the water fallback even if its horizon was invalid; the new helper would reject it during `soil.valid`. This conflicts with the declared unchanged open-water behavior.

Required disposition: explicitly prioritize the already-established water branch (`soil.is_water or soil.valid`, or an equivalent bounded check), without changing the canned water soil. Add an actual builder regression with a water row containing present invalid conversion inputs as well as existing sentinel cases. The canonical compatibility promise already requires this; the checkpoint should record this narrow control-flow adjustment before implementation.

## Valid-state matrix and regression requirements

| State | Required outcome | Evidence required after implementation |
| --- | --- | --- |
| Populated mineral horizon | volume-to-mass conversion using source density | independent mass inventory and serialized soil/native readback |
| Zero fragments with valid density | native mass zero | scalar and native zero control |
| High fragments | convert before native mass cap; report cap separately | emitted mass and executed native cap readback |
| None/-9 fraction or density | unavailable rfg, incomplete-horizon filtering | direct property and actual builder with a remaining valid horizon |
| Missing operand plus invalid other operand | missing precedence, no invented conversion | explicit mixed-state regression |
| Present invalid numeric operands | explicit failure, no plausible soil publication | direct converter/property and builder failure readback |
| Open-water mapunit | unchanged canned water path irrespective of irrelevant conversion values | actual builder water case with invalid/sentinel fields |
| Historical generated soil/raw source | untouched; rebuilt output has additive basis comment | exact raw JSON values and old artifact nonmutation |

No new attack surface, file primitive, dependency or migration is introduced. Existing broad catches in horizon trait preparation are not expanded; conversion failures must not be silently caught there. All supported source keys, format precision,200mm split, restrictive-layer behavior and native caps remain unchanged. Native frozen-water campaign acceptance is separate.

## Approval boundary

After SIFT-C1 is dispositioned in the checkpoint, the design is suitable for the required contract ancestor. Final acceptance still requires actual builder/native propagation, focused and broad verification, and independent final review. Published source definitions do not certify every deployed local database.

## Revised checkpoint disposition — 2026-11-01 Pacific

**PASS for the bounded pre-implementation contract. SIFT-C1 resolved at design level.** The canonical contract, ADR and checkpoint now explicitly prioritize the canned water branch and define missing-operand precedence. Draft regressions include actual water writer cases with invalid or missing mineral inputs and mixed None/NaN conversion cases. No production edit is present at this review. Runtime closure of SIFT-C1 remains a post-implementation regression obligation.

A separate preexisting propagation risk must be checked during actual native acceptance: the mineral SiftSoil OFE header currently appears to emit seven tokens (slid,texid,nsl,salb,ki,kr,shcrit), omitting SAT expected in the7778 header; the canned water header includes saturation. This is source inspection, not an executed parser-failure claim. Do not silently add a fixture default and then claim the unmodified actual builder passed native propagation. Preserve any failure and make an explicit separately reviewed disposition if this blocks the declared acceptance. The dimensional contract itself remains valid.

Final reviewed document identities:

- `docs/work-packages/20261101_sift_rock_frozen_water/artifacts/contract-decision.md`: `216d19897d3caccbfe86761f1ecc087040276ff7d7901552cb7a7dd2e0dd6200`
- `docs/adrs/ADR-0126-sift-rock-volume-to-mass.md`: `079483d074590620894593d9cb86ee0422d23e454572906aaea76f2cfc2efc63`
- `docs/schemas/rock-fragment-representation-contract.md`: `3dd30b9b0363f5cde5d99f1742b321f039691260865b096cde91efcad0df925f`

## Builder-boundary amendment review — 2026-11-01 Pacific

**PASS for the amended pre-implementation checkpoint.** Read the retained actual builder failure at `out/sift-rock-frozen-water-20261101/baseline-builder/failure.txt` and raw JSON. The supported environment cannot import prettytable, and the canonical dependency list is `docker/requirements-uv.txt` (not a repository-root file). Replacing this comment-only formatter with standard-library fixed-width rendering is a smaller compatible repair than adding an undeclared dependency or catch/fallback. Keep raw source columns/values, and ensure every physical rendered line retains its comment prefix. Comment whitespace is explicitly outside numeric-input compatibility.

Read the separate `baseline-header-isolation/rock.sol`: the documented comment-formatter bypass exposes the seven-token mineral header without changing its numeric construction. It is diagnostic evidence only, not a successful actual-builder claim. The amendment explicitly adds mandatory SAT0.75 between SALB and KI, matching existing ISRIC initial saturation and SIFT canned water. This is a bounded missing-field decision with parameterization provenance. It must pass the canonical soil parser and fresh native consumer test; no other coefficients may shift.

These amendments resolve the previously retained header risk at design level and add a concrete baseline failure for the formatter boundary. Final implementation acceptance remains contingent on actual unmocked writer/parser/native readback, raw-source preservation and all declared regression states. No production source change is present in the reviewed diff. No deployment or frozen-water physics approval follows.

Amended reviewed identities:

- `docs/work-packages/20261101_sift_rock_frozen_water/artifacts/contract-decision.md`: `b83f7b5a3217b98e85c03145a36a11ed3dac6933ffd03f8975e35ababdde0e27`
- `docs/adrs/ADR-0126-sift-rock-volume-to-mass.md`: `70b22a720ca124b187267e8fa67052edc3b160dd00f78f5d82d2b39f4987d255`
- `docs/schemas/rock-fragment-representation-contract.md`: `731ca654db3d629c1c88ea3e30097258f4189d276e9a1ab7b07d1b2a0457b15f`
- `out/sift-rock-frozen-water-20261101/baseline-builder/failure.txt`: `7811394f613c522c061432a8495c4d8c2dd350f08acd62d2b656cbfc0219a8ed`
- `out/sift-rock-frozen-water-20261101/baseline-header-isolation/rock.sol`: `6dd955101576b10dedc8ef38415b7884a5dfc59e6b2d040eb09887e01de8dba6`
