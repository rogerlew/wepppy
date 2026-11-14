# Independent remediation slice - 2026-11-14

## Authorization and contract checkpoint

Operator approved proceeding with independent IPC, exact-driver, and archive
remediation before sandbox feasibility. The specification's Independent
remediation contract and ADR-0142 govern this slice. Sandbox, compression-policy,
broader semantics, dependency release evidence, and deployment remain gated.

Independent reviewers `/root/ipc_contract_security` and
`/root/ipc_contract_correctness` approved the contract checkpoint. Required
conditions: descriptor-based regular-file checks, no symlink/FIFO blocking,
preallocation JSON budgets, duplicate/non-finite rejection, typed geometry
nesting, aggregate collection vertex limits, and fixed worker failure messages.
Correctness review required preserving Fiona GeometryCollections and noted that
removing inactive coordinates=None repairs a preexisting parent Shapely failure;
it is not established prior end-to-end parity.

## Red evidence

`wctl run-pytest tests/shape_converter/unit/test_parser_ipc.py --tb=short`:
8 failed, 21 passed. Failures: valid JSON unsupported, NFC and case-fold aliases
accepted, three extra-prefix cases accepted, decomposed spelling not normalized,
and bounds accessed before exact-driver rejection. Other malformed JSON tests
passed only because pickle rejects JSON; they need post-change validation.
The earlier M0 disposable executable canary remains the direct FC-01 red evidence.

## Implementation and validation

Contract checkpoint: `6712ba631`. Implementation is the following local commit
(recorded in Git history); no code was changed before that checkpoint.

Implemented strict JSON IPC (no pickle imports), descriptor-based payload file
admission, byte/depth/value/schema/finite-number/cardinality/coordinate checks,
atomic worker output, exact driver assertion and disabled plugin discovery,
NFC/case-fold archive aliases, and incomplete/optional prefix rejection.
Worker diagnostic streams go to DEVNULL; fixed exit codes preserve canonical
feature/vertex quota errors without parent buffering or content exposure.

Validation commands use the nine M0 modules plus
`tests/shape_converter/unit/test_parser_ipc.py` and
`tests/shape_converter/integration/test_parser_ipc_semantics.py` with `--maxfail=1`.
Consolidated result: **184 passed, 176 dependency-deprecation warnings in
66.38 seconds**. After adding an inert pickle-mapping rejection case, the IPC
module reran: **45 passed, 4 warnings in 8.88 seconds** (185 unique cases total).
An earlier consolidated attempt exposed a stale test assertion expecting
`text=True` on pipes; it was replaced with DEVNULL assertions before the green run. Scope remains limited to changed boundaries.
`wctl check-test-stubs` and broad-exception changed-file enforcement passed.
No parser IPC pickle/marshal remains in production Python source.

Real-worker readback covers XYZ Point plus null geometry, string/int/float/date/
null attributes, and binary MultiPatch producing two MultiPolygons within a
GeometryCollection. GeoJSON and GeoParquet are parsed and compared for values,
counts, type structure, bounds, CRS metadata, download headers, and scratch cleanup.
The existing baseline modules retain point/line/polygon/CRS/timeout coverage.

A disposable container using existing image
`sha256:88a982e44d316824f493c99d0c3a9a3db3e4800feef86ff2c65693677039162b`
and read-only current source repeated all four semantic cases successfully at
UID/GID 10001, read-only root, cap-drop ALL, no-new-privileges, PID 256, 1 GiB,
1.5 CPU, nofile 65536, hardened tmpfs, and internal service network. Each case
passed artifact readback and cleanup. This reused the M0 image with source mounted
and TestClient; it is not a rebuilt candidate, proxy, forest1, or production
acceptance run. No running service was restarted or reconfigured.

## Independent review disposition

- Security reviewer `/root/ipc_contract_security`: approved slice after explicit
  CRSError mapping and removal of unbounded diagnostics. Full closure remains gated.
- Code/correctness reviewer `/root/ipc_contract_correctness`: approved after narrow
  multipart exception handling and real-worker semantic readback. Supplemental
  1,000 deterministic random JSON trees matched exact value-count edges.
- QA reviewer `/root/ipc_qa`: approved after meaningful duplicate/non-finite tests
  and decoder-spy tests proving budgets apply before json.loads.
- All review approvals are conditional on final scoped tests passing; no unresolved
  slice finding remains. Full conformance is not approved.

## Shared consumers and remaining risk

The shared archive helper also serves culvert payloads, AgFields plant archives,
and landuse management uploads. Source inspection confirms their custom policies
still receive normalized paths: culvert delegates to payload validation, AgFields
checks `.man`, and landuse enforces safe root filenames. NFC/case-fold alias rejection
now applies at their shared admission boundary as well. No route/queue wiring changed;
no unrelated suite or downstream runtime acceptance is claimed for those callers.

The fixed JSON budgets do not prove worst-case memory safety at the container cap;
worker serialization still allocates output before enforcing its byte cap. The
missing second sandbox, readiness attestation, full malformed-sidecar/geometry
semantic matrix, compression-policy decision, current SBOM/linkage/CVE evidence,
and production-equivalent release acceptance remain open. No dependency upgrade,
production deployment, or issue closure occurred.

## Final hygiene

Scoped package/specification/PROJECT_TRACKER Markdown lint passed. ADR date
validation and ADR lint passed at the checkpoint. Test-stub validation passed;
broad-exception enforcement introduced no new broad catches. The package and
PROJECT_TRACKER are updated; unrelated preexisting edits remain preserved.
