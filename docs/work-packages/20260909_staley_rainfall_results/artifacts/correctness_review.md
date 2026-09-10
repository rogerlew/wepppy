# Independent correctness review

Review date: 2026-09-09 Pacific. Scope:
[rainfall_io.py](../../../../wepppy/nodb/mods/postfire_debris_flow/rainfall_io.py),
[rainfall.py](../../../../wepppy/nodb/mods/postfire_debris_flow/rainfall.py),
[results.py](../../../../wepppy/nodb/mods/postfire_debris_flow/results.py),
the two new rainfall/results test modules, the local contract, and
[reproduce.py](reproduce.py). R02 is approved by the operator and documented in
[ADR-0062](../../../adrs/ADR-0062-staley-local-rainfall-results.md). Final
validation of its adapter and result-loader guards passes. No medium/high
correctness findings remain open.

## Findings

1. **Medium — persisted predictor acceptance does not enforce scientific
   consistency.** The initial `rainfall_io.py::load_predictors` accepted an
   available S with null K provenance, contradictory S multiplier, empty grid
   and outlet, and domain/support counts inconsistent with the pinned WBT
   summary. The controlled result fixture itself used available S with null K
   provenance. These inputs can produce complete probability tables while
   violating the accepted M1 preparation contract. Validate the existing
   structural invariants without reopening arbitrary provenance paths: K
   policy and multiplier/observed mean, geometry/area/domain, and WBT
   counts/bounds/support. Update the fixture to describe a coherent controlled
   bundle. **Closed:** K, F/S observed-mean, geometry, summary and support
   invariants are enforced; all corresponding direct-file probes return
   `invalid_input`.

2. **Medium — result loading validates encoding but not result semantics.**
   The initial `results.py::open_results` accepted empty mandatory metadata
   objects, wrong unit declarations, impossible numerical values, and repeated
   event/duration rows when hashes and Arrow schemas matched. Queries could
   consequently return probabilities outside [0,1], contradictory units, or
   duplicate events from a catalog described as validated. Validate manifest
   contents and row invariants, including request membership, event identity,
   unique complete duration sets, finite rainfall/unit conversion, status/reason
   consistency, and forward/inverse scalar consistency. Hash checks establish
   byte identity; they do not establish these schema invariants. **Closed:**
   manifest and row validators now check these invariants, including scalar
   forward/inverse parity and date-status consistency. Isolated direct-file
   mutations are rejected with `invalid_input`.

3. **Medium — NOAA parser permits contradictory scientific metadata.**
   `rainfall.py::frequency_csv` initially checked the first units line and
   partial-duration text but ignored `Data type` and the estimate-table heading.
   A copy of the genuine snapshot changed to `Data type: Precipitation depth`
   and `UPPER CONFIDENCE BOUND` still passed those checks and fed values to
   `noaa_design` as mean intensity. The frozen contract excludes depth and
   confidence-bound tables. Require the compatible data type and recognized
   estimate section; add direct-file negative cases. **Closed:** compatible data
   type and mean-estimate heading are required; the contradictory snapshot is
   rejected with `invalid_input`.

4. **Medium — reproduction does not pin its claimed predictor snapshot.**
   `artifacts/reproduce.py` checked the predecessor evidence digest but supplied
   a newly computed `digest(manifest)` as the expected predictor digest. It did
   not compare that manifest to the pinned evidence. A changed available F
   would therefore change the output while still passing the checks, because
   both scalar and hand-equation checks use the newly loaded predictor values.
   Record the known predictor manifest digest in `source_inventory.json`,
   verify it before building, and retain the connection to the pinned
   predecessor/source-overlap evidence. **Closed:** the inventory now pins
   `predictor_manifest_sha256`; reproduction checks it and compares predictors
   to the pinned predecessor evidence before composition.

5. **Medium — positive infinity could falsely satisfy CLI rank support.**
   The newly added `rainfall.py::cli_design` initially included positive infinity
   in its sorted series while reporting only finite positive samples. Two wet
   years with intensities `[inf, 40]` yielded available rank 1 with only one
   reported positive sample. **Closed:** affected duration design rows are now
   unavailable `nonfinite_intensity`; the direct-file case no longer produces
   an available result. The later approved sparse-rank policy is separate from
   this invalid-intensity handling.

6. **Medium — sparse-rank validation must also reject finite unsupported
   rainfall.** The first R02 loader guard checked the rank/count relation only
   for rows already labeled `insufficient_positive_samples`. A sparse row
   replaced with a numerically valid, finite last-observation result could
   therefore reopen with its unsupported rank/count. Require every CLI design
   row retaining rainfall to have nonnull rank/count and `0 <= rank < count`,
   including `missing_predictors` rows that retain valid rainfall. **Closed:**
   the loader now enforces supported ranks for all retained CLI rainfall. The
   direct-file clamped-result mutation is rejected with `invalid_input`; durable
   tests cover both complete and missing-predictor snapshots.

## Validation and closure status

The direct-file reproducer is `artifacts/correctness_probe.py`; it copies
genuine predecessor metadata/artifacts into temporary directories, mutates only
those copies, and constructs controlled result/source files. Run:

```bash
wctl run-python docs/work-packages/20260909_staley_rainfall_results/artifacts/correctness_probe.py
```

The current probe report is [correctness_probe.json](correctness_probe.json). Eighteen
independent malformed-input cases were rejected or returned unavailable, and
all twelve genuine CLI design combinations passed full-request rounded CSV
parity. The complete recurrence context was `[1,2,5,10,25,50,100]`; selecting
only requested 1/2/5/10-year rows did not change that rank context. The genuine
1-year, 15-minute result is 38.78638009814023 mm/hour, or
9.696595024535057 mm, at rank index 99 among 10,312 positive samples.

Initial execution intersected the loader extraction and exposed a temporary
undefined-`t` `NameError`. It was reported immediately and corrected before the
successful rerun. Documentation lint passes with zero errors or warnings.

## Coverage and residual scope

- R02 no longer has an unresolved approval gate. The owner approved unavailable
  sparse ranks. Count boundaries 0/1/9/10 preserve `no_positive_samples`,
  `insufficient_positive_samples`, or an available rank as appropriate. Full
  recurrence context and clamped CSV parity remain unchanged for supported
  rows and independent durations.
- Independent focused validation: `wctl run-pytest
  tests/nodb/mods/test_postfire_debris_flow_rainfall.py
  tests/nodb/mods/test_postfire_debris_flow_results.py -k cli --maxfail=1`:
  **7 passed**, 53 deselected. The sparse direct-file probe creates and opens
  30 event rows, 12 design rows and three inverse rows with an actual rounded
  CSV. Unsupported ranks 9/4/1 retain count 1 and null numeric outputs; the
  supported 30-minute accumulation values remain 45.5/48/49.5/50 mm.
  The parent’s final focused log also records **62 passed** after adding the
  complete/missing-predictor unsupported-rank regressions.
- Existing tests cover event unit conversion, duplicates, zero/missing/negative
  intensity, invalid dates, hash errors, basic NOAA parsing, full predictors,
  missing S, scalar inverse equality, deterministic ties, pagination, and
  interrupted/tampered outputs. Additional tests cover semantic mutations,
  partial F, and constant-response nonunique/unavailable inverse rows.
- The parent execution owns the complete full-suite and generated
  unknown-T/partial-F acceptance record. This bounded review did not rerun
  upstream raster preparation or the full repository suite; its additional
  validation covers local file boundaries, scalar/result consistency, and the
  approved sparse-rank delta.
- The local trusted immutable snapshot boundary does not establish current
  controller freshness, production integration, observed event dates, or a
  postfire recovery forecast. No auth, NoDb locking, RQ, or runtime production
  boundary changes are within this reviewed scope.
