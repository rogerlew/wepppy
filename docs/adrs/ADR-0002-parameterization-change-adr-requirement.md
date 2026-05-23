# ADR: Require ADRs for Parameterization Changes

Status: Accepted  
Date: 2026-05-22  
Review Date: 2027-05-22

## Context

WEPPcloud parameterization changes are frequently decided in recurring meetings (wepp-in-the-woods) while implementation is done later by single maintainer (Roger). Without a durable decision record, future maintainers cannot reliably recover why a parameterization changed or who participated in that decision.

This creates avoidable re-litigation, weakens reproducibility, and burdens implementers with implicit ownership of decisions they did not make.

## Decision

Any change that modifies model or workflow parameterization must include an ADR in `docs/adrs/` before merge.

For urgent incident fixes that must merge first, the ADR must be added within one business day.

This requirement is universal across sponsors and funding sources. It applies equally to all sponsor-funded and non-sponsor-funded parameterization changes.

The required ADR fields and process are defined in:

- `docs/standards/parameterization-adr-standard.md`
- `docs/adrs/ADR-template.md`

## Decision Provenance

Decision Venue: WEPP-in-the-Woods workflow governance request, 2026-05-22 PDT  
Participants Present: Requesting maintainer and Codex implementation session  
Decision Owner(s): WEPPcloud maintainers  
Implementer(s): Codex

## Rationale

This requirement is about memory, not blame.

Capturing decision context and participants reduces ambiguity for future maintainers, improves scientific traceability, and avoids reliance on informal recollection or git archaeology alone.

## Alternatives Considered

1. Keep informal meeting notes only - Rejected. Notes are not consistently discoverable from code changes.
2. Use only work-package tracker decisions - Rejected. Not all parameterization changes originate in a single package, and tracker sections vary in permanence.
3. Rely on commit messages - Rejected. Commit messages rarely capture meeting provenance or alternatives considered.

## Consequences

- Positive:
  - Better continuity and reproducibility for scientific/model behavior changes.
  - Clearer separation between decision ownership and implementation ownership.
  - Faster onboarding and fewer repeated debates.
- Costs:
  - Small documentation overhead for each parameterization change.

## Implementation Notes

- `AGENTS.md` is updated to require this gate.
- Prompt/work-package templates are updated to include ADR checks.
- ADR index updated in `docs/adrs/README.md`.
