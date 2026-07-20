# RQ Worker Agent Guide

## Contract Authority (Required)

- Follow `docs/standards/contract-first-change-standard.md` before editing UI-
  coupled RQ enqueue sites, workers, dependencies, completion/error behavior, or
  outputs. Other RQ domains retain current canonical specifications named by
  their nearest applicable guidance.
- Current canonical contracts define intent. Workers, tests, job trees, and
  historical plans are conformance evidence or context only.
- An intended behavior change requires the accepted contract-decision checkpoint
  and standalone ancestor revision before RQ implementation edits begin.
- A conformance fix restores the unchanged contract and adds regression evidence.
  If intent is unclear or contracts conflict, stop and ratify the resolution.

## Queue Wiring

- Update `wepppy/rq/job-dependencies-catalog.md` whenever enqueue sites or
  dependency edges change.
- Run `wctl check-rq-graph`; regenerate drift only with
  `python tools/check_rq_dependency_graph.py --write`.
- Validate changed wiring against a live job tree with
  `wepppy/rq/job_info.py` or the job dashboard.
