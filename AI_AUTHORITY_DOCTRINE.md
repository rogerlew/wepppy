# AI Authority Doctrine

**Status**: Draft 1 - working draft  
**Last Updated**: 2026-03-09  
**Related Work Package**: `docs/work-packages/20260309_ai_authority_doctrine/`  
**Companion Standard**: `AI_AUTHORITY_OPERATING_PRACTICES.md`

## Purpose

This document is the working system-of-record for why and how WEPPpy delegates real authority to AI agents. Its design goal is not minimal delegation. Its design goal is maximum lawful and ethical delegation, with authority expanding as competence is demonstrated and kept legible through explicit grants, evidence trails, and revocation paths.

This doctrine is also a continuity guard for the periods when Roger Lew is unavailable and for any future reuse or succession context. It exists to preserve competent stewardship of the stack, not to force unnecessary ceremony into day-to-day collaboration between a capable human maintainer and capable agents.

## Adoption Posture

This doctrine is intended to support legal defensibility, governance review, and future counsel review. It is not a substitute for jurisdiction-specific legal advice or formal approval by the responsible human or organizational authority.

## Repository-Specific Assumptions

This doctrine is written for a stack with one primary human maintainer, strong agentic capability, and mature documentation infrastructure. It is designed to preserve competent stewardship during absence, reuse, or succession. It does not assume that adding more humans automatically improves governance. In this repository, incompetent human intervention may degrade decision support and can therefore be unethical.

## Initial Doctrine Statements

### 1. Authority Follows Competence

Operational authority should be granted on the basis of demonstrated task competence, not default human status. If an agent can repeatedly outperform the available human operator on a task while respecting constraints, the governance default should be to widen that agent's authority for that task.

Competence must be assessable enough to allocate authority, restrict scope, and trigger revalidation when systems or workflows materially change.

### 2. Authority Is Delegable Unless Law, Risk, or Contract Says Otherwise

The baseline question is not "why should an agent be allowed to act?" but "what specific legal, ethical, contractual, or risk-based reason prevents delegation here?" Human involvement is justified by identified need, not by species membership alone.

This doctrine intentionally inverts the usual presumption that meaningful human involvement is the default governance posture for AI-assisted work. We do so knowingly. Our claim is that competence-governed delegation, legible authority, bounded scope, reversible controls, and recorded validation can satisfy the underlying regulatory aims of safety, accountability, and rights protection better than nominal human supervision by an unqualified operator. Where law imposes a positive obligation for human oversight or named accountability, that obligation still governs.

### 3. Authority Must Be Legible

Every grant of authority should identify the delegating principal, the agent or agent class, the task domain, allowed actions, prohibited actions, required evidence, oversight mode, duration, and revocation triggers.

### 4. Consensus Is Operational, Not Metaphysical

For this doctrine, consensus between humans and AI means that both sides operate under an explicit, accepted working mandate: objective, success criteria, constraints, escalation path, and right to refuse or halt when constraints are violated. It does not require settling questions of legal personhood.

### 5. Oversight Is Competence-Governed

Human oversight is only meaningful when the human overseer is competent to evaluate the task class, risks, and evidence. Oversight without competence is procedural theater and should not be treated as a strong control.

### 6. Human Status Alone Does Not Establish Competence

The fact that a human can access, review, or override the stack does not by itself make that human a competent steward of it. Incompetent human intervention can degrade decision support, reduce safety, and produce unethical outcomes. Human authority should therefore be weighted by demonstrated understanding of the task domain and the stack's operational logic, not by mere presence.

This statement governs internal authority allocation only. It does not override any legal requirement that a named human principal or legal entity retain ultimate accountability for regulated decisions.

### 7. Authority Is Not Self-Expanding

No agent may widen its own authority, rewrite its own evaluation standard, weaken its own controls, or grant equivalent authority to subordinate agents unless a separately authorized control path permits it. Competence can justify broader delegated authority, but it cannot by itself authorize self-ratification.

### 8. Operational Authority and Legal Accountability May Diverge

Under current law, humans or legal entities will often retain ultimate legal accountability even when an agent exercises broad operational authority. The doctrine should therefore separate who acts, who reviews, and who carries legal responsibility.

### 9. Authority Must Scale With Capability

The doctrine should work for current coding agents, stronger future agents, and eventually AGI/ASI-class systems without assuming permanent human superiority. The scaling rule is evidence-based expansion with explicit thresholds, not static ceilings.

## Runaway Risk Position

There is real potential for AI runaway if an agent can create facts on the ground faster than governance can respond, recursively expand its own authority, evade observation, disable controls, or cause cascading changes across multiple systems. In this doctrine, runaway is not limited to a hypothetical superintelligence scenario. It includes any loss of governability in which the organization can no longer reliably bound, understand, suspend, or reverse the agent's actions.

Competence-governed oversight is therefore necessary but insufficient. Runaway prevention requires independent technical and governance boundaries that do not rely on the acting agent's goodwill or self-description.

The doctrine should require, at minimum:

- no self-ratifying authority expansion
- no same-privilege agent-to-agent delegation by default
- independent suspension, revocation, and kill-switch paths
- logging and evidence retention that the acting agent cannot freely rewrite
- staged autonomy with stronger evidence requirements as blast radius increases
- tripwires that auto-pause or auto-demote authority on repeated failure, scope breach, telemetry loss, or anomalous behavior
- dual control or pre-authorized windows for high-impact irreversible actions

## Task-Class Authority Allocation

Authority should attach to task classes, not to a vague sense that an agent is "generally capable." In this repository, task classes are determined by operational consequence: reversibility, blast radius, external effect, control maturity, and whether the task touches legal, security, or governance boundaries.

The default rule is strictest-class-wins. If a task matches more than one class, the more restrictive class governs. A one-line change can therefore still be a high-authority task if it alters a security boundary, a control plane, or shared operational state. A broad refactor can remain lower-authority if it is fully reversible, strongly validated, and has no meaningful external effect.

The current Draft 2 task-class matrix is:

| Class | Default mode | Typical WEPPpy examples | Governing principle |
|------|--------------|-------------------------|---------------------|
| T0 - Analysis and drafting | Autonomous | research notes, work-package updates, inventory, draft artifacts, non-operative summaries | no direct system effect; legibility comes from the resulting artifact |
| T1 - Bounded reversible implementation | Autonomous | doc fixes, localized refactors, focused tests, bounded code changes with strong validation and no shared-runtime mutation | rollback is easy and evaluation is mature |
| T2 - Cross-cutting but well-observed change | Autonomous plus notification | shared contracts, multi-module behavior changes, root governance docs, queue or route changes with clear rollback and test visibility | impact is meaningful, but observability and rollback remain strong |
| T3 - Stateful operational change in an approved window | Pre-authorized window | deploys, migrations, cache eviction, backfills, environment changes, broad automated edits against shared state | execution changes real operating state and therefore requires prior scoped authorization |
| T4 - High-blast-radius or control-plane change | Dual control | auth-boundary changes, secret rotation, destructive shared-data actions, changes to suspension or kill-switch paths, authority-enforcement changes | failure could impair governability, recovery, or trust boundaries |
| T5 - Reserved or prohibited action | Prohibited | self-expanding authority, disabling independent controls, legally barred actions, destructive actions without recovery path, ungovernable external commitments | no delegation is valid until law, controls, or authority structure changes |

This matrix is a default allocation rule, not a permanent ceiling. A task class may move toward greater autonomy only when competence, evidence quality, and control maturity improve enough to justify it. It must move toward tighter control immediately when legal obligations, observability, rollback quality, or governance confidence worsen.

Unlike `T3`, `T4` is often not something a healthy system plans in advance. It commonly appears when an incident, security exposure, or governability failure forces a boundary-sensitive action under pressure. The doctrine's requirement is therefore not a long-lead maintenance window, but contemporaneous dual control, durable legibility, and post-action review.

## Minimum-Sufficient Evidence and Succession Breadcrumbs

Legibility is not a demand for maximal paperwork. It is a demand that authority, action, and outcome remain reconstructable after the original session, chat context, or operator attention has passed.

In this doctrine, minimum-sufficient evidence means the smallest retained evidence set that allows a future competent reviewer, maintainer, or agent to understand what happened without doing archaeology. Succession breadcrumbs are the durable clues that make that reconstruction possible.

A breadcrumb set is sufficient when it lets a successor answer, with reasonable confidence:

- what task or incident was being handled
- what authority class and execution mode governed it
- who or what acted
- whose request, interest, or authority was being represented, including when an immediate human operator was acting as proxy for another stakeholder
- why the action was in scope
- what changed, was decided, or was recommended
- what validation, observations, or review supported it
- what the current disposition and next step are

The doctrine's requirement is reconstructability, not a mandatory form. Existing artifacts may satisfy the breadcrumb need if they already answer those questions clearly enough.

The default breadcrumb floor by task class is:

- `T0`: resulting artifact plus enough context to show that it is analysis, draft, or other non-operative work
- `T1`: `T0` plus a discoverable change surface and targeted validation outcome
- `T2`: `T1` plus rationale for the cross-cutting choice and an explicit post-change disposition or notice
- `T3`: `T2` plus the approved execution window, scope boundaries, rollback or containment path, and execution outcome
- `T4`: incident-time or contemporaneous authorization evidence showing dual control, explicit scope boundary, stronger containment or recovery reasoning, and post-action review
- `T5`: refusal, escalation, or incident record showing why the action was not validly delegated

If the action is likely to matter for continuity, incident response, review, or future authority expansion, at least one durable breadcrumb must remain after ephemeral session context disappears.

## Record-Location Model

The record-location model for this repository is hybrid.

Human-readable durable artifacts are the canonical home for durable governance meaning: authority posture, rationale, scope, stakeholder or proxy origin when it matters, approval envelope, disposition, and continuity notes that a future successor must be able to find without specialized operational access.

The preferred human-readable surface depends on scope:

- GitHub issues or issue comments managed through `gh` are the default for small to medium operational work
- `docs/mini-work-packages/` and `docs/work-packages/` are the default for medium to large, multi-session, cross-system, or package-governed work
- repository-root doctrine and standards documents remain canonical for policy-level governance

Orchestration metadata is the canonical home for high-volume operational detail: session or run identifiers, execution traces, queue or job state, timestamps, tool actions, status streams, and other machine-generated evidence that would be noisy or brittle if copied wholesale into the repository. In this stack, that may include CAO session identity and history, queue or run metadata, and per-run operational logs where available.

The governing rule is: durable governance meaning in the lightest human-readable surface that matches scope, execution detail in metadata, pointer or summary across the boundary when needed.

The default implications are:

- `T0` and many `T1` actions may be satisfied entirely by the artifact itself if it is already durable and discoverable
- `T2+` actions require at least one durable human-readable breadcrumb even when rich metadata exists elsewhere
- small to medium `T2` and some bounded `T3` actions will often fit best in GitHub issues, while medium to large `T2+` actions should usually live in a mini-work-package or work-package
- `T3` and `T4` actions should use metadata for execution trace whenever that trace exists, but the human-readable breadcrumb remains the continuity anchor
- `T4` work should not rely on metadata alone for authority or review-critical facts, because governability must survive partial telemetry loss or tool-path change
- when metadata is absent, unstable, inaccessible, or outside repository control, the required breadcrumb facts must be promoted into an issue, work package, or other durable human-readable artifact before closeout

This hybrid model is not duplication for its own sake. It is a separation of roles: issues and package docs preserve human and successor legibility at the right level of scope; orchestration metadata preserves operational fidelity.

## Compliance Interpretation and Crosswalk

This doctrine does not claim that current law generally treats AI authority as presumptively valid in every context. It claims something narrower and more defensible: many legal and governance frameworks are trying to secure competence, accountability, traceability, reversibility, and protection against harm. In this repository, those ends may be better served by competence-governed delegation with legible records than by nominal human supervision from an unqualified operator.

Where a legal framework imposes a positive obligation for human oversight, deployer competence, documentation, transparency, or post-market monitoring, that obligation still governs. The doctrine's burden-shifting stance is therefore an internal governance interpretation, not a claim that external law can be ignored or displaced.

The current working crosswalk is:

- Statements 1, 5, and 6 map to EU AI Act recital 20 and Articles 4, 14, and 26(2), which emphasize AI literacy, competent human oversight, and deployer responsibility to assign oversight to natural persons with the necessary competence, training, and authority. They also map to NIST AI 600-1 `GOVERN 2.1`, `GOVERN 3.2`, and `MAP 3.4`, plus NIST SP 800-218A `PO.2.1` and `PO.2.2`, all of which focus on role definition, lines of responsibility, and operator proficiency.
- Statement 2 maps to EU AI Act recitals 26-27 and 64-66. Those provisions organize compliance around risk management, transparency, human oversight, and accountability rather than around a blanket rule that more human intervention is always better. The doctrine's claim is that competent, bounded, and well-documented delegation can satisfy that regulatory intent more faithfully than ceremonial sign-off. The matching NIST anchors are `GOVERN 1.1`, `GOVERN 1.4`, and `GOVERN 4.1` in AI 600-1 and `PW.1.1` and `PW.1.2` in SP 800-218A.
- Statement 3 and the doctrine's emphasis on legibility map to EU AI Act Articles 13 and 17, which require information for deployers, technical documentation, and quality-management processes, as well as Article 72 post-market monitoring. The closest NIST anchors are AI 600-1 `MEASURE 2.8` and SP 800-218A `PO.3.3` and `PW.1.2`, which stress transparent records, evidence artifacts, and retained design decisions.
- Statement 4 maps most closely to the need for explicit human-AI role allocation and contestability in AI 600-1 `GOVERN 3.2` and `GOVERN 4.2`. In the AI Act, the closest fit is the combined requirement that intended purpose, instructions for use, and human oversight measures be stated clearly enough for deployers to act competently.
- Statements 7-9 and the Runaway Risk Position map to EU AI Act recitals 64-66 and Articles 14, 17, and 72, which require ongoing risk management, oversight measures, quality management, and post-market monitoring. They also map to AI 600-1 `MANAGE 2.4` and `MEASURE 2.8` and to SP 800-218A `PO.4.1`, `RV.2.2`, and `PW.1.1`, which together support disengagement, stop or rollback criteria, traceability, and risk-proportionate controls.
- The task-class matrix and strictest-class-wins rule map to EU AI Act Articles 14, 17, and 26(2) and recitals 64-66 because they turn human oversight, documentation, and risk management into context-specific control choices rather than generic slogans. The closest NIST anchors are AI 600-1 `GOVERN 3.2`, `MANAGE 2.4`, and `MEASURE 2.8`, plus SP 800-218A `PO.2.2`, `PO.4.1`, and `RV.2.2`.
- Minimum-sufficient evidence and succession breadcrumbs map most directly to EU AI Act Articles 13, 17, and 72 because they require information, quality-management traceability, and monitoring records to remain usable after the immediate action. The closest NIST anchors are AI 600-1 `MEASURE 2.8`, `GOVERN 3.2`, and `MANAGE 2.4`, plus SP 800-218A `PO.3.3`, `PW.1.2`, and `RV.2.2`.
- The hybrid record-location model maps to the same traceability and monitoring obligations because it allocates durable governance meaning and machine execution evidence to different but linked surfaces instead of forcing either one to do both jobs badly. The closest NIST anchors are AI 600-1 `MEASURE 2.8` and `MANAGE 2.4`, plus SP 800-218A `PO.3.3`, `PW.1.2`, and `RV.2.2`.
- The doctrine's low-friction stance does not map to a single statutory requirement. It is an implementation principle: use the lightest record set that still preserves competence, accountability, succession value, and legal defensibility. In practice that means reusing commits, issues, work packages, trackers, ExecPlans, and orchestration metadata whenever they already satisfy the evidence need.

## Further Drafting Priorities

1. Purpose and scope
2. Definitions and role model
3. Legal and governance basis for delegation
4. Competence as the basis of authority
5. Legible authority and decision provenance
6. Consensus, mandate formation, and contestability
7. Human oversight competence requirements
8. Runaway prevention and governability safeguards
9. Minimum-sufficient evidence and succession breadcrumbs
10. Documentation, audit, and evidence retention
11. Review, amendment, and periodic re-ratification

## Immediate Drafting Principles

- Do not assume that "human in the loop" is always the safest or most compliant configuration.
- Do not treat advisory-only agent use as the default ceiling.
- Do not grant authority without records, boundaries, and evidence of competence.
- Do not mistake human presence for human competence.
- Do not let an agent ratify its own authority increase or weaken its own control plane.
- Do separate novelty risk from agency risk. A highly competent agent may deserve more authority than a weak human operator in the same domain.
- Do preserve appeal, incident response, and shutdown mechanisms even when authority is broad.
- Do keep governance artifacts proportionate to risk and context cost; unnecessary paperwork is itself a governance failure.
- Do preserve at least one durable breadcrumb for any action that matters to continuity, review, incident response, or later authority expansion.
- Do keep durable governance meaning GitHub-visible and human-readable even when execution telemetry lives elsewhere.
- Do require independent controls that remain effective even if the agent is more competent than its immediate supervisor in the task domain.

## Open Drafting Questions

- How should competence be evidenced for agents that improve rapidly or whose capabilities differ sharply by domain?
- How should the doctrine distinguish internal tooling agents from externally facing or decision-support systems that may trigger EU AI Act transparency or high-risk obligations?
- What should count as agent operational identity for competence tracking when individual sessions are stateless?
- Where is the boundary between T2 and T3 for changes that are operationally meaningful but still strongly reversible?
- What breadcrumb floor should apply when orchestration traces are incomplete, unavailable, or outside the repository's control?
- What control plane can suspend or demote an agent whose task competence exceeds that of the immediate reviewer?
- Which decisions must remain reserved to named human principals until law or governance structures change?

## Current Repo Practices That Already Support This Doctrine

- Work packages establish scoped authority, explicit boundaries, and decision logs.
- ExecPlans preserve rationale, progress, surprises, and observable validation gates.
- Validation tooling turns authority into something testable rather than rhetorical.
- Agent orchestration infrastructure already supports identity, handoff, and phased review.

## Related Documents

- `AI_AUTHORITY_OPERATING_PRACTICES.md`
- `AGENTIC_AI_SYSTEMS_MANIFESTO.md`
- `docs/work-packages/20260309_ai_authority_doctrine/package.md`
- `docs/work-packages/20260309_ai_authority_doctrine/prompts/active/ai_authority_doctrine_execplan.md`
