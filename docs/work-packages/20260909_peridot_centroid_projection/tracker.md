# Tracker

## Status

2026-09-09 23:00 UTC: implementation and validation complete; closing package and publishing WEPPpy commit.

## Tasks

- [x] Reproduce root cause; discover build and export paths.
- [x] Commit authoritative contract and ADR.
- [x] Implement and test pointwise projection (51 Rust tests).
- [x] Build, vendor, and validate generated artifacts, including container CLI execution and actual MOFE soil prep.
- [x] Correctness self-review and closeout complete; Peridot main pushed at 3cef07b, WEPPpy publication accompanies this closeout.

## Decisions

Preserve pixel-index convention; fix only CRS conversion. Reuse one PROJ transformer per writer, constructed inside its worker task. Do not share native transformer contexts between parallel writers.

## Evidence and discoveries

Peridot main pushed at 3cef07b. WEPPpy topo checks: 158 passed, 4 skipped. Broad suite: 8146 passed, 72 skipped in 820.53 seconds. Generated coordinates agree with pyproj; eight affected hillslopes now write 0.0001 in nine OFEs. WBT/sub-field non-coordinate columns and slope bytes match a source-baseline build. TOPAZ baseline repeats themselves change geometry, so byte parity is not claimed. Prior vendored sub-field schema is older than current committed source.

Tooling friction: wctl doc-lint panics for files outside the WEPPpy repository root. The same markdown-doc linter run from Peridot validates its three edited docs successfully.

## Handoff

Durable decision: docs/adrs/20260909_peridot_centroid_projection.md, Context and change; canonical Peridot docs/contracts/watershed-output-contract.md, Centroid coordinate authority. Live data remains unchanged. Final binary hashes are in artifacts/release_manifest.json. Unrelated workspace changes were preserved and excluded from commits.
