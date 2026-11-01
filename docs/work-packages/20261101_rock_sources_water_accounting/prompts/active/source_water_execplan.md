# Resolve rock source definitions and native water accounting

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. It succeeds the completed dimensional repairs at WEPPpy `234580e22`; it does not modify the previous package's hash-bound evidence.

## Purpose / Big Picture

Establish which surface and regional rock observations can be used faithfully, and what a physically consistent native water-capacity experiment must account for. Users gain source-grounded findings, reproducible acquisition/diagnostics, and a reviewed implementation decision. This is investigation and faithful source analysis, not a surrogate model or a promise to promote new physics.

## Progress

- [x] Read applicable instructions and prior scientific/consumer findings.
- [x] M1: bounded source acquisition, BC dataset lineage, surface-record interpretation.
- [x] M2: actual native writer/reader and stock/flux accounting map.
- [x] M3: source-grounded executable checks and development disposition.
- [x] M4: independent reviews, reproducibility, archive and checkpoint.

## Context and Orientation

`wepppy/locales/canada/bc/soils/sift/sift.py` consumes the BCSLF_Soil_Layer_File table in `/geodata/ca/env.gov.bc.ca/BC_Soil_Map.gdb/`; COFRAG is currently emitted directly as native mass RFG and BD supplies bulk density. The exact prepared-field definitions are unconfirmed. `wepppy/soils/ssurgo/ssurgo.py` divides whole-soil water content by a capped mass-fragment complement. Neither path inherits the prior SoilGrids correction without independent evidence.

Surface acquisition in `docs/work-packages/20261031_rock_representation/artifacts/fetch_surface_evidence.py` timed out. Retry only development materials 1718465, 1718494, 1856573 and 2711184. The six withheld materials remain excluded. A query result is survey information, not measured engineered armor. Preserve raw response, source time, identifiers, nulls, fragment kind/size and component proportions before aggregation.

Native source is `/workdir/wepp-forest-release-20261009/src`. SCON sets initial water using POR*CPM but its UL limit omits CPM; INFPAR already uses CPM. POR is air-corrected porosity, CPM fine-earth volume share, ST stored liquid above a dry reference and UL an upper limit in that coordinate. Prior 586-layer initialization checks establish ordering only, not freeze/thaw or later water conservation. Trace SCON, GRNA, INFPAR, both water balances, percolation/lateral drainage and freeze/thaw at exact source identities.

## Plan of Work

M1 retrieves authoritative BC metadata and inspects local dataset/schema if present. Retry the original bounded NRCS request to a fresh directory, then use documented service endpoints/formats if transport evidence justifies it. Distinguish endpoint errors, absent records and semantic uncertainty. Retain source URLs, payload hashes, dates and extraction commands. Develop a producer only after record overlap and basis are established; do not replace missing observations.

M2 records all relevant writers/readers, units, layer support and execution order. Identify liquid, ice, reference water, capacity and routed fluxes; classify parameter proxies separately from conserved stocks. Independent review checks the map against source. Do not change POR globally or retrofit a lower capacity by clipping existing water.

M3 executes bounded diagnostics with independent arithmetic. An actual-source scalar probe requires a frozen declaration and reviews before compiling/running; pin compiler PATH and complete input/source identities. Cover zero/high rock, reference shifts, ordered limits, overflow and frozen partitions where actually exercised. Record unsupported states instead of claiming exhaustive validation. A source-confirmed regional production correction requires a reviewed contract/ADR, actual emitted input and native readback, focused regressions and full suite; otherwise retain an explicit development decision and prerequisites. No native behavioral lane proceeds before source/scalar review.

M4 obtains independent scientific and implementation reviews, resolves findings, lints changed docs using `wctl doc-lint`, and verifies fresh artifact hashes. Archive completed raw evidence outside the raw root after writers stop; bind public files and keep earlier artifacts unchanged. Update this plan and tracker, then commit the bounded reviewed result on the current branch.

## Validation and Acceptance

Source findings must cite the exact consumed dataset and retain acquired payloads or explicit failure receipts. The consumer map must identify actual writers and readers, not merely search hits. Diagnostics must expose the original native arithmetic or clearly identify illustrative accounting identities; no Python reimplementation is labeled an actual-native test. Production changes, if justified, require canonical generated-artifact acceptance and the repository's test gates. Documentation/research-only work uses relevant script readback and scoped lint, not an unrelated full-suite rerun.

## Idempotence and Recovery

Every experiment refuses existing output directories. Public reports contain no native source. Original source, private builds, live projects, prior studies and unrelated dirty files remain unchanged. Retain failed requests and rejected probes. Use existing standard-library, geospatial and compiler tooling; no new dependency is needed.

## Surprises & Discoveries

NRCS returned15rows with8surface records across9components. Mapunit2711184 sums to90% composition, so the first reader failed its100%-total assumption; the revised reader preserves10% unallocated. BC official dictionary establishes volume COFRAG and fine-earth BD; actual serializer retains the mismatch. A synthetic ordered-capacity diagnostic traps in the actual hourly drainage denominator while its native control passes. Frozen overflow and daily/hourly small-excess thresholds differ as declared.

## Decision Log

2026-11-01: execute source investigation and native accounting first, as recommended and authorized by the operator. Preserve the completed package rather than amend its hash-bound publication. Rationale: source definitions and stock/flux ownership determine whether later scientific changes are valid.

## Outcomes & Retrospective

The requested source and native-accounting tracks produced reviewed findings and17compiled source-fragment observations:16normal reference matches and one expected invalid-domain counterexample. Source queries/readers and independent replays complete; scoped docs lint passes. No production code or native model behavior changed. BC repair is now eligible for a separate ADR and generated/native-artifact implementation; source availability does not imply deployed database inspection. Whole-routine frost mapping, coupled drainage domains and surface overlap remain open. Verified archive and final reviews are linked from the package.

Continuation decision, 2026-11-01: retain this as the requested source/accounting checkpoint. Do not bundle the newly eligible BC correction or native response changes into observational acceptance. Rationale: they require separate emitted/native input or coupled physical gates, whereas this campaign supplies the prerequisites and counterexamples. Completed review/retention results are documented in tracker.md and artifacts.
