# Interchange Parser Observability Standard

## Purpose

WEPP interchange converts model text output into Parquet datasets used by reports, exports, and operational diagnostics. A converter must never report success after silently losing a data-looking record. This standard makes source admission, rejection, and intentional emptiness observable across the WEPPpyo3 native readers and their WEPPpy callers.

## Applies To

Apply this standard to every WEPPpyo3 text-to-Parquet parser and to the WEPPpy code that invokes it. It covers new readers, producer-format changes, parser refactors, and incident repairs. It does not replace output-specific schemas; those schemas still define accepted fields and units.

## Terms

- **Header**: the recognized line that starts a table and defines how following lines are interpreted.
- **Non-data line**: a documented blank, separator, comment, or repeated header that is not a record.
- **Candidate record**: a line after a recognized header that has the record marker expected for that table. A candidate may be valid or malformed, but it is never silently ignored.
- **Accepted record**: a candidate successfully represented in the output dataset.
- **Rejected record**: a candidate that cannot be represented under a supported layout.
- **Intentional empty output**: a documented producer case where a recognized table validly contains no candidate records.

## Required Parser Contract

Every parser must:

1. Require a recognized header unless its input format has an explicitly documented headerless contract.
2. Classify each post-header line as either a documented non-data line or a candidate record.
3. Accept only explicitly supported layouts. A producer adds columns only through a documented compatible layout or an additive schema revision.
4. Return `InterchangeError::Parse` for a rejected candidate. The error must include the input path, one-based line number, expected layout or semantic requirement, and a bounded line preview.
5. Count candidate, accepted, and rejected records. A successful conversion must report those counts through the native binding and WEPPpy structured log.
6. Fail when candidates were encountered but accepted records are zero. Do not publish an empty Parquet artifact in that case.
7. Allow zero accepted records only for an output type with an explicit intentional-empty contract and a regression test proving that case.
8. Write atomically so a failing conversion cannot replace a prior valid artifact with a partial or empty one.

## Change Gate

Before changing a producer or parser layout, the change owner must:

1. Update the output-specific schema/reader documentation with every accepted layout and its field semantics.
2. Add fixtures for each supported layout and a negative fixture for malformed width, malformed value, and missing header behavior.
3. Verify accepted/rejected counts through the public native/Python interface.
4. Run a generated-output parse using the current model binary when the producer is available.
5. Update affected user, operator, and developer documentation in the same change set.

No fallback may silently discard unknown columns, unknown records, or failed numeric conversions. Compatibility must be explicit, bounded, and test-covered.

## Operator Signals

Successful conversion logs must identify the input/output paths and candidate, accepted, and rejected counts. A failure must name the parser, input path, line number, and reason. Operators should treat an empty interchange dataset from a non-empty model output as a defect until its intentional-empty contract is demonstrated.

## Regression Evidence

Each reader needs tests for a successful current-layout conversion, malformed candidate rejection, missing-header rejection where applicable, and its intentional-empty behavior if supported. The WEPPpy integration layer needs a test that a native failure remains an explicit job failure rather than an apparently complete post-processing step.
