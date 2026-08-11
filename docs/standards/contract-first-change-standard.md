# Pure UI and UI-Coupled Contract-First Change Standard

## Purpose

This standard applies to Pure UI and UI-coupled WEPPcloud, NoDb, and RQ behavior.
It prevents implementation from silently becoming the specification. Current canonical contracts define intended behavior. Source code, generated
artifacts, tests, runtime observations, and historical plans demonstrate or
explain behavior; they do not create normative intent.

## Canonical Authority

A contract is current and canonical only when it is in one of these finite sets:

1. Before GOV-00A convention cutover:
   - `docs/schemas/rq-response-contract.md`;
   - `docs/schemas/weppcloud-csrf-contract.md`;
   - `docs/schemas/output-scope-contract.md`;
   - `docs/schemas/nodb-persistence-concurrency-contract.md`;
   - `wepppy/nodb/mods/features_export/specification.md`, section 11;
   - `docs/ui-docs/controller-contract.md`, for shared runtime invariants only;
   - `wepppy/weppcloud/feature_registry/specification.md` and
     `wepppy/weppcloud/feature_registry/feature_registry.yaml`, for feature-menu
     metadata, discoverability, authorization, prerequisites, and active-state
     presentation;
   - `docs/adrs/ADR-0001-time-limited-publication-embargo-for-omni-contrasts.md`,
     for Omni Contrasts maturity, embargo, and disabled discoverability;
   - an operator-approved contract-decision checkpoint in the registered child
     package that owns the affected Pure UI obligation.
2. After GOV-00A convention cutover:
   - the cross-cutting contracts above;
   - `docs/ui-docs/controller-contract.md`, for the tests-first controller
     convention; and
   - the controller-specific canonical contract or concise intent matrix cited
     by the active registered child package.

This finite-set rule is exclusive only within this standard's Pure UI/UI-coupled
scope. Outside it, current canonical specifications explicitly named by the
nearest subsystem `AGENTS.md` remain normative and are not demoted by this
standard.

The GOV-00A package and child-package register govern ratification and ownership;
they do not substitute for a domain behavior contract. Unlisted UI documents,
migration inventories, archived work packages, and archived plans are evidence
or historical rationale only. Current implementation is authoritative only for
what is observed, never for what is intended.

If no current canonical contract covers intended behavior, stop. Use the
registered child package to create and ratify the contract before changing
implementation.

## Covered Implementation Boundary

Contract-first sequencing applies to intended behavior changes anywhere across:

- shared UI macros/helpers and rendered templates;
- controller fields, selectors, serialization, events, caching, and reload;
- transport methods, encodings, authentication, CSRF, and payloads;
- WEPPcloud and rq-engine parsing, validation, defaults, aliases, and errors;
- UI-coupled NoDb/server mutation, persistence, invalidation, and hydration;
- RQ enqueue sites, workers, dependencies, terminal/error states, and outputs.

## Valid-State and User-Experience Gate (Required)

Before implementation, enumerate valid runtime states separately from request
or flag combinations. At minimum assess absent or never-used optional state,
present-empty state, populated state, supported legacy state, and malformed or
hostile state. A claim of exhaustive coverage is valid only when it names both
the input matrix and the state matrix.

For every user-reachable exception, record whether the triggering condition is
expected or exceptional and cite the canonical contract that permits failure.
Expected absence of optional state defaults to create or no-op behavior when
that is necessary to reach an already-required final state; it must not be
reclassified as corruption merely because a safety helper requires an existing
object.

Security, locking, and containment controls are noninterference constraints on
valid behavior. Their review evidence must prove both sides:

- every valid state still reaches its contracted user outcome; and
- every malformed or hostile state fails without escaping its authorized
  boundary.

Correctness and user-experience review owns the first obligation. Security
review owns the second and verifies noninterference, but security approval
cannot substitute for correctness approval. At least one direct, unmocked test
must exercise each changed safety, persistence, or filesystem boundary; an
orchestration test that mocks the failing boundary is not conformance evidence
for that boundary.

## Required Pre-Implementation Checkpoint

For an intended behavior change, implementation files must not be edited until
all of the following are complete:

1. Create `artifacts/<date>_contract_decision.md` in the registered child package.
2. Record the starting implementation revision, every applicable contract, the
   exact normative delta, rationale, compatibility impact, security impact,
   discrepancy classification, and proposed regression evidence.
3. Record the operator's explicit approval of the intended behavior.
4. Amend every affected canonical contract. Mark implementation conformance as
   pending; do not claim the intended behavior is already deployed.
5. Obtain two independent read-only contract reviews and disposition their
   findings. An author cannot approve their own amendment.
6. Commit the checkpoint, contract amendments, and review disposition as a
   standalone ancestor commit. Record its revision in the child tracker.

Only after that ancestor commit exists may UI, route, NoDb, or RQ implementation
work begin. The implementation commit may include regression tests and supporting
documentation, but it cannot retroactively manufacture the checkpoint. Final
reviewers verify base revision, contract revision, commit ancestry, and review
timestamps.

If commit authority has not been granted for the child package, stop after the
accepted checkpoint is prepared and request that authority. Do not begin
implementation merely because the checkpoint is present in an uncommitted diff.

Any future automated enforcement must preserve this distinction. GOV-01 is
currently deferred pending measured controller-test evidence and explicit
operator approval.

## Bounded Cross-Owner Remediation

A production defect may span more than one registered future owner before the
normal dependency spine reaches those packages. The operator may authorize one
bounded remediation package to borrow only the affected obligations without
claiming those owner packages are executed, verified, or dependency-complete.
This exception is for a concrete defect with a finite implementation and test
surface; it is not a general way to start planned domain work early.

Before the borrowed-boundary package becomes a canonical checkpoint, all of the
following are required:

1. GOV-00A registers a stable remediation id, the dated package, every borrowed
   owner, exact source boundary, excluded behavior, and the operator's explicit
   authorization.
2. The remediation package lists every applicable contract, resolves conflicts,
   and amends authoritative metadata in the checkpoint ancestor. It cross-links
   the borrowed owners so their later audits inherit the decision and evidence.
3. Security impact is the highest expected impact of any borrowed owner. A
   formal security artifact is mandatory when any borrowed owner is `high`.
4. Two independent read-only reviews assess authority, scope containment,
   security, compatibility, and regression evidence; the primary agent
   dispositions every finding.
5. The checkpoint, contract/metadata amendments, GOV-00A registration, reviews,
   and disposition are committed together as a standalone ancestor before
   implementation files are edited.
6. Implementation and final review remain limited to the registered defect.
   Queue wiring, model parameterization, data schemas, and unrelated owner
   behavior remain blocked unless explicitly included and separately governed.

The remediation package closes only the registered defect. It does not advance
the evidence grade or execution state of a borrowed owner. GOV-01 must later
validate that the remediation decision and regression evidence are referenced
by each borrowed owner's canonical contract.

A GOV-00A governance amendment supporting one bounded remediation may close as
an independently reviewed milestone before the rest of GOV-00A closes. The
register must name that milestone as the remediation dependency, and the
standalone ancestor must include the milestone decision, standard/register
amendments, reviews, and disposition. Closing that milestone does not ratify or
close the remaining GOV-00A controller-test convention deliverable.

## Bounded Cross-Owner Enhancements

An operator may authorize one finite enhancement package that composes behavior
owned by multiple registered packages before their normal audit sequence runs.
This path is for a concrete requested capability with a small, exact source and
contract boundary. It is not permission to execute, close, or raise the evidence
grade of the composed owners, bypass their unrelated dependencies, or redesign
their domains.

Before a bounded cross-owner enhancement becomes a canonical checkpoint, all of
the following are required:

1. The child register assigns a stable amendment id, dated package, every
   composed owner, exact normative and source boundary, exclusions, security
   impact, and the operator's explicit authorization.
2. The package records the starting revision, every applicable canonical
   contract, exact intended delta, compatibility and data impact, regression
   evidence, and observable generated-output acceptance where applicable.
3. The operator explicitly approves the exact contract matrix and confirms that
   the package may compose the named owners without advancing or closing them.
4. Security impact is the highest expected impact of any composed owner. A
   dedicated security artifact is mandatory when any owner or changed surface
   is `high`.
5. Two independent read-only reviews assess authority, scope containment,
   security, compatibility, and regression evidence; the primary agent
   dispositions every finding and obtains post-fix confirmation for resolved
   high or medium findings.
6. The standard/register amendment, checkpoint, canonical matrix, reviews, and
   disposition are committed together as a standalone ancestor before
   implementation files are edited.
7. Implementation and final review remain limited to the registered
   enhancement. Unlisted parameterization, schemas, queue topology, auth,
   owners, and shared behavior remain blocked.

The enhancement closes only its finite composition. Each composed owner later
inherits the decision and evidence but retains its prior state and dependencies.
GOV-01 must evaluate recurring enhancement use before any generalized workflow
or enforcement is introduced.

## Conformance Fixes and Urgent Restoration

When current code contradicts an unchanged canonical contract and no intent is
changing, classify the work as a conformance fix. Record the unchanged contract,
discrepancy, and regression plan concisely in the controller package or tracker;
write the failing regression before the patch when practical. A routine
conformance fix does not require a standalone contract-decision ancestor or two
pre-implementation reviews because no normative decision is being made.
Normative contract behavior remains unchanged.

Make the smallest compatible patch, run the applicable focused and existing
broad tests, and obtain one independent correctness review for a production
change. Repeat security review only when the actual patch changes an attack
surface. Intended behavior changes still require the full checkpoint above.

For an urgent service restoration, the operator may defer the two independent
pre-implementation reviews only when the change strictly restores already-
canonical behavior. Before code edits, the checkpoint must cite the unchanged
contract, classify the strict restoration, define regression evidence, and
record the operator's explicit urgent authorization and UTC timestamp. Commit
that checkpoint as a standalone urgent ancestor and record its revision in the
tracker. If commit authority is unavailable, urgent implementation remains
blocked.

This path cannot add a field, default, alias, compatibility rule, authorization
rule, or RQ behavior. Any uncertainty about intent ends the exception and blocks
implementation. Complete both independent reviews and disposition before merge
or routine deployment. Final reviewers verify the urgent ancestor's ancestry,
authorization, and timing.

## Contract Conflicts

All applicable canonical contracts apply simultaneously. A shared/cross-cutting
invariant controls unless it explicitly permits a domain exception. A domain
exception must be cross-linked from both contracts and identify its bounded
scope.

When contracts conflict:

1. record the conflict in the checkpoint and each affected discrepancy ledger;
2. stop implementation;
3. identify every contract owner;
4. reconcile and cross-link every affected contract;
5. obtain explicit operator approval and two independent reviews; and
6. commit the disposition in the pre-implementation ancestor revision.

Where conflicts recur in executable controller behavior, retain a regression
test. Do not build a validator solely to encode a hypothetical conflict.

## Review and Documentation Gate

Reviewers reject a change when implementation precedes its required contract
checkpoint, an unlisted document is treated as normative, applicable contracts
are omitted, or code is used to infer intent. A conformance fix must prove that
normative behavior stayed unchanged.

Reviewers also reject production behavior changes when the valid-state matrix
is absent, user-reachable exceptions lack an explicit policy, security evidence
covers only hostile inputs, or mocks replace the boundary that can produce the
reported failure. Use
`docs/prompt_templates/correctness_review_template.md` for production behavior
and incident-remediation review artifacts.

Every production change also updates affected user, operator, and developer
documentation in the same final change set. Contract-first ordering is additive
to that repository-wide documentation obligation.
