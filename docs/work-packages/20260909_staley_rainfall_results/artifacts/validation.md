# Local rainfall/results validation

Status: complete local acceptance, 2026-09-09 Pacific; R02 explicitly approved.
No production deployment, controller mutation, climate acquisition or rebuild.

## Genuine source and generated artifact evidence

`source_inventory.json` pins genuine local Climate snapshots and complete Wallow
predictor/evidence manifests. Original run DEM/mask/outlet/SBS/K hashes match the
predecessor evidence. Climate is PRISM mode (5), CLIGEN station az020159, with
100 simulation year labels; it is not an observed postfire event catalog.
Both CSVs identify latitude 33.6837, longitude -109.3221. NOAA's station field
is None; its location metadata and Atlas 14 volume/version remain preserved.

`acceptance_summary.json` summarizes inspectable `generated/r02-cli` and
`generated/r02-noaa` bundles. Each contains 30,936 event duration rows
(10,312 wet events), 12 design rows and six inverse rows. Event and inverse
SHA-256 match across frequency sources; source-specific design SHA-256 differ.
The NOAA 1-year 15-minute input independently checks 56 mm/hour × 0.25 h = 14 mm
and the published M1 coefficient equation. Event sample probabilities and
inverse values are checked against the accepted scalar engine.

Build time is 2.24–2.28 seconds, validated open 1.22–1.24 seconds, list about
19 ms and event detail 1.8–2.0 ms. Peak process RSS is about 453,000 KiB,
including the existing package import/tabular stack; the initial scalar prototype
was about 400,000 KiB and 0.230 seconds for all 30,936 probabilities. Materialize
once to avoid repeated scalar computation for probability sorting. These are
measured local baselines, not deployment service-level guarantees.

`generated/historical-unknown-t` is explicitly historical diagnostic evidence,
not current-project acceptance: the older July 1 predictor bundle preserves
null point T, all 30,936 null probabilities and all valid rainfall. Controlled
pytest cases separately exercise partial F, missing S and constant-response
inverse nonunique/unavailable states.

## Reproduction

From repository root, create a fresh parent directory and run:

    wctl run-python docs/work-packages/20260909_staley_rainfall_results/artifacts/reproduce.py /tmp/rainfall-noaa-NEW --frequency-source noaa
    wctl run-python docs/work-packages/20260909_staley_rainfall_results/artifacts/reproduce.py /tmp/rainfall-cli-NEW --frequency-source cli
    wctl run-python docs/work-packages/20260909_staley_rainfall_results/artifacts/reproduce_unknown_t.py /tmp/rainfall-unknown-NEW

Each destination must not exist. Reproduction verifies frozen source digests and
writes manifest/table hashes, query examples, scalar checks and performance to
`acceptance.json`. It reads existing local predecessor bundles; those authentic
binary artifacts must remain available. No script acquires or rebuilds them.

## Local query example

From repository root, this queries the retained CLI bundle using its recorded
manifest digest and returns the highest-probability 15-minute event plus all
three duration details. Each API result also includes predictor/area context.

    wctl run-python -c '
    from pathlib import Path
    from wepppy.nodb.mods.postfire_debris_flow.results import open_results, list_events, get_event
    catalog = open_results(Path("docs/work-packages/20260909_staley_rainfall_results/artifacts/generated/r02-cli"), expected_manifest_sha256="78558b2980e0506b65217ffd09e34482d4f7bc6a257042a4c21f4545d5bc3341")
    page = list_events(catalog, duration_minutes=15, sort="probability", descending=True, limit=1)
    print(page["rows"])
    print(get_event(catalog, page["rows"][0]["event_id"])["rows"])
    '

## Tests and review

- Focused `wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_rainfall.py
  tests/nodb/mods/test_postfire_debris_flow_results.py --maxfail=1`: **62 passed**,
  two existing dependency deprecation warnings. Final approved-policy run: 10.13 s.
- `wctl check-test-stubs`: passed. No `.pyi` or existing stub API changes.
- Final `wctl run-pytest tests --maxfail=1`: **8,273 passed, 77 skipped**,
  3,110 warnings in 912.43 s (15:12), exit 0. This run collected all 62 focused
  cases and exercised the final runtime. The prior baseline (8,244/77) is kept
  in `logs/full-baseline.log`; one intermediate run was stopped after 246 passes
  to incorporate the last persisted-rank consistency guard.
- Correctness review: six medium findings closed; 18 direct invalid-state
  probes plus 12 genuine CLI scenarios with complete-request CSV parity.
- QA review: pass implemented paths; no medium/high findings. Low follow-ups
  concern splitting the long row validator and richer row-context diagnostics.
- Security review: pass implemented paths; 29 direct file/query checks, no
  unresolved findings. Correctness and QA closure are incorporated in the
  dedicated security artifact.

Doc lint passed for the module (15 files), work package (10 files) and ADR
(1 file), with zero errors/warnings. `git diff --check` passed. Original
Climate artifact hashes were rechecked after both source builds and remained
unchanged. Final logs are retained under `artifacts/logs`.

## R02 acceptance

The operator explicitly approved unavailable sparse ranks. Controlled
`generated/r02-sparse` uses pinned real predictors and a labeled synthetic
10-row climate, with CSV generated by the unchanged Climate exporter. Three
unsupported 15-minute scenarios remain unavailable; the supported 10-year row,
all 30-minute rows and source-independent inverse results remain intact. Empty
60-minute samples report no_positive_samples. The completed bundle reopens and
queries successfully. All genuine CLI/NOAA table hashes match before/after R02.

    wctl run-python docs/work-packages/20260909_staley_rainfall_results/artifacts/reproduce_sparse.py /tmp/rainfall-sparse-NEW

The final persisted-table guard rejects finite rainfall at unsupported CLI ranks,
including rows with unavailable predictors. ADR-0062 and the canonical contract
record approval, semantics and rationale. The final full suite and all independent review gates pass; the plan is
archived. Production stages 5/7 remain outside this local package.
