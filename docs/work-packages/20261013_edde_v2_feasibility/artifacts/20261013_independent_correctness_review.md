# Independent correctness and user-experience review — EDDE v2 feasibility

## Metadata

- **Package**: `docs/work-packages/20261013_edde_v2_feasibility/`
- **Reviewer**: independent Codex reviewer, `/root/edde_correctness_review`; no implementation edits.
- **Date**: 2026-10-13 UTC.
- **Scope reviewed**: `wepppy/climates/edde/`, `tests/climates/test_edde_client.py`, `tests/climates/test_edde_cligen.py`, study scripts, retained source/climate/WEPP artifacts, report, package, and active ExecPlan.
- **Commit/branch context**: `master`, planning commit `03435abc5154ad7aa77ee6868abf49cd70c4f6c0`, plus working-tree implementation. Reviewed `client.py` SHA-256 `d91247a2a8a7362617d4344a74090b78b6e1804261f05a43a8f3064ff4e36ef0`; `cligen.py` SHA-256 `9ca2c1b83c9ca3619e994ecda432927eb8d91e9d9d55b57191a17f444d400205`.
- **Canonical contracts**: [experimental client contract](../../../schemas/edde-v2-experimental-client-contract.md), sections Acquisition and eligibility, Source integrity and errors, CLIGEN generation, and Multiple PRISM; [ADR-0091](../../../adrs/ADR-0091-edde-v2-experimental-daily-replay.md); [package](../package.md), Scope and decisions and M1–M4; [acceptance criteria](acceptance-criteria.md).
- **Related review artifacts**: implementer [correctness review](20261013_correctness_review.md) and [security review](20261013_security_review.md). Independent security review is a separate gate.

## User Outcome

- **User goal**: determine whether EDDE v2 can support actual-location acquisition, CLIGEN daily replay, and Multiple PRISM before WEPPcloud integration.
- **Success presented as**: reproducible research files and a qualified feasibility disposition, including explicit rejected combinations. A successful process or query is not scientific production acceptance.
- **Failures that may reach the user**: invalid request, unavailable period/variable, ineligible native cell, source-data defects, upstream transport failure, CLIGEN quality-guard rejection, or invalid PRISM source/revision.
- **Partial-state behavior**: query/generation manifests remain incomplete, failed CLIGEN inputs/logs remain retained, and retries use new output locations. PRISM rejects invalid source data and existing output/provenance before writing; study-level rejection summaries retain scientific failures.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Source cache absent or empty | Yes | Bounded acquisition, source identity, complete data only | Live cold acquisition; `test_cache_integrity_and_partial_failure` |
| Hash-verified cache populated | Yes | Identical source values without weather transfer | `warm-cache-and-direct-parity.json`; recorded hash verification |
| Cache contents corrupted or transfer truncated | No | Reject or reacquire explicitly; retain partial attempt identity | Real-file corruption/truncation test |
| New query/generation output | Yes | New manifest and source-derived artifacts | 120 complete query records and 42 full-period generation manifests |
| Existing output CLI or PRISM companion | No for a new attempt | Preserve existing evidence and reject reuse | `test_prism_preserves_existing_provenance`; independent existing-companion probe |
| Empty, nonfinite, negative-P, or discontinuous CLI | No | Reject before accepting a PRISM revision | Strengthened `_validate_cli`; real serialized corruption tests/probes |
| Supported legacy projects | Yes | Existing workflows unchanged | Additive research module; no route, NoDb, RQ, or configuration wiring |
| Native land cell with requested records | Yes | Exact selected cell, finite complete dates/fields | Both grids; 15 locations and 120 model-years |
| Outside grid or selected ocean cell | No | Explicit eligibility error without relocation | `location-eligibility.json`, `native-edge-probes.json` |
| Valid same-period PRISM normals and source | Yes | Existing ratios/offsets, exact readback, meaningful wet storms | All 21 retained full-period PRISM climates pass strengthened validation |
| PRISM temperatures invert after offsets | No | Explicit rejection without clamping | Three retained rejected full-period attempts |

Input dimensions reviewed separately include model/scenario/year availability, date intervals, selected variables, point identity, cell geometry, source units, station/seed, and reference/target normals. Neither table nor tests claim exhaustive combinations.

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Missing archive combination | Expected | `AvailabilityError` | Inventory determines supported choices; no scenario/year substitution |
| Outside or nonland cell | Expected | `EligibilityError` | Native-cell eligibility contract |
| Missing/nonfinite source values or invalid metadata | Exceptional source defect | Explicit failure; no completed extraction | Source integrity contract; existing tests cover representative defects |
| Existing CLI/provenance output | Expected caller error | `ValueError`, original bytes preserved | New-output and artifact-retention contract |
| Negative P, nonfinite auxiliary field, or invalid storm in source CLI | Exceptional input defect | `DataQualityError`, no new CLI/companion | Corrected PRISM validation boundary |
| Missing PRISM normals or invalid revised extrema | Expected unsupported combination | Explicit rejection | PRISM coverage alone cannot establish revision validity |
| CLIGEN quality failure | Expected experiment outcome | Failed generation retained; no bypass | ADR-0091 and executable quality contract |
| Transport failure | Exceptional upstream failure | Existing requests exception | No hidden fallback or error translation |

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Direct evidence | Result |
| --- | --- | --- | --- |
| Request intent | Explicit source, point, dates, variables, station/seed, and spatial mode | Query/generation manifests and study selection scripts | Pass for bounded experiments |
| Reloaded persisted state | No application NoDb state involved; retained manifests identify selection | Archived query manifests and source hashes | Pass for research persistence; NoDb N/A |
| Generated intermediate | Exact native values and explicit units; normalized table and PRN quantization | 120 CSV SHA-256 checks; raw/normalized/PRN files and retained direct-NetCDF parity | Pass |
| Prepared/executable input | CLI P/T fidelity, dates, meaningful wet storms; fixed fixture inputs | 32 successful generation directories' recorded file hashes; all 21 PRISM climates independently parsed | Pass for successful cases; ten generation and three PRISM cases explicitly rejected |
| Execution output | Exact consumed inputs and fresh finite WEPP daily output | 69 execution records; all archived non-CLI consumed-input hashes and retained raw water-output hashes verified | Pass for stated smoke-test scope |
| User-facing result | Traceable findings and inspectable research evidence | `report.md`, three indexed archives, source/quality/seasonal tables | Pass for research handoff; application browser/report N/A |

Independent container probes verified all three archive SHA-256 values against the final `evidence-index.json` (created `2026-10-13T22:52:43.242808+00:00`). The source archive has 120 complete and two rejected query records; verified complete CSVs contain 657,450 point-days. Full-period generation manifests have 32 complete and ten incomplete outcomes. WEPP records contain 69 complete executions totaling 504,045 consumed climate days.

All 36 new seasonal PRISM pairs were recomputed independently from archived CLI files: 1,512 numerical comparisons passed for wet fractions, dry/wet spells, wet-day P95, daily P99, mean calendar-year seasonal maxima, absolute maxima, and historical/future differences. DJF maxima use January/February/December within calendar years, as now disclosed in the report. Spell calculations reset at omitted seasonal dates. These diagnostics are descriptive, not a scientific acceptance threshold.

- **Direct unmocked failing boundary**: before the fix, changing the first archived source CLI precipitation to `-1.0` or an auxiliary wind/duration/dewpoint field to `nan` produced a PRISM result marked complete. After the fix, each raw serialized corruption raises `DataQualityError` before either output file exists. Existing PRISM provenance bytes are also preserved by rejection.
- **Actual-project/environment evidence**: frozen U.S. project fixtures and `container-acceptance.json`; Canadian climates use a frozen U.S. hillslope. This does not establish Canadian watershed acceptance or production environment parity.
- **Highest completion claim supported**: locally validated standalone research extraction and executable climate feasibility, with a documented production no-go.
- **Deployment/recovery outstanding**: all application integration, project browser/archive behavior, production parity, and scientific adoption decisions remain successor-package gates; no deployment or affected-resource repair occurred.

## Review Checks

- [x] Canonical operator intent is distinct from implementation/test behavior.
- [x] Absent, empty, populated, legacy, and malformed states are considered; coverage gaps are named.
- [x] Request combinations and filesystem states are separate dimensions.
- [x] The changed PRISM rejection and preservation boundaries have direct unmocked filesystem probes.
- [x] Generated artifacts are read at the CLI/WEPP consumer boundary; hashes alone are not presented as semantic proof.
- [x] NetCDF fixtures use real files; CLIGEN artifact tests use the actual executable.
- [x] Completion language separates research validation, scientific suitability, and deployment.
- [x] Valid retained PRISM states still pass after source rejection controls were added.
- [x] Partial-state, retry, and preservation behavior is explicit for this research scope.
- [x] Existing application behavior remains unchanged; no exhaustive coverage claim is made.

## Findings

| ID | Severity | User/state surface | Description and evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| ICOR-01 | Medium | PRISM source CLI | Original `revise_prism` checked only changed P/T rounding, allowing negative P or nonfinite auxiliary fields to be emitted with complete status. Independently reproduced on archived real CLIs. | Validate complete source/readback semantics and regress malformed serialized input. Implemented in `wepppy/climates/edde/cligen.py:18`, called before revision and after writing; current focused suite and independent probes pass. | Resolved |
| ICOR-02 | Medium | Feasibility evidence completeness | Initial signal table covered monthly mean T and summed P only; package M3 also promised wet-day and extreme-event behavior before/after PRISM. | Retain seasonal frequency/spell/extreme evidence. Added `prism-seasonal-extremes.csv`; independently recomputed all 36 pairs and 1,512 numeric values. | Resolved |
| ICOR-03 | Medium | Existing PRISM provenance | Original revision checked only target CLI existence and could overwrite an existing `.prism.json`. Security reviewer identified the related ownership concern. | Reject either occupied output and any source alias. Corrected at `wepppy/climates/edde/cligen.py:135`; direct preservation probe and regression test pass. | Resolved |

The report's historical bias, station-derived auxiliary weather/header, quality-guard failures, coastal/Canadian coverage limits, and PRISM temperature inversions are scientific or integration no-go findings, not unresolved defects in the bounded research implementation. They remain real production blockers; this review does not accept or waive them.

## Verdict

- **Gate status**: `pass` for correctness of the standalone feasibility delivery.
- **Unresolved implementation findings**: High 0; Medium 0; Low 0.
- **Release recommendation**: `ship-with-conditions` — retain the experimental research scope and the explicit hold on WEPPcloud production integration.
- **Reviewer sign-off**: independent Codex reviewer, 2026-10-13 UTC.

No major unresolved implementation finding remains after the reviewed corrections. Residual coverage limits are material: only selected locations/stations/seeds and source windows were exercised; direct hourly aggregation parity covers one historical month; full paired PRISM diagnostics cover Tiger-Mill because Cascade historical generation failed. There is no calibrated hydrologic, complete future auxiliary-weather, Canadian watershed, or production deployment validation. The focused validation log reports 25 passing tests. The unrelated SBS full-suite assertion and the separately running continuation suite must remain accurately reported by the parent handoff; this review does not convert that run into an all-tests-pass claim.

## Artifact Observability Gate

- [x] Comparable mechanisms are the existing climate client, CLIGEN, and PRISM workflows; canonical study inventory is `evidence-index.json` and the experimental contract's Artifact layout and operational recovery section.
- [x] Inputs, intermediates, failures, provenance, and outputs are retained in visible standalone study files/archives with reproduction instructions.
- [x] Real writer/consumer probes and archive member/hash verification support retention. Project browser/download/archive tests are N/A for this package because no project integration is implemented; they remain mandatory successor-package gates.
- [x] No project-artifact exclusion, hidden project directory, or waiver of normal project authorization is introduced.
