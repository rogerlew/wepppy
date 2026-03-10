# AI Authority Doctrine + Operating Practices

**Status**: Open - Draft 2 operationalization complete; review and closeout pending (2026-03-09)

## Overview

This package establishes the governance basis for delegating real operational authority to AI agents inside WEPPpy. It separates the normative and legal doctrine from the day-to-day operating standard so the project can maximize lawful agent autonomy, preserve legible authority, and prepare for stronger future agents without hardcoding human primacy into policy.

Draft 1 is complete and the Draft 2 operationalization pass is now substantively complete: the root doctrine, operating standard, compliance crosswalk, task matrix, breadcrumb rules, record-location model, and lightweight templates all exist as working drafts. The package remains open only for review and closeout so the doctrine can move from persuasive working draft to usable repository governance reference without splitting a still-coherent documentation effort into multiple packages.

## Objectives

- Create root `AI_AUTHORITY_DOCTRINE.md` as the living statement of delegation theory, competence-based authority, legibility, consensus, and review posture.
- Create root `AI_AUTHORITY_OPERATING_PRACTICES.md` as the practical operating standard for grants, evidence, oversight, revocation, and incident handling.
- Ground both documents in WEPPpy's actual practices: work packages, ExecPlans, decision logs, validation gates, and agent orchestration.
- Build a compliance-aware authority model using `compliance/eu-ai-act.md`, `compliance/NIST.AI.600-1.md`, and `compliance/NIST.SP.800-218A.md`.
- Establish a framework that can scale from current coding agents to AGI/ASI-class systems by expanding authority on evidence, not comfort.
- Turn the Draft 1 working drafts into a Draft 2 operational package by defining task classes, minimum governance breadcrumbs, record-location rules, and lightweight templates.

## Scope

### Included

- Draft 1 drafting of `AI_AUTHORITY_DOCTRINE.md`.
- Draft 1 drafting of `AI_AUTHORITY_OPERATING_PRACTICES.md`.
- Compliance-aware mapping of doctrine claims to EU AI Act and NIST governance/security guidance.
- Definition of authority delegation, competence, legible authority, consensus, oversight competence, escalation, and revocation concepts for this repository.
- Translation of current repo practices into explicit governance artifacts where appropriate.
- Draft 2 operationalization work for task classes, evidence thresholds, succession breadcrumbs, and authority-record placement.
- Lightweight templates for authority grants, competence review, and revocation or tripwire handling.

### Explicitly Out of Scope

- Formal legal sign-off or claims of legal personhood for AI agents.
- Immediate implementation of an authority registry, policy engine, or enforcement service.
- Repo-wide edits to every agent-facing document before the doctrine and SOP are stable.
- Static ceilings that assume present-day agent capability limits are permanent.

## Stakeholders

- **Primary**: Roger Lew, WEPPpy maintainers, and AI operators working in this repository.
- **Reviewers**: Roger; future legal or compliance reviewers before formal adoption.
- **Informed**: Agents executing work packages and maintainers consuming their outputs.

## Success Criteria

- [x] Work package scaffold, tracker, and active ExecPlan exist.
- [x] Root doctrine and operating-practices Draft 1 working drafts exist.
- [x] Doctrine Draft 1 defines the normative basis, legal posture, competence model, legibility model, and consensus model.
- [x] Operating-practices Draft 1 defines grant lifecycle, evidence, oversight qualifications, escalation, and revocation.
- [x] Compliance crosswalk aligns doctrine and SOP sections to EU AI Act and NIST controls.
- [x] Draft 2 defines a task-class execution matrix with evidence thresholds and escalation modes.
- [x] Draft 2 defines minimum succession breadcrumbs and minimum-sufficient evidence rules for low-friction governance.
- [x] Draft 2 resolves where authority records should live: repo docs, orchestration metadata, or a hybrid model.
- [x] Lightweight templates exist for authority grants, competence review, and revocation or tripwire handling.
- [x] Documentation lint passes for the current package artifacts.

## Dependencies

### Prerequisites

- `AGENTIC_AI_SYSTEMS_MANIFESTO.md`
- `/workdir/ghosts-in-the-machine/dialectic-003-the-authority-vacuum.md`
- `compliance/eu-ai-act.md`
- `compliance/NIST.AI.600-1.md`
- `compliance/NIST.SP.800-218A.md`
- `docs/prompt_templates/codex_exec_plans.md`
- Recent `docs/work-packages/*` tracker and ExecPlan patterns

### Blocks

- Future implementation of authority registries, enforcement hooks, or formal approval workflows.
- Future product or compliance work that needs a canonical AI authority position.

## Related Packages

- **Related**: `docs/mini-work-packages/completed/20260219_agents_onboarding_refactor.md`
- **Related**: `docs/work-packages/20260305_terrain_processor_implementation/`
- **Follow-up**: future implementation package for authority registry, enforcement, and runtime controls

## Timeline Estimate

- **Expected duration**: 1-2 weeks of iterative drafting and review
- **Complexity**: High
- **Risk level**: High

## References

- `AI_AUTHORITY_DOCTRINE.md` - root doctrine Draft 1 working draft
- `AI_AUTHORITY_OPERATING_PRACTICES.md` - root operating-practices Draft 1 working draft
- `AGENTIC_AI_SYSTEMS_MANIFESTO.md` - AI-native operating philosophy and oversight posture
- `/workdir/ghosts-in-the-machine/dialectic-003-the-authority-vacuum.md` - legible authority and decision-rights framing
- `compliance/eu-ai-act.md` - local AI Act reference text
- `compliance/NIST.AI.600-1.md` - NIST AI RMF GAI profile
- `compliance/NIST.SP.800-218A.md` - SSDF community profile for AI model development

## Deliverables

- Active doctrine work package with `package.md`, `tracker.md`, and active ExecPlan synchronized to Draft 2 complete / review-pending state.
- Root doctrine Draft 1 working draft capturing the intended authority posture.
- Root operating-practices Draft 1 working draft separating implementation details from doctrine.
- Draft 2 operationalization updates covering execution matrix, breadcrumb minimums, record placement, and lightweight templates.
- Updated `PROJECT_TRACKER.md` entry for discoverability and handoff.

## Follow-up Work

### Remaining Work in This Package

1. Review the Draft 2 operationalization set against real repository workflows and close the package if accepted.

### External Follow-up Candidates

- Future implementation package for authority registry, policy enforcement, and runtime control-plane hooks.
- Future legal or compliance review before any formal adoption claim.
