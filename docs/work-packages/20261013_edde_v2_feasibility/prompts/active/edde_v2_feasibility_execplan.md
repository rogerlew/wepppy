# Execute EDDE v2 query and climate feasibility

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective with the package tracker. The executing package is `20261013_edde_v2_feasibility`; WEPPcloud integration remains deferred.

## Purpose / Big Picture


A researcher will query real U.S. and Canadian points from the public EDDE v2 archive, inspect provenance and quality, and produce historical/future CLIGEN climate files with optional existing Multiple PRISM spatial revision. Fresh WEPP hillslope execution and source-to-output comparisons establish feasibility, not application deployment or scientific suitability for every project.

## Progress


- [x] (2026-10-13 21:20 UTC) Planning documents committed as `03435abc5`; inspect existing clients, CLIGEN replay, PRISM revision, study fixtures, and running dev stack.
- [x] (2026-10-13 22:00 UTC) M1: Implement bounded public-archive discovery, native-grid eligibility, daily point extraction, CLI, and meaningful offline tests; retain live inventory and acquisition evidence.
- [x] M2: Probe both grids and actual-location matrix; measure historical quality, future signals, data completeness, and multidecade acquisition.
- [x] M3: Implement explicit experimental CLIGEN adapter and demonstrate single/PRISM climates and fresh WEPP outputs with preserved provenance.
- [ ] M4: Implementation/evidence delivered; focused tests and independent reviews pass, contract and ADR promoted. Broad regression gate remains open due to the preexisting SBS assertion; continuation is incomplete.

## Surprises & Discoveries


The first daily file inspected is NETCDF3_CLASSIC, despite the registry description of compressed NetCDF4. January humidity is 32,858,496 bytes; the 1985 daily MPI inventory has 84 files, seven variables, totaling 2,711,344,148 bytes. It has `time,y,x` arrays and unlimited time. Full monthly download is the simplest initial client; multiple requested points share acquisition. HTTP byte ranges work, but a new range parser is not justified before measuring this bounded approach. Daily fields are `husmean`, `prday`, `tsmax`, `tsmean`, `tsmean2`, `tsmin`, and `wspds`; radiation requires separate investigation.

Live inventory found MPI future daily coverage ending in 2099 and NorESM SSP2-4.5 ending in 2079, with no NorESM SSP3-7.0 directory. Use 2060–2079 for matched model comparisons, and retain MPI 2080–2099 as a distinct late-century experiment. Topanga's three sampled hillslopes and Miami select ocean-mask cells; eight Canadian cities select valid land cells. A 465-point-day precipitation comparison establishes same-labeled 00–23 UTC daily aggregation (maximum error 1.22e-6 mm). Pilot climate generation and 59 fresh WEPP runs passed; one PRISM target was rejected for daily temperature inversion, without clamping. The operator continued after the pending independent-review request; correctness and security reviewers were then engaged. Their concrete findings prompted rejection of invalid PRISM source files, protection of existing companion provenance, suppression of ambient netrc authentication, and additional seasonal wet-day/extreme diagnostics.

## Decision Log

Operator follow-up (2026-10-13): document PRISM inversions instead of treating them as a separate EDDE integration blocker. Code inspection and retained normals establish a generic independent-offset mechanism; other-dataset occurrence frequency is unmeasured. No executable change was requested or made.

On 2026-10-13 the operator clarified future-climate-only application scope and identified CLIGEN guard/quantization limitations as already known. Historical runs remain diagnostic evidence; solving existing CLIGEN limitations is not a new integration prerequisite. Preserve current safeguards and failure reporting. Bias interpretation, future auxiliary-field assumptions, and PRISM inversion policy remain separate questions; no new correction was authorized.


On 2026-10-13 the operator authorized commitment and end-to-end execution of the feasibility package. No UI integration or deployment is authorized by this package. Use public anonymous S3 over the existing requests and netCDF4 dependencies; add no dependencies. Reject unsupported requests explicitly. Preserve source units/calendar in raw extraction and put any CLIGEN conversions in a separately documented adapter.

The initial executable path is CLIGEN's existing daily replay (`Cligen.run_observed`), conditioned on EDDE precipitation and daily air-temperature extrema only after variable metadata confirms that meaning. This method name describes the executable interface; EDDE remains simulated, never labeled observations. Preserve generated-field attribution. Bias treatment, storm construction limitations, and retained station parameters must remain explicit; no new bias correction is inferred.

## Context and Orientation


`wepppy/climates/cligen/cligen.py` supplies `df_to_prn`, `Cligen`, `CligenStationsManager`, and `ClimateFile`. PRN is CLIGEN's daily precipitation/temperature input. The PRN writer expects a precipitation key containing `mm` to invoke mm-to-inch conversion and mutates its DataFrame, so pass a copy. `run_observed` can fail its quality guard; do not bypass it silently. `wepppy/climates/prism/__init__.py:prism_revision` multiplies monthly precipitation by hillslope/reference PRISM ratios and adds corresponding temperature differences. It uses existing metquery normals. Reuse it after eligibility and finite-normal checks.

Study fixtures and coordinates in `docs/work-packages/20261008_dewpoint_openet/artifacts/manifest.json` describe nine hillslopes in three actual watersheds. They are immutable historical evidence, usable as inputs after hash validation; place all new experiments under `/home/workdir/wepppy-scratch/edde-v2-20261013`. Do not change project state or old packages. New small scripts/manifests/results live under this package's `artifacts/`; large source files remain in the bounded scratch cache with keys, hashes, and reproduction commands retained. No NoDb/project schema mutation is planned.

## Plan of Work


M1 adds `wepppy/climates/edde/client.py`, package exports, and `__main__.py`. Discover objects using paginated S3 listings and select exact advertised variable/year/month combinations. Download only a preflighted byte budget, with explicit HTTP timeouts, object identity, safe paths, and incomplete-attempt diagnostics. Cache source objects with hashes and metadata; never trust a partial download. Read native projected grid axes and coordinate arrays from static land masks; transform requested WGS84 points into the advertised model projection and check cell-face bounds before nearest-cell selection. Verify geometry and land mask independently per model. Extract all points together per monthly file with strict calendar and missing-value checks. Public methods expose inventory, eligibility, and daily query, accepting explicit model/scenario/dates/points and returning tabular values plus JSON provenance. Tests use real miniature NetCDF fixtures and mocked HTTP transport only; live probes exercise real acquisition separately.

M2 records inventory for both model families and scenarios, timestamps at period endpoints, and actual U.S./Canadian/grid-edge/outside points. Start with a one-year query and measure cold and warm cost. Then collect matched historical and late-century multidecade windows within recorded request budgets. Evaluate data validity, seasonal means, wet days/spells/extremes, temperature, independent historical reference agreement, and scenario changes. Explicitly identify incomplete reference coverage and distinguish gross-invalid data from plausible biased climate. Scientific suitability does not follow solely from passing finite-value tests.

M3 adds `wepppy/climates/edde/cligen.py` only after metadata review and an ADR. It writes raw/normalized daily tables, PRN, station parameters, binary/seed metadata, climate files, and diagnostics into visible output directories. Validate source-to-PRN rounding, PRN-to-CLI temperature/precipitation preservation, and generated storm fields. Execute both baseline and future files through existing WEPP hillslope fixtures with retained hashes of exact consumed inputs. Repeat with PRISM revision at real hillslope coordinates, demonstrating seasonal signal preservation and recording rounding effects. Station-derived radiation, wind, dewpoint, and intensity remain attribution/acceptance limitations unless explicit source replacement is implemented and tested.

M4 updates client/user/operator documentation, a durable experimental contract, this plan and tracker, and the integration entry gate. Run focused tests then broad suite, stub hygiene, documentation lint, and changed-exception enforcement. Obtain independent correctness and security review artifacts required by root/work-package guidance; resolve actionable findings. A conditional/no-go is valid only with the measured reason and explicit unvalidated workflows, never as a substitute for completing executable tests that remain possible.

## Concrete Steps


Work from `/home/workdir/wepppy`. Use `wctl run-pytest tests/climates/test_edde_client.py tests/climates/test_edde_cligen.py` as new tests are added; run `wctl run-pytest tests --maxfail=1` before handoff. For live study commands use the existing host virtualenv `/workdir/wepppy/.venv/bin/python`, then reproduce executable acceptance through `wctl exec -T weppcloud` with the mounted paths. Update this section with exact implemented study/CLI commands and resulting evidence files. Do not install dependencies or restart the running stack.

## Validation and Acceptance


A passing query yields continuous daily dates, finite requested fields, eligible native land cells, and exact object/variable metadata for every value; invalid or outside requests fail explicitly. Compare extraction to direct NetCDF indexing. Repeated queries must match while showing measured cache savings. Historical assessment needs real overlapping observations/reference data, not comparison of future weather to observations. Climate acceptance parses exact `.cli` files, checks full daily precipitation/temperature within format rounding, verifies dates and meaningful storm fields, and runs fresh WEPP output. Multiple PRISM must preserve future/historical monthly ratios and additive temperature changes within declared rounding tolerance. No arbitrary numeric quality threshold may silently become a runtime default.

## Idempotence and Recovery


Operate exclusively on new scratch study directories. Existing projects and study fixtures are read-only. Use per-request/attempt manifests, atomic source-file promotion, and explicit incomplete statuses. Resume only after hash and selection verification; failed generation must not leave an old successful climate mislabeled current. Remove no diagnostic evidence. Download cache is reconstructible from pinned keys/identity metadata; study outputs remain visible and attributable.

## Artifacts and Notes


Retain source inventory, grid and location manifests, query timing/bytes/memory, raw/normalized point tables, historical/future quality tables, consumed-input/output hashes, binary and seed identities, logs, and reviews in the package. Source-file headers and representative direct parity checks supplement the live-study scripts. Measured evidence and production restrictions are summarized in `../../report.md`; compact source, generated climate, and exact consumer evidence archives are indexed in `../../artifacts/evidence-index.json`.

## Interfaces and Dependencies


Use existing `requests`, `netCDF4`, `numpy`, `pandas`, and `pyproj` for HTTP, NetCDF, array/table operations, and the native projection. These do not replace owned raster/hydrology kernels. Public S3 root is fixed at `https://epa-edde-v2.s3.amazonaws.com/`; no arbitrary source URL or credentials. Models are discovered `WRF-MPI`/`WRF-Nor`, scenarios from exact directory names, and years from inventory. The CLI must expose an inventory operation and a daily-query operation with explicit coordinates, period, variables, cache/output paths, and download budget.

## Outcomes & Retrospective


The 120-model-year study completed 657,450 point-days and 69 successful full-period WEPP executions. Ten of 42 CLIGEN attempts and three of 24 PRISM attempts were explicitly rejected; the 59-run pilot and development-container single/PRISM consumer checks succeeded. Historical biases and station-derived auxiliary weather prevent general production adoption. The full regression gate failed an unchanged SBS metadata expectation after 1,265 passes and 28 skips; isolated reproduction confirms it. A continuation ended without a final summary at approximately 34%, so it is incomplete coverage, not a passing gate. Final focused validation and independent reviews are recorded in the report. Initial plan authored 2026-10-13.

Final implementation and retained evidence were committed as `5dd665305`. Independent correctness and security gates pass with no unresolved implementation findings; 25 focused tests pass. The package remains open for the documented broad-suite regression gate, not additional data acquisition or integration work.

Scope clarification revision: corrected the handoff framing so diagnostic historical runs and known CLIGEN behavior do not expand the requested future-climate feature. Report, package scopes, durable contract, and trackers now record that distinction. Documentation lint passed; no executable behavior changed.

PRISM clarification revision: report and authoritative scope now distinguish the generic spatialization limitation from EDDE-specific findings, following operator direction to document it. Current experimental rejection remains explicit.
