# Security review - Shape-converter security conformance

**Status**: Pending; mandatory high-impact gate

**Reviewer**: Unassigned; must be independent of the implementation author

**Candidate revision**: Not yet available

## Threat Boundaries

- Public upload to ZIP admission and request-scoped extraction.
- Selected sidecar set to native Fiona/GDAL open.
- Native parser worker to parent IPC.
- Parser process to API process, filesystem, network, signals, and resources.
- Readiness/configuration claim to effective runtime containment.
- Built image to native dependency/linkage/vulnerability evidence.

## Required Security Evidence

- Malformed, over-size, over-depth, non-finite, wrong-schema, and object-capable
  IPC cannot execute code or create/mutate a canary.
- Disguised formats fail at exact-driver admission.
- Unicode aliases, extra prefixes, expansion abuse, malformed sidecars, record
  mismatch, invalid geometry/ranges, and field collisions are dispositioned.
- The sandbox cannot read parent-only data, write outside output, use network,
  signal the API, or exceed process/resource limits; timeout kills descendants.
- Readiness fails closed when the sandbox/probe is absent or ineffective.
- Current runtime versions/linkage/image/scan are retained; no GDAL upgrade or
  hidden dependency drift occurred.
- Rollback cannot restore pickle IPC or an unsandboxed parser release mode.

## Findings

| ID | Severity | CWE / OWASP | Finding | Disposition | Evidence |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | High | CWE-502 / A08 | Existing executable parser IPC tracked in #655. | Open | Pending implementation. |
| SEC-02 | High | CWE-250, CWE-653 / A05, A06 | Existing ineffective second sandbox tracked in #656. | Open | Pending implementation. |

## Gate

**Decision**: Fail pending remediation and review. No unresolved Critical/High
finding may remain at package closure. A reachable Critical dependency finding
blocks closure but does not authorize a GDAL upgrade in this package.

## M0 prerequisite review - 2026-11-14

Independent reviewer: `security_reviewer` agent `/root/sandbox_gate_review`.
Reviewed source and supplied namespace/Bubblewrap probe results. Stop at M0;
selected candidate cannot initialize under tested restrictions. This does not
identify the exact denying control or establish that every mechanism is infeasible.
SEC-01 and SEC-02 remain High/open. Full implementation review remains pending.
See [receipt and resume gate](20261114_m0_baseline_and_sandbox_probe.md).

## Independent slice review - 2026-11-14

Reviewer: `/root/ipc_contract_security`. Approved the independent IPC/driver/archive slice,
conditional on final scoped tests passing. Findings and fixes are recorded in
[the slice receipt](20261114_independent_slice.md#independent-review-disposition).
This is not full package approval; sandbox, resource, dependency, and release gates
remain open. The earlier pending gate applies to full conformance closure.
