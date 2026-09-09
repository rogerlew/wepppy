# Independent contract reviews

## Correctness review

2026-09-09 UTC, independent reviewer `/root/contract_correctness`, read-only.
No high findings. COR-01 (medium): legacy creation accepts `nodb:mods` overrides,
so requiring a module name while banning all request values contradicts valid
input behavior. Installation-only advice also misdiagnoses invalid overrides.

Disposition: the canonical contract now expressly permits the whole-message
bounded module identifier even when request-derived. Guidance covers verifying
the configured name or installing/enabling the required module. The checkpoint
regression matrix includes legacy overrides and hostile diagnostic strings.
Reviewer confirmation: COR-01 resolved; correctness contract gate passed with
zero unresolved high or medium findings.

## Security contract review

2026-09-09 UTC, independent reviewer `/root/contract_security`, read-only.
No high or medium findings. SEC-C01 (low): promote the exact whole-message
signature, grammar, and length bound from transient decision notes into the
canonical contract.

Disposition: the canonical contract now requires the entire message to match
`unknown mod <identifier>` with `[A-Za-z0-9_][A-Za-z0-9_-]{0,63}`. Review of this
change together with COR-01's narrow request-value exception passed: SEC-C01
resolved, zero unresolved high, medium, or low contract findings.

## Scope and remaining gates

The operator then authorized the checkpoint commit and all-create-failure
coverage. Both reviewers independently reviewed the expanded canonical section.
COR-02 (medium) required expanding the regression matrix beyond initialization;
the author added policy/auth/validation, service/identity, idempotency,
pre/post-allocation unexpected, and nonfatal TTL/README cases, preserving
303/Retry-After and lifecycle behavior. The correctness reviewer confirmed
COR-02 resolved and the expanded gate passed. Security requested two low doc
corrections (actual failure stage and the coverage cross-link); both were fixed
and confirmed. Both reviewers report zero unresolved contract findings.

These are pre-implementation contract reviews, not final correctness or security
evidence. Implementation remains untouched and checkpoint commit authority is
granted. Later evidence must cover both aliases, valid creation, legacy and
project-owned modes, safe classifications, unknown errors, original exception
precedence over cleanup, and formatted log correlation. No deployment approval
is claimed.
