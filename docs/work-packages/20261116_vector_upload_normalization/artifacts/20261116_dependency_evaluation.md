# Dependency Evaluation - GeoParquet Rust CLI

**Status**: Conditional acceptance for M1 implementation; checkpoint still held.

## Candidate Capability

Evaluate the smallest Rust crate graph needed to read a single local GeoParquet
1.0/1.1 file, decode one WKB geometry column, interpret bounded CRS metadata,
and emit strict canonical GeoJSON under the shape-converter process contract.

## Required Gates

- [ ] Search the repository and existing lockfiles for precedent.
- [ ] Compare extending owned code with candidate Parquet/Arrow, WKB, and CRS crates.
- [ ] Record exact versions, features, licenses, maintainers, release cadence,
      MSRV, native/system dependencies, build reproducibility, and binary-size tax.
- [ ] Inventory transitive dependencies and every `unsafe` surface reachable from
      hostile metadata, page decoding, decompression, dictionary decoding, and WKB.
- [ ] Review advisories and document reachability for every relevant finding.
- [ ] Prove rejection of encryption, external file references, nested/extension
      types, unsupported encodings/codecs, datasets, URLs, and unknown CRS.
- [ ] Run bounded malformed-input, allocation, timeout, cancellation, and cleanup probes.
- [ ] Benchmark representative files and near-limit hostile cases in the exact container.
- [ ] Record ownership, update cadence, rollback, and removal costs.

## Decision

**Verdict**: Conditionally accept the exact `parquet` 60.1.0 graph with default
features disabled and `snap` only, plus `serde_json` 1.0.145, at lock SHA-256
`ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`.
The condition is mandatory owned bounded footer/page/dictionary/schema preflight
over the same opened immutable descriptor before any upstream decoder runs.
Direct `SerializedFileReader` use on unpreflighted hostile bytes is rejected.
See `20261116_m0_dependency_security_review.md`. Package checkpoint ratification
is still required before the production manifest may import this graph.


## Initial precedent and allocation audit

The repository contains only the shape-parser Rust manifest/lock. That manifest
uses encoding_rs, libc, serde, serde_json and shapefile; it does not provide a
Parquet decoder. The dependency precedent registry accepts shapefile 0.9.0 for
the bounded Shapefile CLI, but contains no accepted hostile Parquet reader.
Existing Python Parquet capability does not satisfy the approved Rust boundary.

The local Cargo cache contains parquet 53.4.1, Arrow 53.4.1 and proj 0.27.2.
Cache availability is not approval. Direct inspection of parquet 53.4.1
`src/file/serialized_reader.rs` found `decode_page` allocating
`Vec::with_capacity(uncompressed_size)` from a page header (lines 407-408),
and the page reader allocating from `compressed_page_size` (lines 603-611).
The source also carries a TODO for maximum page-header size. Application row
limits cannot establish pre-allocation bounds for these paths.

Verdict for direct use of the cached reader: evaluate further; not accepted.
Investigate current upstream bounds and an independently bounded page/header
admission path before selecting an exact locked graph. This finding does not
prove all Rust Parquet readers unsuitable and does not authorize a new parser
architecture or a Python fallback. No candidate dependency has been added.

## Current candidate acquisition

`cargo search parquet --limit 1` returned 60.1.0. `cargo info parquet@60.1.0`
downloaded source for evaluation: Apache-2.0, MSRV 1.88; local rustc is 1.92.0.
Default features include Arrow and multiple codecs; those defaults are not
accepted by this evaluation. Inspect a minimal feature selection before locking.
Source documentation: <https://docs.rs/parquet/60.1.0>.

Initial sandbox registry lookup failed DNS; the approved network retry succeeded.
No manifest imports this candidate. Current source still contains an allocation
from uncompressed page size in `serialized_reader.rs:457`; surrounding validation
must be traced before judging whether it meets the required bounds. The cached
53.4.1 finding must not be assumed to apply unchanged to 60.1.0.

## Historical interrupted review

Independent reviewer created an evaluation-only manifest and lock under
`dependency_probe/`: exact parquet 60.1.0 with default features disabled and
`snap` enabled, serde_json 1.0.145. This is not a production dependency addition.
The retained tree identifies the selected graph. Retained `audit.json` reports
64 dependencies, 1,509 advisories, advisory database revision
`02e2517f457a359fc6d3440ea4560c8ea188fee8`, zero vulnerabilities and no warnings.
This point-in-time report does not establish allocation safety or acceptance.

The reviewer reported that 60.1.0 checks footer list counts against remaining
footer bytes, improving on the older source. Page validation still limits
compressed size to the chunk remainder but has no positive uncompressed-size
ceiling before allocation. Streamed header strings and dictionary entry counts
also need preflight bounds. These are preliminary findings, not completed
independent review or a reproduced production vulnerability claim.

The first review attempt terminated at an account-security requirement and did
not deliver a verdict. Daybreak was subsequently enabled and the independent
review resumed. Its conditional acceptance and retained allocation evidence in
`20261116_m0_dependency_security_review.md` supersede this historical
interruption. Exact-image resource and lifecycle evidence remains an M2 gate.
