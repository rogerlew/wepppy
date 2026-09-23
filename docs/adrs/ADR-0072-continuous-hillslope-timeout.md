# ADR-0072: Double the single-OFE continuous hillslope timeout

## Status

Accepted, 2026-09-23.

## Context and evidence

The production run `indistinguishable-keep` failed during its 1000-year
stochastic simulation. Parent job `d280184e-0cb4-420b-bf60-10f227533ce6`
reported failed child `3a895113-93b7-48f8-967e-1d65e2c3ae13` at
2026-09-23 20:34:56 UTC. Its traceback identifies `subprocess.TimeoutExpired`
after 60 seconds in `run_hillslope`, for `wepp_id=55`, using
`wepp_dcc52a6_hill`. All four attempts timed out; the last output of attempts
three and four reached 20 September of year 1000. This establishes a
per-attempt execution timeout, not a simulation-year limit or RQ job timeout.

Evidence: [production job tree](https://wepp.cloud/rq-engine/api/jobinfo/d280184e-0cb4-420b-bf60-10f227533ce6).
Read-only SSH checks confirmed host `wepp1`, checkout `/workdir/wepppy`,
the run directory in host and worker views, and running `rq-worker`,
`rq-worker-batch`, `rq-engine`, and `weppcloud` services. Production source
readback confirmed the 60-second service constant.

## Decision

`WeppRunService` shall pass a 120-second per-attempt timeout for single-OFE
continuous hillslope execution, doubling `_CONTINUOUS_HILLSLOPE_TIMEOUT_S`
from 60 to 120. The existing 300-second MOFE timeout, runner retry count,
standalone runner default, and RQ job timeouts retain their current values.

The scope is the requested literal timeout adjustment. No model inputs,
output schemas, persistence, permissions, or queue dependencies change.

## Decision provenance

- Venue: operator request in Codex chat, 2026-09-23 (America/Los_Angeles).
- Participants: requesting operator and Codex; Jackson N.'s incident report
  was quoted by the operator.
- Decision owner: requesting operator, who explicitly requested identifying
  the triggered timeout and doubling it.
- Implementer: Codex.
- Rationale: give the long simulation twice the execution budget at the
  confirmed failing boundary with a single reversible value change.

## Alternatives considered

- Increase the RQ timeout: rejected because the subprocess timeout fired.
- Change retries, MOFE limits, or standalone runner defaults: outside the
  confirmed failing setting and requested scope.
- Infer a 1000-year model limit: unsupported by the failure evidence.

## Validation and rollout

Validate by source readback and Python syntax parsing, following the literal
config-edit policy; no tests are added or rewritten to assert the value.
This repository change does not deploy to production or rerun the project.
A successful 1000-year simulation remains unverified until rerun after rollout.

## Risks and rollback

An actually stalled single-OFE process can consume twice the execution budget
per attempt. Revert the constant to 60 if the longer allowance causes
unacceptable worker occupancy. A repeated timeout requires fresh diagnosis;
120 seconds is not a guarantee of completion.
