# Support 23 soil input horizons

Status: Open, 2026-11-19 UTC. Owner: operator; implementer: Codex.

## Purpose and scope

Repair generated-soil capacity exhaustion, first observed in
`quasi-religious-allotment` on wepp1. Implement separate native input capacity
`mxhzin=23` while retaining calculation `mxnsl=10`, depth handling and physical
formulas. Integrate executable-aware Python serialization and execution checks,
validate actual generated artifacts, and prepare a paired Linux binary release
and rollout. Preserve historical binaries, project selections and uploaded soil
bytes. No horizon merging, conductivity changes or automatic default migration.

The national October 2026 SSURGO inventory proves a current-writer maximum of
21 horizons; 23 covers all 22 raw source horizons plus the 200 mm split without
relying on validity exclusions. This supersedes the eleven-horizon experiment
as implementation scope; its closed evidence remains historical.

## Complexity budget

Reuse the native reader, existing release JSON sidecars, canonical normalizer,
NoDb/RQ orchestration, wctl tests and canonical deployment tools. Permit one
bounded input limit and an integer sidecar capability, with propagation through
existing writers and a consumption check. No new dependencies, services, queues,
datastores, permissions or deployment topology. Escalation requires evidence
that this implementation misses the actual acceptance condition.

## Acceptance and artifact evidence

The 21-horizon Puaulu and eleven-horizon Zepol soils must pass the actual reader
and complete fresh native runs. Existing inputs must preserve baseline outputs.
Counts above 23 fail explicitly; old/unknown binaries retain a ten-input limit.
Generated raw, prepared/Disturbed, multi-OFE and channel soils must preserve
material tokens across normalization. Uploaded inputs remain unmodified and
must never reach an incompatible native reader silently.

An isolated copy of the original wepp1 project must run through real WEPPcloud
soil generation and preparation with the selected candidate binary, with input
readback, fresh model output and user-facing report evidence. All state must be
isolated from the original project and Redis identity. Record exact source and
binary hashes, runtime identities and mounts. Passing local fixtures is not
production recovery. Package scope prepares a release/rollout; production
activation and original-run recovery are separately reported actions.

## Security and correctness

Security impact: high because executable/input capability checks cross upload
and process-execution boundaries. Retain dedicated security and correctness
reviews; close medium/high findings. Authentication, permissions, paths and
queue wiring remain unchanged. Inspect valid legacy, missing, malformed and
mismatched sidecars as well as malicious count declarations. An independent
review is a required gate; distinguish self-review if independent review cannot
be obtained in this session.

## Parameterization and contracts

ADR-0148 will record capacity, scientific invariants, provenance and rejected
alternatives. Update the canonical generated-soil boundary and executable
selection contracts before implementation. No new production parameter default
other than the explicitly selected binary's declared input capacity is implied.

## Failure class and observation

Original failure: inserting 200 mm would exceed native ten-layer limit.
Historical native readers can silently discard surplus records. Inventory all
normalizer and raw-copy consumers. Health: matching declared/actual counts,
correct depths/properties, complete fresh hillslope/channel output. Danger:
truncation, silent binary substitution, altered uploaded bytes or old-input
numerical drift. Release observation starts with the isolated original run and
Puaulu case; subsequent production adoption must retain those evidence gates.
No temporary mitigation is planned.

## Execution and references

[Active plan](prompts/active/implementation_execplan.md), [tracker](tracker.md).
Prior evidence: `docs/work-packages/20261118_native_soil_input_capacity/` and
`docs/investigations/2026-11-18-ssurgo-input-capacity/assessment.md`.
Highest current claim: diagnosed and prototype evaluated, not integrated/deployed.
