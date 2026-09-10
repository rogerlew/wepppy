# Independent contract reviews and disposition

## Correctness review

Reviewer: /root/cancel_contract_correctness (read-only reviewer agent).
C-01, medium: generic process-pool tests omit CLIGEN's detached-session writer.
Required actual detached writer regression, unrelated process-group preservation,
pre-stop identity capture/equivalent containment, and lock retention when
termination evidence is incomplete.

Disposition: accepted. Canonical directory contract now explicitly covers
detached/reparented writers and unknown/denied termination evidence. Decision
state matrix and ExecPlan require detached-session regression, pre-stop identity
capture/equivalent containment, and preservation of unrelated process groups.
Also accepted the optional terminal-job and cancellation-race test clarification.
Post-fix confirmation: reviewer approved the amended checkpoint; finding closed.

## Security review

Reviewer: /root/cancel_contract_security (read-only security reviewer agent).
Medium: detached/reparented writers missing from concrete regression matrix;
retain locks with diagnostics if termination cannot be verified.
Low: explicitly test stale execution-A cleanup against same-job retry B.

Disposition: accepted both. Canonical termination rule and matrix amended as
above; decision and ExecPlan now explicitly require same-job retry coverage.
Post-fix confirmation: reviewer approved the amended checkpoint; finding closed.

## Validation and scope

Checkpoint/contract Markdown files passed wctl doc-lint; git diff --check
passed. No production implementation, process-boundary verification, or final
implementation security approval is claimed. Dedicated implementation security
review remains required before acceptance. Standalone checkpoint commit authority was granted on 2026-09-10 UTC.
