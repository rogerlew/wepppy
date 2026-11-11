# Security review - Pickle artifact restriction

## Metadata

- **Package**: `docs/work-packages/20261110_pickle_artifact_restriction/`
- **Reviewer**: unassigned; implementation author cannot self-approve.
- **Date**: 2026-11-10 Pacific / 2026-11-11 UTC.
- **Scope reviewed**: initial source and contract assessment only.
- **Related artifacts**:
  - [Contract decision](20261110_contract_decision.md)
  - [Failure-class matrix](20261110_failure_class_matrix.md)
  - [Correctness review](20261110_correctness_review.md)

## Security Triage Decision

- **Security impact level**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: project-controlled files reach executable Python
  deserialization in browse and D-Tale server processes.
- **Threat model assumptions**:
  - A legitimate Bootstrap writer is not trusted with server code execution.
  - NUL absence does not establish serialization safety.
  - Existing pickle artifacts may be hostile even when their provenance is old.
  - Authorized raw byte download does not execute server-side content.
- **Valid states controls must preserve**: existing file listing/download and all
  currently supported non-pickle Bootstrap/preview/D-Tale formats.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-F2 | High | Bootstrap/browse/D-Tale | Project-controlled pickle reaches `read_pickle` | Pre-receive, browse flow, D-Tale registry | Complete restriction package | Open |
| SEC-F2A | Medium | Capability drift | UI, bridge, docs, or stubs may continue advertising removed support | Suffix tuples and docs | Remove all positive capability paths | Open |
| SEC-F2B | Medium | Rejection ordering | D-Tale bridge currently resolves/materializes before suffix admission | Browse D-Tale handler | Reject before downstream work | Open |

## Verdict

- **Gate status**: fail.
- **Unresolved findings**: High 1; Medium 2; Low 0.
- **Release recommendation**: hold until focused evidence and independent review
  close all findings.

## Required Surface Checks

- [ ] Both suffixes and case variants reject at every boundary.
- [ ] No request-time `read_pickle`, pickle reader registry, or permissive
      fallback remains.
- [ ] Bootstrap rejection precedes blob parsing and push logging.
- [ ] Browse/D-Tale rejection precedes materialization and outbound/internal load.
- [ ] Existing files are not opened during listing or download beyond byte stream.
- [ ] Supported formats retain their readers and lazy/eager constraints.
- [ ] Error messages disclose no file contents, tokens, or sensitive paths.
- [ ] Rollback cannot silently restore pickle parsing.

## Validation Evidence

- Automated runtime checks: pending implementation; focused list is in tracker.
- Source review: confirms two request-time readers and their advertisements.
- Live production checks: none.
- Full-suite status: intentionally not required by operator decision.

## Residual Risk

- Suffix restriction does not detect pickle bytes renamed to another extension;
  no remaining request path may choose a pickle parser for those extensions.
- Authorized clients can still download and deserialize files on their own
  machines; that client-side trust decision is outside the server boundary.
- Internal serialization uses remain outside this package's authorized class.

## Sign-off

- **Security reviewer**: pending.
- **Package owner**: pending.
