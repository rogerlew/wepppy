# Independent M1 contract correctness review

## Metadata and scope

- Reviewer: `/root/prism_contract_correctness`, independent read-only contract reviewer.
- Reviewed: 2026-10-14 01:55 UTC; filename follows the package checkpoint date.
- Starting revisions: WEPPpy `78295c949bf5832c9d1ffaa5b8c708387f9aa356`; wepppyo3 `822b6fe1200d980e9eb434547097c976eafcc38f`.
- Scope: package/ExecPlan, contract decision, proposed `docs/schemas/prism-spatialization-temperature-contract.md`, EDDE contract amendment, ADR-0091/0092, and all four existing writer implementations. Also inspected historic PRISM, downstream eligibility, climate artifact lineage, and NoDb guidance.
- No implementation files were edited. This is pre-implementation contract review, not validation of a built extension or generated output.

## Findings

| ID | Severity | Finding and evidence | Required disposition | Status |
| --- | --- | --- | --- | --- |
| M1-COR-01 | Medium | The checkpoint omits the applicable historic PRISM contract, and the package's blanket exclusion of dewpoint changes leaves a compatibility ambiguity. `docs/schemas/prism-historic-climate-contract.md`, Spatial semantics and model transformations, requires recomputing hillslope dewpoint as `max(raw tdmean, revised Tmin)`. `wepppy/nodb/core/climate_observed_build.py:223-230` implements this after PRISM revision. The midpoint rule lowers Tmin on repaired days; therefore unchanged downstream floor arithmetic can legitimately lower final dewpoint. That conflicts with an unqualified reading of package.md:27 and the new contract's other-weather preservation language. | List historic PRISM as an applicable, assessed contract. Clarify that the four writers preserve auxiliary fields, while existing dataset-specific downstream dewpoint flooring still uses final repaired/quantized Tmin. Do not alter the floor formula or raw source dewpoint. Add a regression case where raw tdmean lies below unrepaired Tmin so the effect cannot be hidden by an unaffected fixture. | Resolved by reviewed amendments, 2026-10-14 01:57 UTC |

## Contract assessment

The numerical proposal is well bounded: apply existing offsets in their existing order, repair only finite introduced inversions with `a / 2 + b / 2`, permit equality, and preserve valid adjusted pairs. The ADR explains midpoint preservation, output rounding, monthly drift, and the rejected alternatives without claiming calibrated climate accuracy.

All four intended paths are correctly identified: Rust daily `rust_cli_revision`, NoDb Python breakpoint `cli_revision`, public Python `prism_revision`, and EDDE `revise_prism`. The Rust path currently clips precipitation normals and adjusts zero storm duration; the proposed same-writer baseline correctly prevents this package from unintentionally changing those existing behaviors. EDDE's offset operation order differs from the generic writers; preserving each path's order and allowing existing serializer rounding differences is appropriate.

The new rejection contract explicitly separates source inversions/nonfinite temperatures from introduced inversions. Rust's established I/O-to-`OSError` translation exists at `wepppyo3/cli_revision/src/lib.rs:1646`; Python `ValueError` and EDDE `DataQualityError` are specified. Temperature parsing and finite checks must remain narrow so implementation does not silently expand unrelated legacy-format admission. Generic partial destinations remain failed artifacts, while EDDE occupied-output ownership stays unchanged.

State and input matrices cover new outputs, populated outputs, absent legacy diagnostic metadata, invalid input, and stale native modules separately from daily/breakpoint and numerical cases. Missing optional legacy metadata is correctly distinguished from zero corrections. Public returns, NoDb keys, staging/finalization, and project rebuild authority remain unchanged.

## Acceptance requirements and residual risk

- Contract acceptance does not certify implementation. Required evidence remains actual Rust/Python serializers, rebuilt-module import identity, valid-day/non-temperature parity, and fresh prepared-input/WEPP output readback.
- Native diagnostics use process output, while Python paths use logging; the amended contract also requires a visible per-output log. Verify working/completed status, failure retention, canonical stage publication, and project browser/download/archive/restore behavior using actual writers. A captured unit-test string alone does not prove operational observability.
- Preserve historic PRISM's existing dewpoint-floor invariant after repaired temperatures, including raw-source immutability, per M1-COR-01.
- Finite source/normal operands can still overflow during offsets; the specified finite-result checks must run before midpoint repair and serialization. Do not treat finite inputs alone as sufficient.
- No deployment, automatic existing-project rebuild, new path authority, lock change, or external dependency is authorized. Existing artifact/browser/archive contracts remain in force; this review does not waive their final evidence requirements.

## Verdict

Gate status: **pass for the M1 contract checkpoint**. Unresolved findings: High 0; Medium 0; Low 0. Final code, build, performance, artifact visibility, and consumer validation remain separate gates.

## Post-fix confirmation

Re-reviewed 2026-10-14 01:57 UTC before implementation changes. The canonical contract's Artifact visibility and downstream scope section now expressly preserves the Historic PRISM floor on final Tmin, identifies the legitimate downstream effect, and requires a repaired-day regression. The checkpoint includes the historic contract, and the package/ExecPlan repeat the bounded distinction. This resolves M1-COR-01 without broadening the numerical decision or authorizing changes to raw dewpoint.

Also reviewed the control-review amendments: the per-output `.temperature-ordering.log` provides the previously missing durable destination without changing public returns; working/complete status and occupied EDDE log handling are explicit. Canonical project archive/restore and actual browse/download checks are now required. This is a bounded diagnostic file in existing output locations, not a new service or storage abstraction. The implementation must preserve existing source ownership and avoid mistaking diagnostic completion for full climate-build readiness.
