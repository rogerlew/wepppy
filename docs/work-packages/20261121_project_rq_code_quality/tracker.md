# Project RQ code quality tracker

## In Progress

- [ ] Extract WBT subcatchment job inspection and validation.
- [ ] Verify the project worker and real Redis state readback.
- [ ] Close the package and merge its PR.

## Decisions

- **2026-11-22 06:07 UTC** — Keep enqueue, registration, retry, and release
  logic in the worker module. Move the state readers and validator together
  with the metadata keys they interpret.
