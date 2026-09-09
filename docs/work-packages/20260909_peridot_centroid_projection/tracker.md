# Tracker

## Status

2026-09-09 UTC: active; scope and compatibility plan recorded before implementation.

## Tasks

- [x] Reproduce root cause; discover build and export paths.
- [ ] Commit authoritative contract and ADR.
- [ ] Implement and test pointwise projection.
- [ ] Build, vendor, and validate generated artifacts.
- [ ] Correctness review, closeout, commit and push both repositories.

## Decisions

Preserve pixel-index convention; fix only CRS conversion. Reuse one PROJ transformer per writer, constructed inside its worker task. Do not share native transformer contexts between parallel writers.
