# Pure UI and UI-Coupled Contract-First Change Standard

## Purpose

This standard applies to Pure UI and UI-coupled WEPPcloud, NoDb, and RQ behavior.
It prevents implementation from silently becoming the specification. Current canonical contracts define intended behavior. Source code, generated
artifacts, tests, runtime observations, and historical plans demonstrate or
explain behavior; they do not create normative intent.

## Canonical Authority

A contract is current and canonical only when it is in one of these finite sets:

1. Before Pure UI registry cutover:
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
2. After GOV-00A registry cutover:
   - the cross-cutting contracts above; and
   - domain/shared contracts listed by the ratified
     `docs/ui-docs/contracts/contract-obligations.json` registry.

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

GOV-01 change-aware enforcement must preserve this distinction. Same-change file
presence is not evidence of contract-first ordering.

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
close any other open GOV-00A schema, registry, template, or tooling deliverable.

## Conformance Fixes and Urgent Restoration

When current code contradicts an unchanged canonical contract and no intent is
changing, classify the work as a conformance fix. The checkpoint identifies the
contract, discrepancy, starting revision, and regression plan; normative contract
behavior remains unchanged.

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

Where conflicts are machine-representable, the GOV-00A/GOV-01 validators must
include a negative fixture or deterministic rejection.

## Review and Documentation Gate

Reviewers reject a change when implementation precedes its required contract
checkpoint, an unlisted document is treated as normative, applicable contracts
are omitted, or code is used to infer intent. A conformance fix must prove that
normative behavior stayed unchanged.

Every production change also updates affected user, operator, and developer
documentation in the same final change set. Contract-first ordering is additive
to that repository-wide documentation obligation.
