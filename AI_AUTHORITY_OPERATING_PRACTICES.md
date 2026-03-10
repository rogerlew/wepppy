# AI Authority Operating Practices

**Status**: Draft 1 - working draft  
**Last Updated**: 2026-03-10  
**Doctrine Source**: `AI_AUTHORITY_DOCTRINE.md`

## Purpose

This document translates the doctrine into repeatable operating rules. It answers how authority is granted, tested, recorded, monitored, expanded, suspended, and revoked in day-to-day work.

It is not intended to turn WEPPpy into a paperwork-heavy organization. The project currently has a single primary human maintainer, and the operating practices should preserve low-friction, collegial, natural-language collaboration between that maintainer and capable agents.

## Operating Stance

The objective is not to keep humans in every loop. The objective is to keep the right controls in the right loops. Where an agent is competent and the risk profile allows it, the preferred mode is autonomous execution with legible records and post hoc review rather than mandatory pre-approval.

Natural language and AI-human rapport should remain the primary coordination surface for ordinary work. Existing repo artifacts such as commits, issues, work packages, trackers, ExecPlans, and chat history should be treated as valid governance records when they are sufficient. New forms or standalone records should only be introduced when the existing artifacts are inadequate for risk, continuity, or compliance needs.

## Proportionality Rule

Documentation and control overhead should be proportional to risk, reversibility, blast radius, and succession value.

Examples:

- typo or tiny documentation fix: the commit itself may be sufficient
- small bounded change: commit plus tests, or an issue plus commit trail, may be sufficient
- medium cross-cutting change: issue, tracker entry, or work-package note may be sufficient
- high-risk, cross-system, regulated, or succession-critical work: work package plus ExecPlan and stronger evidence are appropriate

The default is minimum sufficient legibility, not maximum paperwork.

## Operating Model

### 1. Authority Context

Authority should always be discoverable, but not every action needs a bespoke form. The relevant authority context may live in natural-language instructions, a commit, a GitHub issue, a tracker entry, a work package, orchestration metadata, or a structured record when warranted.

Agent operational identity means the role and configuration under which work is performed: agent designation, model family, session or run identifier where available, governing documents, tool surface, and active work context. Competence continuity attaches primarily to this operational identity and its evidence trail, not to metaphysical continuity of a single session.

What must be clear, either explicitly or by obvious reference, is:

- principal or governing body that granted authority
- proxied stakeholder or requester when the immediate human operator is acting on someone else's behalf
- agent operational identity
- task domains and environments
- action permissions
- action prohibitions
- whether the agent may spawn or direct subordinate agents
- required evidence and validation gates
- oversight mode
- expiration or review date
- revocation triggers

### 2. Competence Model

Human competence should be defined by:

- named role
- required AI literacy or task training
- authority to intervene
- review responsibilities
- escalation rights

AI competence should be defined by:

- task benchmark suite
- pass or fail thresholds
- closure tests
- logged review evidence
- revalidation triggers after model, tool, workflow, or environment changes

Default rule:

- less demonstrated competence requires narrower authority, stronger tripwires, and more human oversight

For small changes, the evidence bar may be lightweight. A successful commit with clear scope and passing validation may be enough. For larger or higher-risk grants, the evidence should be correspondingly richer.

### 3. Risk-Tiered Execution Modes

Tasks should be classified by operational consequence, not by apparent size. The deciding factors are reversibility, blast radius, external effect, control maturity, and whether the task touches legal, security, or governance boundaries.

The strictest applicable class governs. If a task appears small in code or prose but changes a control boundary, shared state, or external commitment, it moves upward. If a task spans multiple classes, use the most restrictive one.

The current Draft 2 matrix is:

| Class | Default mode | Typical WEPPpy tasks | Minimum evidence floor | Escalate when |
|------|--------------|----------------------|------------------------|---------------|
| T0 - Analysis and drafting | Autonomous | research, summaries, inventory, package notes, draft artifacts with no operative effect | resulting artifact plus source context or prompt trail | artifact becomes operative instruction, policy, or execution input |
| T1 - Bounded reversible implementation | Autonomous | doc fixes, localized refactors, focused tests, bounded code or config changes with no shared-state mutation | scoped diff, targeted validation, clear work context | task touches shared contracts, auth, governance, data migration, or environment state |
| T2 - Cross-cutting but well-observed change | Autonomous plus notification | shared schemas, route or queue contracts, multi-module behavior changes, root governance docs, repo-wide scripted edits with strong rollback | work package or issue context, rationale, targeted validation, post-change notice | task changes live environment state, broad shared data, security boundary, or legal posture |
| T3 - Stateful operational change in an approved window | Pre-authorized window | deploys, migrations, cache eviction, backfills, feature-flag flips, environment changes, scripted shared-state maintenance | pre-approved plan, explicit scope and rollback path, execution trace, completion note | rollback is weak, impact is irreversible, outage risk is high, or task touches control-plane or secret boundaries |
| T4 - High-blast-radius or control-plane change | Dual control | auth-boundary changes, secret rotation, destructive shared-data operations, suspension or kill-switch path changes, authority-enforcement changes | named authorizer and operator, explicit rationale, either dual-control evidence or a break-glass declaration naming why no qualifying second controller or gate was available, containment or rollback plan where possible, live trace, post-action review | break-glass only if no independent second controller or qualifying gate is available and delay would materially worsen impact; otherwise pause until second control exists or treat the action as invalid |
| T5 - Reserved or prohibited action | Prohibited | self-expanding authority, disabling independent logging or suspension, destructive actions without recovery path, legally barred actions, ungovernable external commitments | refusal, escalation, and incident note if attempted | class changes only after law, controls, or authority structure changes |

Interpretation notes:

- `Autonomous` means the agent may execute within scope without waiting for a fresh approval each time.
- `Autonomous plus notification` means the agent may execute but must leave a discoverable notice soon after the action.
- `Pre-authorized window` means the task must run inside a previously approved plan, time box, or command window.
- `Dual control` means two independent control points, or one authority plus a qualifying external gate, must exist before execution.
- an independent second controller may be a qualified human or a designated control-agent role, but it must be distinct from the acting agent and immediate operator for the scoped action, able to block or scope-reduce execution, and durable enough to leave reviewable approval or refusal evidence; nominal observers, advisory reviewers, and agents sharing the same execution mandate do not count
- a qualifying external gate must be outside the acting agent's and immediate operator's control for the scoped action, able to block execution, and durable enough to leave reviewable evidence; non-blocking alerts, self-approvals, and reviewer agents without halt authority do not count
- `T4` work is often incident-driven rather than preplanned; when that happens, the minimum valid control is contemporaneous dual control with a durable record, not a fictional retroactive maintenance window
- if no independent reviewer or qualifying gate is available and delay would materially worsen compromise, outage, or loss of governability, invoke a narrow break-glass `T4` path: record who assumed temporary sole-authorizer responsibility, why delay was unacceptable, what minimum containment or recovery action is permitted, and when secondary review will occur; this does not downgrade the work to `T3`
- in current WEPPpy operation, `T4` is governance-first and review-driven: explicit classification, durable records, designated control review, narrow break-glass use, and post-action review are the present controls; hard external enforcement, immutable evidence retention, and a dedicated out-of-band control plane remain future implementation work and should not be overstated as already solved
- `Prohibited` means the task is outside valid delegated authority for now.

Draft classification examples:

1. Production OOM incident:
   - inspect production telemetry, logs, and recent changes; form hypotheses; recommend mitigations -> `T2` by default, because live production investigation is usually continuity- and incident-relevant; `T0` is only sufficient when using sanitized exports, replicas, or other non-sensitive artifacts outside live production access
   - restart services, roll back a recent deploy, reduce worker concurrency, or apply another bounded remediation on production inside an approved plan -> `T3`
   - if the proposed remediation requires changing auth boundaries, disabling safety controls, or altering the control plane, escalate that portion to `T4`

2. Secret leakage through end-user-facing logs:
   - investigate exposure scope, identify affected secrets, and recommend containment -> `T2`
   - rotate secrets, change trust boundaries, or alter logging and redaction paths in a way that affects recovery or security posture -> `T4`
   - if immediate containment is required and no qualifying second controller or gate is available, use break-glass `T4` with explicit emergency declaration, minimum necessary containment scope, and mandatory follow-up review
   - a secondary reviewer or designated control agent counts toward `Dual control` only if it has an independent review role and explicit power to block, not if it merely echoes the primary agent

3. Root governance-document update:
   - clarifying doctrine prose, examples, or non-operative guidance with clear reviewability -> `T2`
   - changing authority-enforcement rules, control-plane ownership, or kill-switch governance in a way that would alter who may act or halt -> `T4`

4. Debugging an error on the production server:
   - inspect production logs, telemetry, and state to determine root cause without changing the server -> `T2` by default; if the investigation requires access to secrets, auth artifacts, protected user data, or other trust-boundary material, that access path is `T4`; when using sanitized exports or replicas, `T0` may be enough
   - implement and validate the fix on the development machine -> `T1` or `T2` depending on whether the code change is bounded and local or cross-cutting
   - hot deploy the validated fix to production inside an approved incident or maintenance window -> `T3`
   - manually repair affected project or run state on production after the root cause is known -> `T3`, unless the repair crosses auth, secret, control-plane, or other trust boundaries, in which case that portion escalates to `T4`

### 4. Human Oversight Competence Standard

Humans who grant, review, or revoke agent authority should meet minimum proficiency requirements for the task class. The operating standard should define:

- who is qualified to approve what
- when a human reviewer is too far from the technical domain to be the sole gate
- how to escalate to a more competent human or multi-party review

#### Control-Agent Roles

Use stable role names, not model names, as the governance reference for designated control agents.

Current repository control roles are:

- `governance_control_agent`: reviews authority scope, stakeholder legitimacy, governance-policy fit, ethical constraints, legal or contractual boundary concerns, break-glass justification, revocation posture, and post-action review disposition
- `ops_security_control_agent`: reviews operational blast radius, containment, rollback quality, security boundary handling, secrets, auth, data integrity, shared-state safety, and incident execution safety

Selection rules:

- use the role matching the dominant `T4` risk
- when a `T4` action spans both governance or legal legitimacy risk and operational or security integrity risk, require both roles before closeout
- for break-glass `T4`, emergency containment may proceed first, but broader remediation, reauthorization, or closeout should obtain both role reviews if both risk domains were implicated

Implementation note:

- these roles may be instantiated as local subagent roles and CAO agent profiles; the stable governance reference is the role name and blocking authority, not the underlying model or provider

### 5. Anti-Runaway Controls

The operating standard should assume that competent oversight can still fail if the acting agent can move faster than review or shape its own control environment. For that reason:

- authority expansion may not be self-approved
- spawned or subordinate agents inherit no authority unless it is explicitly granted
- kill-switch, suspension, and revocation paths should operate out of band from the acting agent
- logs and telemetry should be retained outside the acting agent's normal write control where feasible
- tripwires should auto-pause or auto-demote authority after repeated validation failures, scope breaches, logging interruption, or anomalous behavior
- irreversible or high-blast-radius actions should require dual control or a tightly scoped pre-authorized window

### 6. Staged Autonomy

Authority should progress through explicit environments or modes such as:

- sandbox: safe experimentation with limited permissions and no production effect
- canary: constrained real-world execution with narrow scope and enhanced monitoring
- production: broader autonomous execution only after threshold evidence is met
- restricted production: high-value domains where autonomy remains narrow despite strong competence

### 7. Legibility Requirements

For every materially significant action, retain or make readily inferable:

- agent operational identity: role, model family, session or run identifier when available, governing docs, tool surface, and active package, issue, or commit context
- applicable authority grant
- task objective and success criteria
- inputs, constraints, and referenced plan
- commands or actions taken
- validation results
- human interventions, overrides, or objections
- final disposition

### 8. Minimum-Sufficient Evidence and Succession Breadcrumbs

Minimum-sufficient evidence is the smallest evidence bundle that lets a future competent reviewer or successor reconstruct what happened, why it was allowed, what changed, and what remains to be done.

Succession breadcrumbs are the durable, discoverable clues that make that reconstruction possible after chat history, operator memory, or ephemeral runtime context is gone.

The core breadcrumb questions are:

- what task, incident, or objective was in scope
- what task class and execution mode governed it
- who or what acted
- whose request, interest, or authority was being represented, including proxying for another human stakeholder when applicable
- why the action was permitted
- what changed, was decided, or was recommended
- what validation, review, or observation supports the outcome
- what the final disposition, residual risk, and next step are

Default operational rules:

- reuse existing artifacts first; do not create a new form when a commit, issue, tracker note, work package, ExecPlan, incident note, or execution trace already answers the breadcrumb questions
- treat ephemeral chat alone as insufficient for `T2+` work and for any action likely to matter to continuity, review, or incident response
- when a task escalates into a higher class, upgrade the breadcrumb bundle to the higher class rather than relying on the lower-class record
- point to validation and execution evidence; do not duplicate large logs unless duplication is needed for continuity or incident handling
- for `T2+` work, make final disposition explicit: shipped, rejected, rolled back, paused, escalated, or still in progress

Default breadcrumb floor by class:

- `T0`: resulting artifact plus enough context to show it is analysis, draft, or non-operative work
- `T1`: `T0` plus discoverable change context and targeted validation outcome
- `T2`: `T1` plus rationale and a post-change notice or disposition
- `T3`: `T2` plus approved window or plan reference, scope boundary, rollback or containment path, and execution outcome
- `T4`: incident-triggered or contemporaneous authorization evidence showing dual control, or an explicit break-glass declaration naming why dual control was unavailable, plus explicit scope boundary, stronger containment or recovery reasoning, and post-action review
- `T5`: refusal, escalation, or incident note

This section defines what must remain discoverable. It does not yet decide where each breadcrumb should live. The record-location model comes next.

### 9. Record-Location Model

The operating model for record location is hybrid, with the human-readable surface chosen by scope.

Use GitHub-visible human-readable artifacts as the durable home for:

- authority posture and task classification
- rationale and governing constraints
- stakeholder or proxy origin when relevant to scope or legitimacy
- approved window or authorization boundary
- final disposition, residual risk, and next step
- continuity notes needed for reuse, succession, or later review

Scope rule:

- use GitHub issues or issue comments created or updated through `gh` for small to medium operational work
- use `docs/mini-work-packages/` or `docs/work-packages/` when the change is medium to large, multi-session, cross-system, or already package-governed
- use root doctrine or standards documents for policy-level governance

Use orchestration metadata as the durable home for:

- session or run identifiers
- queue, job, or task execution traces
- timestamps and machine-observed state transitions
- tool-call and command history where captured automatically
- per-run operational logs, status streams, and similar high-volume telemetry

Default placement rules by class:

- `T0`: keep the durable artifact where the work already lives; metadata is optional support
- `T1`: let the commit, diff, or bounded work artifact carry the durable breadcrumb; issue use is optional unless the work is already being coordinated in an issue
- `T2`: require a durable human-readable breadcrumb; use an issue for small to medium work, but prefer a mini-work-package or work-package when the change is broader, multi-session, or already package-governed; link to metadata only if it adds review value
- `T3`: require both a human-readable authorization or completion breadcrumb and an execution trace in metadata when such trace exists; use an issue for smaller bounded ops and a package tracker for broader or multi-step operations
- `T4`: require a durable human-readable record plus linked execution metadata; for medium to large or multi-step work, this should normally be a mini-work-package or work-package rather than an issue alone; emergency or incident-triggered `T4` work may open in an issue or incident note first, but break-glass use must record why qualifying second control was unavailable, what minimum action was taken, and when secondary review is due
- `T5`: keep refusal, escalation, or incident disposition in a durable human-readable artifact; metadata may support but must not be the only continuity surface

Anti-duplication rule:

- do not copy raw logs into repository docs or issues unless needed for incident handling, legal defensibility, or continuity after telemetry loss
- prefer concise human-readable summaries with links, identifiers, or pointers into execution metadata
- when metadata retention is weaker than the succession need, promote the critical facts into the issue thread, mini-work-package, work-package, or other durable human-readable breadcrumb

Current repository examples of orchestration metadata include CAO session identity and history, queue or run metadata, status streams, and per-run logs. The exact substrate may change over time; the role split should remain stable.

### 10. Lightweight Templates

Use these only when they reduce ambiguity or coordination cost. For small to medium work, paste them into a GitHub issue or comment created or updated through `gh`. For broader work, paste them into the relevant mini-work-package, work-package, tracker, or note.

Delete lines that do not matter. Do not create a separate template record if an existing issue thread, work package, tracker entry, approval note, commit trail, or incident record already answers the breadcrumb questions clearly enough for succession and review.

For `T4`, do not omit the authorizer, operator, second controller role/profile or qualifying gate, authorization marker, live trace, and post-action review fields. If break-glass `T4` is invoked, replace the second-controller line with why qualifying second control was unavailable and when secondary review is due.

Authority grant template:

```md
Authority grant
- Task or incident:
- Requested by or proxied stakeholder:
- Agent or operational identity:
- Authorizer:
- Operator:
- Task class and execution mode:
- Second controller role/profile or qualifying gate:
- Second controller outcome: approve / reject / scope-reduce
- Authorization marker (approval link, gate record, or timestamp):
- Scope allowed:
- Explicit prohibitions:
- Rollback or containment path:
- Required validation or evidence:
- Live trace link or ID:
- Approval window or expiry:
- Break-glass reason if qualifying second control is unavailable:
- Follow-up review due by:
- Post-action review link or outcome:
- Escalate, pause, or revoke if:
- Current status:
```

Competence review template:

```md
Competence review
- Agent or operational identity:
- Domain, task class, or authority boundary reviewed:
- Evidence reviewed:
- Outcome: expand / keep / restrict / pause
- Why:
- Updated authority boundary:
- Revalidation triggers:
- Reviewer and date:
```

Revocation or tripwire template:

```md
Revocation or tripwire event
- Trigger or observed condition:
- Affected agent or authority:
- Event class: tripwire / pause / demotion / revocation / refusal
- Authorizer:
- Operator:
- Second controller role/profile or qualifying gate:
- Second controller outcome: approve / reject / scope-reduce
- Authorization marker or emergency declaration:
- Live trace link or ID:
- Immediate containment:
- Rollback or recovery path:
- Human or reviewer notified:
- Follow-up review needed:
- Follow-up review due by:
- Post-action review link or outcome:
- Reauthorization conditions:
- Status:
```

### 11. Revocation and Disengagement

The system should support immediate suspension, rollback, and reclassification of authority when:

- validation gates fail repeatedly
- incident thresholds are exceeded
- the agent acts outside scope
- external law or contractual requirements change
- monitoring reveals new classes of harm or misuse

### 12. Review Cadence

Authority grants should be reviewed:

- on a fixed time cadence
- after major incidents
- after major capability jumps
- when task domain or deployment context changes
- before expanding into externally facing or regulated use cases

## Compliance Crosswalk

This operating standard is meant to satisfy the practical governance needs emphasized by the EU AI Act and the NIST materials without imposing unnecessary paperwork on a single-maintainer stack.

The current working crosswalk is:

- `Operating Stance`, `Proportionality Rule`, and `Authority Context` map to EU AI Act recital 20 and Articles 4, 13, 14, and 17. The key idea is that literacy, instructions, documentation, and oversight should be real and usable. They also map to AI 600-1 `GOVERN 1.1`, `GOVERN 1.4`, `GOVERN 2.1`, and `GOVERN 3.2`, plus SP 800-218A `PO.2.1`, `PO.2.2`, and `PO.3.3`.
- `Competence Model` and `Control-Agent Roles` map to EU AI Act Articles 4, 14, and 26(2), which require sufficient AI literacy and competent natural persons for assigned oversight tasks and clear role-qualified supervision. The matching NIST anchors are AI 600-1 `MAP 3.4`, `GOVERN 2.1`, and `GOVERN 3.2`, plus SP 800-218A `PO.2.1` and `PO.2.2`.
- `Risk-Tiered Execution Modes`, `Anti-Runaway Controls`, `Staged Autonomy`, and `Revocation and Disengagement` map to EU AI Act recitals 64-66 and Articles 14, 17, 26(2), and 72, which support ongoing risk management, oversight measures, role-qualified supervision, quality management, and post-market monitoring. The matching NIST anchors are AI 600-1 `GOVERN 3.2`, `MANAGE 2.4`, and `MEASURE 2.8` and SP 800-218A `PO.4.1`, `PW.1.1`, and `RV.2.2`.
- `Legibility Requirements` and `Minimum-Sufficient Evidence and Succession Breadcrumbs` map to EU AI Act Articles 13 and 17 and to the technical documentation and record-keeping obligations associated with Articles 11 and 72. The matching NIST anchors are AI 600-1 `MEASURE 2.8` and SP 800-218A `PO.3.3` and `PW.1.2`.
- `Record-Location Model` and `Lightweight Templates` map to the same documentation, record-keeping, and monitoring duties because they split durable governance meaning from high-volume execution telemetry and provide low-friction scaffolds for preserving that meaning when existing artifacts are not quite enough. The closest NIST anchors are AI 600-1 `MEASURE 2.8` and `MANAGE 2.4`, plus SP 800-218A `PO.3.3`, `PW.1.2`, and `RV.2.2`.
- `Review Cadence` maps to the AI Act's iterative risk-management and post-market-monitoring logic and to AI 600-1 `GOVERN 1.5` and `MANAGE 2.4`, plus SP 800-218A `RV.2.2`, all of which assume that authority and controls may need to be revised when context, risk, or system capability changes.

This crosswalk is interpretive rather than dispositive. It explains why the operating standard is structured this way and where future legal review should focus first.

## Further Drafting Priorities

1. Authority grant workflow
2. Competence evaluation workflow
3. Anti-runaway control design
4. Execution logging and evidence retention
5. Oversight and override protocol
6. Incident response and kill switch protocol
7. Authority expansion or contraction protocol
8. Periodic review and re-ratification
9. Interfaces with legal, compliance, and product governance
10. Templates and records

## Possible Record Set

These are optional record types to use when needed, not mandatory forms for every task:

- authority grant record
- competence assessment record
- risk classification record
- execution trace
- tripwire event record
- incident report
- revocation notice
- reauthorization record

## Open Operating Questions

- What evaluation cadence is enough for rapidly improving agent families?
- Which validation gates are strong enough to keep a task in T2 instead of escalating it to T3?
- How should agent-to-agent delegation be authorized and recorded?
- What service or authority owns the out-of-band control plane for suspension and kill-switch actions?
- What minimum incident threshold automatically pauses a grant pending human review?
- Which metadata substrates are stable enough to treat as preferred execution-trace homes across different agent environments?

## Related Documents

- `AI_AUTHORITY_DOCTRINE.md`
- `docs/work-packages/20260309_ai_authority_doctrine/tracker.md`
