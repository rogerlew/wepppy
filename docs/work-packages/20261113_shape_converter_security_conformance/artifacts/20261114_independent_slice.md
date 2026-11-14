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

Pending. No full conformance or deployment claim.
