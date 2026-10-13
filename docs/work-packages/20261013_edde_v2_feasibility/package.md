# EDDE v2 client and climate-workflow feasibility

**Status**: Open — study executed; broad regression gate remains unresolved (2026-10-13)
**Timezone**: UTC

## Overview

Evaluate EPA Dynamically Downscaled Ensemble version 2 (EDDE v2) as a future-climate source for WEPP. Build a reusable Python query client, measure actual-location data quality and acquisition cost, and demonstrate CLIGEN climate generation and PRISM multiple spatialization before committing to WEPPcloud integration.

## Scope and decisions

These are the operator's 2026-10-13 planning decisions and the authoritative scope while this package is open. Promote accepted runtime contracts outside work packages before closure.

- Scope availability by locale, then validate each project's actual location against the selected dataset grid and data availability. Locale membership alone is insufficient: Canadian coverage is partial. Evaluate U.S. and Canadian locales first; determine exact supported locale identifiers from repository configuration and evidence.
- Build an API client over the published public S3/NetCDF data. A point-query service is not assumed to exist. Preserve model, scenario, period, source variable, grid-cell identity, coordinates, units, calendar, and object provenance in every extraction.
- Demonstrate a single-location baseline and **Multiple PRISM** where the existing PRISM climatology coverage is available. This is the existing spatial revision concept (`ClimateSpatialMode.Multiple`), not a request to substitute historic daily PRISM for future EDDE weather.
- Exclude **Multiple Interpolated** from initial supported modes. A 12 km source grid may not justify apparent fine-scale variation; this is an initial scope choice, not an established scientific finding. Reconsider only with evidence and an explicit scope decision.
- PRISM unavailability must be explicit. An EDDE-eligible Canadian location can still support the single-location workflow without qualifying for Multiple PRISM. Do not silently substitute another spatialization.
- Separate feasibility from web integration so data access, scientific assumptions, and executable climate artifacts can be evaluated independently.

## Milestones and deliverables

### M1 — Source inventory and executable query client

Before implementation, author an ExecPlan in `prompts/active/edde_v2_feasibility_execplan.md` using `docs/prompt_templates/codex_exec_plans.md`. Inspect existing clients under `wepppy/climates/`, particularly `gridmet/`, `prism/`, and `holden_wrf_atlas.py`; propose an additive `wepppy/climates/edde/` client and focused `tests/climates/` coverage. Reuse installed transport and NetCDF dependencies after the dependency precedent check.

Inventory actual model/scenario/year/variable/frequency objects. Resolve the published 2099 versus 2100 endpoint discrepancy from timestamps, and never treat historical 1985–2014 plus future 2025 onward as a continuous record. Check grids independently for each driving model. Deliver a documented command that takes latitude/longitude, model, scenario, dates, variables, and output directory and returns a bounded extraction plus a machine-readable provenance and eligibility manifest. Discover available combinations rather than hard-coding advertised availability.

Use the smallest bounded acquisition first. Measure cold/warm bytes, time, memory, cache size, and repeated-location cost for one year and a representative multidecade window. Record object sizes before large downloads. Do not create a mirror of the entire archive. Distinguish out-of-domain, unavailable data, invalid requests, and transient retrieval failures; no silent nearest-edge clamping or missing-data filling.

### M2 — Actual-location coverage and quality study

Retain a reproducible location matrix spanning coastal, mountain, dry, wet, and cold U.S. sites plus Vancouver, Calgary, Edmonton, Winnipeg, Toronto, Montreal, Quebec City, and Halifax. Include actual project coordinates and hillslope footprints chosen from available runs, a point outside the northern grid, edge cells, and locations with and without PRISM coverage. The earlier static-grid spot check is reconnaissance, not completed acceptance.

Determine the usable footprint from grid geometry and valid cells, not latitude/longitude extrema alone. Record selection distance, land/missing-value status, boundary proximity, and eligibility for every location and required hillslope. Define and justify any exclusion distance or boundary buffer before using it. Compare models and scenarios over matched windows.

Audit units, calendars/leap days, timestamp completeness, duplicate records, accumulation/reset conventions, missing values, temperature ordering, radiation, humidity/dewpoint, and precipitation totals and extremes. Compare historical seasonal means, wet-day frequency, dry/wet spell lengths, heavy precipitation, and temperature distributions against suitable independent reference data with documented coverage and period overlap. Distinguish quality defects from model bias and natural variability; do not compare future projections to observations as forecasts. Report finite-ensemble limitations and establish explicit acceptance tolerances with rationale before declaring suitability.

### M3 — CLIGEN and Multiple PRISM feasibility

Inspect `wepppy/climates/cligen/cligen.py`, `wepppy/nodb/core/climate_prism_build.py`, and climate build/scaling helpers. Document the mapping from EDDE variables to WEPP climate fields, which values are retained directly, and which CLIGEN must generate. Evaluate direct time-series conditioning versus changes to CLIGEN station parameters; select and justify a concrete workflow before implementation. Do not silently choose a bias correction or substitute station climate for missing EDDE variables.

Build reproducible historical and future single-location climate files using the existing CLIGEN executable and seed/provenance mechanisms. Assess storm duration, time to peak, peak intensity, wet-day treatment, solar radiation, wind, temperature, and dewpoint support. Do not claim hourly precipitation resolves subhourly erosion-driving intensity; inventory finer-frequency availability separately if needed.

Apply existing Multiple PRISM spatial revision at eligible project/hillslope locations. Preserve and test the EDDE historical-to-future signal; quantify seasonal precipitation ratios, temperature changes, wet-day occurrence, and extreme-event changes before and after revision. Document the PRISM reference period, variables revised, order of transformations, and avoidance of double scaling or double bias correction. Compare generated files across hillslopes, including hillslopes sharing an EDDE cell. Record unsupported combinations explicitly.

### M4 — Feasibility disposition and integration handoff

Deliver source inventory, client documentation, retained probe manifests, quality tables, acquisition benchmarks, generated climate evidence, and a go/conditional-go/no-go disposition by locale/model/scenario/period/spatial mode. A no-go supported by evidence is a valid feasibility conclusion; it must identify which workflows remain unimplemented or invalid. A go requires the executable evidence below and an accepted client/data contract. Transfer unresolved limitations to the successor package without labeling them complete.

## Complexity budget

Reuse the current Python climate-client, CLIGEN, PRISM, local cache, and WEPP execution mechanisms. Permit an additive client, bounded local extraction/cache, study scripts, and climate adapters. No new service, queue, datastore, daemon, dependency, privilege, or deployment topology is preauthorized. Escalation requires a retained failed acceptance test of the simpler approach, the smallest alternative, and its operational/recovery cost. No UI, route, RQ, deployment, or existing-project mutations in this package.

## Generated artifact validation and success criteria

- [x] Repeatable live extraction for actual U.S. and Canadian locations, plus explicit rejection of invalid/outside-grid requests; exact source keys, metadata, checksums, and timestamps retained.
- [x] Historical quality and future-signal assessments across available driving models, scenarios, and representative windows; limitations and justified tolerances retained.
- [x] Raw extraction to normalized input to CLIGEN-consumed input to fresh `.cli` file traced with semantic readback, binary identity, seed, and reproducible commands.
- [x] Single-location and Multiple PRISM climate artifacts exercised in fresh WEPP runs using the exact generated input; date/units, hillslope assignments, water-balance diagnostics, and output plausibility checked against explicit criteria.
- [x] Representative actual-project geometry used in isolated scratch copies; source projects remain untouched. Record runtime identity/environment and highest supported claim; no deployment claim follows from local success.
- [x] Conditional-go/no-go dispositions identify failed or untested criteria rather than checking them off. Successor implementation requires the applicable gates to pass.
- [ ] Focused tests and `wctl run-pytest tests --maxfail=1` pass for substantive implementation; documentation lint and correctness/security findings closed before implementation closeout.

Before any project-data/schema mutation, write a compatibility and regression plan. Preserve source data and existing field names; validate propagation to exact WEPP-consumed artifacts under `wepp/runs/` when applicable. Follow `docs/standards/generated-artifact-validation-standard.md` and `docs/standards/artifact-observability-standard.md`.

## Parameterization and review gates

**Parameterization change expected**: yes; **ADR required**: yes before merge of formulas, thresholds, unit conversions, spatial revision, or bias treatment. [ADR-0091](../../adrs/ADR-0091-edde-v2-experimental-daily-replay.md) records accepted experimental transformations; production scientific policy remains deferred. Capture operator provenance and scientific rationale per `docs/standards/parameterization-adr-standard.md`.

**Security impact**: high for implementation because the client adds external egress/file acquisition and exercises executable boundaries. **Dedicated security review required**: yes, under `artifacts/<date>_security_review.md` using the repository template. Review bounded requests, source/path validation, cache integrity, and executable arguments. Planning-only documentation introduces no runtime attack surface. Require a separate correctness artifact for production-bound behavior and no unresolved medium/high findings at closeout.

**Stakeholders**: operator/scientific decision owner; climate-client and CLIGEN maintainers; independent correctness and security reviewers during implementation.

## Dependencies and references

- [Initial source evidence](notes/source-evidence.md)
- [Tracker](tracker.md)
- **Blocks**: [EDDE v2 WEPPcloud integration](../20261013_edde_v2_weppcloud_integration/package.md)
- Existing contracts: `docs/schemas/climate-parquet-lineage-contract.md`, `docs/schemas/climate-precipitation-scaling-contract.md`, and `docs/schemas/prism-historic-climate-contract.md` (historic PRISM behavior is distinct from this proposed spatial revision).

## Current outcome

[Report and disposition](report.md): research extraction/replay is feasible; hold production integration. Completed 120 model-years/657,450 point-days, historical Daymet comparison, 42 full-period CLIGEN attempts (32 successful, ten quality-guard rejections), 24 PRISM attempts (21 successful, three inversion rejections), 69 successful 20-year WEPP runs, and actual-input development-container acceptance. These results support tested combinations only. No algorithmic bypass or corrective scientific policy was silently introduced.

Focused tests, API stubtest, and stub hygiene pass. The full-suite attempt exposed a preexisting SBS metadata assertion failure, reproduced in isolation; the continuation ended without a final result and independent reviews are recorded separately. Final focused validation passes 25 tests. The package stays open for the broad regression gate; study execution is complete. User-requested planning commit: `03435abc5`.
