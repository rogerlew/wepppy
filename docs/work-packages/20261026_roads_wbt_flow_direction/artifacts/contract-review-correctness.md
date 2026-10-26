# Independent contract review: correctness and compatibility

Reviewer: `/root/roads_contract_review`. Date: 2026-10-26 UTC.
Scope: proposed ROADS-WBT-D8 contract and work package; read-only source inspection.
Base WEPPpy 69ddcafe9; native adapter 47e51b8; Peridot 3cef07b.

## Disposition

**PASS for the bounded contract checkpoint**, with one low documentation correction
below. This is approval of intended behavior and validation design, not a claim
that implementation, rebuilt artifact, project acceptance or deployment passes.
No medium/high findings.

The user explicitly authorized executing this repair after confirming Roads is
WBT-only. The contract correctly limits Roads to `wbt=True` without adding a UI
backend selector, while the native API preserves existing TOPAZ positional and
keyword callers by appending a keyword-only option defaulting to false. This is
an encoding correction and does not change a scientific parameter or add a
fallback. The supported legacy state is native TOPAZ input, not a non-WBT Roads
project.

The specified eight mappings match Peridot's conversion values and TOPAZ
`d8_offset` neighbor coordinates. Existing comments next to several conversion
arms are misleading, so independently specified row/column-neighbor tests are
necessary; comparing the adapter only to that same conversion would be circular.
The contract already requires independent expectations and real raster reads.

Security impact is low: conversion occurs in the already loaded native buffer;
no new path interpretation, authority, persistence, subprocess or queue behavior.
Keeping source rasters unchanged and publishing the paired `.so` by atomic rename
is appropriate. A stale extension must raise for the unsupported keyword, never
fall back silently. Fresh-process import/hash validation is required before any
end-to-end result is attributed to the rebuilt library.

The acceptance plan names both state and input dimensions: absent/unused Roads,
empty eligible set, populated WBT data, legacy TOPAZ callers and malformed raster
or seed/shape inputs; eight directions, invalid codes, loops, edges and step
limits. Existing lifecycle behavior remains authoritative for empty or failed
runs. Missing paths and invalid shapes retain explicit exceptions. Four NoData
outlets remain excluded; they are not evidence of a regression.

Actual-project acceptance extends beyond successful tracing: five recovered
segments must execute and appear in fresh report rows, with current receipt,
PASS/watershed completion and unchanged baseline/source hashes. Source snapshot
provenance and before/after outputs must be retained. Thirty-five completed
segments is an acceptance hypothesis until that full run proves it. The package
correctly distinguishes local/environment validation from deployment and repair
of the production project.

## Finding

**LOW C1 — correct the accounting-contract filename before checkpoint commit.**
`artifacts/20261026_contract_decision.md` names
`roads-modeled-area-accounting-contract.md`, which does not exist. The current
canonical file is `docs/schemas/roads-water-accounting-contract.md`. Correct the
reference so the checkpoint identifies its actual obligations. No normative
change to that accounting contract is needed for this encoding repair.

## Required closeout evidence

Implementation review must inspect the actual PyO3 signature, the explicit Roads
keyword, source-to-binary identity and existing-default parity. It must read the
fresh isolated project artifacts and retained negative cases rather than infer
correctness from mocked controller tests or a broad-suite pass. Production
rollout and original-project regeneration remain outside this checkpoint.
