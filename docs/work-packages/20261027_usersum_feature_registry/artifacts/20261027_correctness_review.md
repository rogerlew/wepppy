# Correctness and user-experience review

## Metadata and authority

Reviewer: `/root/catalog_contract_correctness`, 2026-10-27 UTC.
Contract ancestor: `96f7df370`. Reviewed Usersum route/template/index/tests and
supporting docs against Usersum specification, Public Feature Catalog, and
registry specification, Public Metadata Catalog. Final follow-up approved.

## User outcome and state coverage

Anonymous users receive all 18 feature and 16 configuration rows from real
validated loaders. The Usersum index links to the catalog. Config maturity
includes runtime overrides, including conservative Experimental handling.

| State | Required outcome | Evidence |
| --- | --- | --- |
| No account or run | Public catalog without initialization | Real anonymous route tests/readback |
| Empty registry | Explicit empty state | Empty/escaped metadata test |
| Populated registry | Every id, source order, correct maturity/policy | Five real-loader caller/query cases |
| Optional/legacy metadata absent | Neutral fields, ordinary anonymous eligibility | Real rows and optional metadata case |
| Malformed registry | Explicit loader failure, no partial success | Injected registry error test |
| Hostile display text | Escaped HTML | Real Jinja rendering of hostile label |

Request matrix: anonymous with/without internal role query; authenticated User,
PowerUser with user query, Root with internal query; proxy prefix; optional
trailing slash. Existing shell/document visibility tests remain passing.

## Error policy and evidence chain

Registry validation errors are exceptional and propagate under the current
registry failure contract. Empty optional values are expected, not corruption.
No persistence, run files, generated model intermediates, or recovery mutations
are involved. The HTML boundary consumes real loaded metadata; direct parsing
compares its complete row ids and maturity values. Real project execution and
archive/restore are inapplicable. Claim: locally validated, not deployed.

## Findings and disposition

COR-01 (medium): initial ordinary User policy wording implied authenticated
roles only. Corrected to no elevated role required, explicitly including
anonymous users subject to operation/launch permissions. Added focused assertion.
Reviewer confirmed closure after reading corrected source/test.

## Verdict and limits

PASS. Unresolved high/medium/low: 0/0/0. 219 focused tests passed; all eight
catalog tests passed again after COR-01. Source review and Flask HTTP/Jinja
readback do not claim browser visual or production validation. Light gates
explicitly requested by operator; broad Python/frontend suites omitted.
