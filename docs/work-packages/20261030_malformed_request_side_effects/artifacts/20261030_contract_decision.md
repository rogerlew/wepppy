# MRS-01 pre-implementation contract decision

Date: 2026-10-30. Starting implementation revision:
`e35d7a3e69497ddfd9709736af50107f56963584`. Checkpoint revision: **not committed**.

## Authority and classification

The operator requested execution of `/tmp/malformed-request-side-effects-repair-prompt.md`,
retained in `../prompts/active/repair_request.md`. Its explicit outcome is
“Reject malformed requests before side effects, preserving intentional empty/default
requests,” including equivalent confirmed consumers. It explicitly withholds
independent commit authority. No production implementation edits precede the
required accepted standalone ancestor checkpoint.

Classification: bounded cross-owner remediation, including normative clarification
of malformed transport, scalar flags/aliases and error ordering. Do not claim it
is solely conformance to an unchanged contract. SUDI already requires validation
before settings changes; several promotion/late-validation paths contradict that
rule. WAM-01 admission protection is unchanged and remains a constraint.

## Canonical amendments and applicability

The exact proposed normative matrix is in `docs/schemas/request-payload-contract.md`.
Amended integration contracts: `rq-response-contract.md` (400 envelope),
`rq-webhook-contract.md` (new reservation after validation),
`wepp-run-input-contract.md` (supplied flag/numeric validation under WAM-01),
`single-user-defined-inputs-contract.md` (bounded parsing and promotion order),
`rq-engine-agent-api-contract.md` (client guidance), and
`weppcloud-csrf-contract.md` (unchanged auth/CSRF precedence).
These seven paths are under `docs/schemas/`. Also amend
`docs/ui-docs/contracts/wepp-hillslope-clipping-contract.md` User Controls and
Validation and Failure Behavior: its earlier malformed-length no-update/infinity
exception rule conflicts with MRS-01 and is explicitly superseded for new malformed
requests. Preserve exact numeric alias precedence, no-update sentinels, finite
fractional conversion and existing persisted zero/negative/non-finite runtime
handling. This reconciliation is within the operator-authorized invalid-to-default
failure-class repair; it changes no slope formula/default or valid finite value.
Both independent reviewers must confirm the reconciliation. Implementation remains
explicitly pending.

Domain authorities remain additive: project-owned config and creation policy;
landuse modification; fork-console; Omni thinning/freshness; Roads preparation;
current NoDb persistence/concurrency and RQ errors. This checkpoint neither
advances their separate work packages nor alters domain schemas, scientific
ranges/formulas/defaults, queue topology or access policy. Any newly discovered
conflicting domain rule requires reconciliation and reviewed checkpoint amendment
before implementing that conflicting behavior. Preserve historical `kslast` rules.

## Delta and rationale

Reject invalid transport rather than conflating it with intentional empty input.
Keep headerless JSON compatibility, media-type-selected parsing, existing form/
list/upload adapters and zero-byte/default operations. Keep decoder duplicate-key
behavior rather than introducing a custom parser. Validate raw scalar flags before
container normalization, accept established tokens/0/1, reject arbitrary truthiness,
resolve alias/form conflicts, and preserve explicitly enumerated null/blank policies.
Validate supplied values before the first business effect, including early optional
state creation/recovery and file promotion; adapt enclosing error handlers so client
errors do not become 500/HTML. Do not promise rollback of later operational failures.

The alternative of changing only the shared parser misses direct Flask parsers,
webhook-only default operations, local broad catches and early writes. Globally
requiring JSON or nonempty payloads would break current default/form callers.
Universal scalar coercion would damage legitimate collections and raw strings.
A new framework/service or transaction layer is unnecessary for this bounded repair.

## Security, compatibility and evidence

Security impact high: invalid requests can reach cleanup, writes, uploads and
external work. Preserve auth/CSRF/locks and valid-state noninterference. Only bounded
field errors may be public; do not leak body/paths/tracebacks. Dedicated security
artifact remains open until final implementation evidence passes.

[Consumer/state matrix](consumer-matrix.md) records confirmed defects and unresolved
candidates, source locations, callers, sentinels, first effects and required tests.
Safe baseline HTTP probe confirms both parsers' fallback and truthy flag behavior.
Required regressions cover every confirmed real route and exception wrapper,
representative real persistence/cache reload and valid follow-up, RHEM cleanup
sentinels, bounded multipart/no promotion, and retained five-route WAM-01 behavior.

## Reviews and checkpoint gate

Two independent read-only source audits completed. Both independent reviewers approved the revised checkpoint after dispositioning
null/blank/recorder, webhook/numeric and clipping-contract findings. See
`20261030_contract_reviews.md`; source audits alone were not treated as approval.
Retain both review verdicts in `20261030_contract_reviews.md`. After acceptance,
request explicit authority for a standalone checkpoint commit containing only this
package, its root tracker entry and the eight canonical files. Do not stage
unrelated PROJECT_TRACKER/Roads/research changes. Record the commit SHA in tracker
and verify ancestry before source/test implementation edits.

Operator explicitly authorized the standalone checkpoint commit with “yes” on
2026-10-30 after reviewing the manifest and required ancestor gate.
