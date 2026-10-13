# Correctness and user-experience review — EDDE v2 feasibility

## Metadata and user outcome

Reviewer: Codex implementer self-review, 2026-10-13 UTC. **Independent correctness review remains pending.** User goal: a reusable query client, real-location/data-quality evidence, executable CLIGEN/PRISM feasibility, and a justified integration decision. Scope is research execution; there is no new WEPPcloud UI.

Authoritative contracts: `docs/schemas/edde-v2-experimental-client-contract.md`, ADR-0091, package scope, and `artifacts/acceptance-criteria.md`. Evidence: `report.md`, `evidence-index.json`, source/quality tables, generated climate/WEPP manifests, and `container-acceptance.json`.

## Valid-state matrix

| State | Expected outcome | Evidence |
| --- | --- | --- |
| Absent cache / fresh output | Bounded download and new artifacts with source identity | Live acquisition, offline transport/filesystem tests |
| Empty or malformed point/date/variable selection | Explicit validation error; no substituted data | Point, time, missing-variable tests |
| Valid populated cache | Hash-verified identical data; no weather transfer | Live one-year warm benchmark and direct native-float parity |
| Corrupt or partial cache | Reject/reacquire within budget; never bless partial data | Corruption/truncation tests and attempt records |
| Unsupported model/scenario/year | Availability error | NorESM absent SSP3-7.0 and 2080 requests |
| Inside native valid-land grid | Exact cell, complete finite records | 15 points, both grids, 120 model-years |
| Outside or ocean-cell point | Eligibility error without edge/nearest-land clamp | Yellowknife, Topanga, Miami, native edge probes |
| Valid PRISM coverage and arithmetic | Explicit normals, faithful ratio/offset output | 21 full-period revisions, direct artifact tests |
| Missing PRISM or inverted daily extrema | Explicit rejection | Canadian grid exclusions, three full-period inversion cases |
| Existing generated output | Reject reuse rather than overwrite old success | New-directory and existing-output tests |
| Supported legacy projects | Unchanged; no integration edits | Scope/diff boundary and broad regression attempt |
| Hostile source path/object identity | Reject traversal/identity drift | Safe-key and ETag tests |

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| COR-01 | High for production adoption | Large location-dependent historical bias; no bias correction | Retain raw values; hold general future-impact integration pending scientific policy and validation |
| COR-02 | High for production adoption | Auxiliary fields and header derive from station, not a complete EDDE future-weather mapping | Explicit provenance/limitations; hourly metadata probed; full-period source-derived auxiliary workflow remains a handoff gate |
| COR-03 | High for unrestricted Multiple PRISM | Three full-period target cases invert temperature extrema | Rejected before output; no clamp; policy decision required before broader support |
| COR-04 | Medium for coverage claims | Coastal land can select ocean cells; Canada and PRISM footprints differ | Independent grid/mask checks, explicit rejection, no whole-country promise |
| COR-05 | Medium for workflow availability | Ten selected-station/seed CLIGEN cases fail existing quality guard | Failed attempts retained; no bypass or seed/station fallback |
| COR-06 | Medium for release evidence | Independent review not yet authorized/completed; broad suite has a preexisting SBS assertion failure | Keep final release/package gate open and report validation limits |

The high scientific findings are not claimed fixed or accepted risks. A feasibility study can document a no-go result; these findings continue to block production integration.

## Artifact and consumer checks

Source objects to extracted tables are directly compared at native float32 precision. Daily/hourly precipitation alignment is tested at 465 point-days. All requested source dates/fields are complete and valid. Raw and normalized tables, exact PRN/station inputs, binary and seed identity, CLI values, consumed WEPP input hashes, fresh output hashes, and parsed annual diagnostics form the retained chain. NoDb state is not applicable because these are standalone experiments.

Successful source-to-CLI precipitation/temperature differences remain within existing format rounding. The 69 successful 20-year WEPP cases match consumed precipitation, continuous dates, and finite output; 1,380 case-years of flux/storage diagnostics are retained. The three full water-output examples are selected by fixed location/model/arm, not model outcome; other raw outputs remain in scratch and are reproducible. A separate dev-container check exercises actual EDDE single/PRISM input under its configured identity. This does not prove production deployment or Canadian watershed acceptance.

PRISM signal validation covers 108 matched monthly checks at Tiger-Mill. Cascade historical CLIGEN failures prevent corresponding full-period paired claims. Header station/nominal-year metadata, small-precipitation quantization, dewpoint versus minimum temperature, reference-data limitations, and partial water-balance accounting are disclosed in the report.

## Verdict

**Study outcome: conditional go for standalone research extraction/replay; no-go for general production integration as currently parameterized. Review gate: pending independent sign-off.** No deployment, repaired-run, or full hydrologic validation claim is supported. Security review is separate and does not close these scientific or correctness gates.
