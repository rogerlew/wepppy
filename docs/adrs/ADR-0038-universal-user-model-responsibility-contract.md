# ADR-0038: Universal User Model-Responsibility Contract

Status: Accepted

Date: 2026-08-03

Review Date: 2027-08-03

## Context

The WEPPcloud User Guide already stated that model outputs are approximations,
required independent verification before consequential use, and assigned users
responsibility for decisions and consequences. It did not state with equal
clarity that users are also responsible for reviewing automatically selected
or generated inputs, model configuration, and parameterization. The stronger
parameterization language appeared only in suggested PowerUser training text.

That split could imply that ordinary users, automated setup, successful model
completion, or a `stable` feature label transfers scientific responsibility to
WEPPcloud. It does not.

## Decision

Adopt one universal responsibility contract for anonymous, ordinary,
PowerUser, and internal workflows. Users are responsible for:

- selecting and reviewing input and uploaded data, model configuration,
  parameter values, and parameterizations, including values WEPPcloud selects
  or generates automatically;
- determining whether the model, assumptions, parameterization, site,
  conditions, scale, and intended use are compatible;
- independently evaluating and validating outputs using site-specific
  observations, qualified professional judgment, comparison evidence, or other
  methods proportionate to the consequences of error; and
- deciding how outputs are interpreted, communicated, published, or applied.

Automation, defaults, successful completion, and `stable` maturity do not
certify calibration, validation, accuracy, or fitness for a particular purpose.
The canonical user-facing statement is the Legal Disclaimer in the WEPPcloud
User Guide. Release-governance and role-specific onboarding must not weaken it.

## Decision Provenance

Decision Venue: Codex API workspace thread, 2026-08-03 PDT

Participants Present: requesting WEPPcloud operator; Codex

Decision Owner: requesting WEPPcloud operator

Implementer: Codex

## Change Summary

Old contract: users bore responsibility for decisions and consequences and
were required to independently verify outputs, while ordinary-user
responsibility for run inputs and parameterization remained implicit.

New contract: responsibility expressly spans setup, automated inputs,
configuration, parameterization, domain applicability, validation,
interpretation, communication, publication, and application.

This amendment changes policy language only. It does not change model inputs,
defaults, formulas, thresholds, access control, data retention, or runtime
behavior. It does not add click-through acceptance or claim that the wording
has received legal review.

## Rationale

Scientific responsibility begins before execution and continues after results
are produced. One universal statement is clearer than assigning output-use
responsibility generally while discussing parameterization responsibility only
for elevated roles.

## Alternatives Considered

1. Retain the existing disclaimer - rejected because parameterization and
   automated-input responsibility remained implicit.
2. Apply the stronger wording only to PowerUsers - rejected because ordinary
   and anonymous runs have the same scientific interpretation risks.
3. Treat successful or stable workflows as validated - rejected because
   operational maturity does not establish site-specific scientific validity.
4. Add mandatory click-through acceptance in this amendment - deferred because
   that is a separate authentication, UX, record-retention, and legal-review
   decision.

## Consequences

Users receive an explicit, role-independent statement of responsibility.
Documentation and future onboarding or result surfaces must remain consistent
with it. The amendment does not reduce WEPPcloud's responsibility to disclose
known defects, limitations, provenance, or feature maturity accurately.

Legal counsel should review the disclaimer and any future acceptance mechanism
when contractual enforceability is required; this ADR records product policy
and scientific-use expectations, not a legal opinion.

## Evidence

- `wepppy/weppcloud/routes/usersum/weppcloud/user-guide.md`, Legal Disclaimer
- `wepppy/weppcloud/routes/usersum/weppcloud/feature-maturity-and-release-governance.md`, Core Principles and PowerUser Training Text
- Operator request and clarification in the 2026-08-03 Codex API workspace
  thread

## Risk and Rollback Notes

The principal risk is inconsistent wording across duplicated UI surfaces.
Landing-page or action-boundary conformance changes remain subject to their
applicable contract-first review and build gates. Rollback restores the prior
policy text and records why responsibility for parameterization should again be
implicit; it does not alter stored runs or model results.

## Implementation Notes

The authoritative documentation is amended in this change. Generated Usersum
search indexes remain governed by their normal build workflow. Do not hand-edit
generated indexes.
