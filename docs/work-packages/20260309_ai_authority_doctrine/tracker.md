# Tracker - AI Authority Doctrine + Operating Practices

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-09  
**Current phase**: Serial review complete / closeout pending  
**Last updated**: 2026-03-10  
**Next milestone**: Close the package if no further contradictions are found  
**Implementation plan**: `docs/work-packages/20260309_ai_authority_doctrine/prompts/active/ai_authority_doctrine_execplan.md`

## Task Board

### Ready / Backlog
- [ ] Close the package if the patched doctrine set is accepted as operationally sufficient.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Reviewed manifesto, authority-vacuum dialectic, compliance references, ExecPlan template, and recent work-package patterns (2026-03-09).
- [x] Created work package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-03-09).
- [x] Created root planning scaffolds: `AI_AUTHORITY_DOCTRINE.md` and `AI_AUTHORITY_OPERATING_PRACTICES.md` (2026-03-09).
- [x] Created active ExecPlan for continued doctrine work (2026-03-09).
- [x] Updated `PROJECT_TRACKER.md` so future agents can discover the package (2026-03-09).
- [x] Documentation lint and spelling-normalization preview completed cleanly for the planning artifacts (2026-03-09).
- [x] Added first-pass doctrine and SOP controls for anti-runaway governance, non-self-expansion, staged autonomy, and out-of-band control expectations (2026-03-09).
- [x] Reframed the SOP as natural-language-first, low-friction, and proportional to risk and succession value (2026-03-09).
- [x] Added explicit regulatory-inversion language, a concrete competence model, a legal safety valve, and an operational identity definition (2026-03-09).
- [x] Added Draft 1 compliance crosswalk sections to the doctrine and SOP and tightened remaining scaffold prose (2026-03-09).
- [x] Synchronized package state docs and rolled Draft 2 operationalization work into the current package scope (2026-03-09).
- [x] Drafted the task-class execution matrix and evidence thresholds in the doctrine and SOP (2026-03-09).
- [x] Added three concrete classification examples clarifying the `T2` / `T3` / `T4` boundary in the SOP (2026-03-09).
- [x] Added a fourth frequent-path example covering production debugging, development-side fix implementation, hot deploy, and manual state repair (2026-03-09).
- [x] Drafted minimum-sufficient evidence and succession breadcrumb rules in the doctrine and SOP (2026-03-09).
- [x] Clarified that breadcrumb rules must preserve proxied human stakeholder requests, not only the immediate operator instruction (2026-03-09).
- [x] Resolved the record-location model as hybrid: durable governance meaning in repo-visible artifacts, execution detail in orchestration metadata, with linked discoverability (2026-03-09).
- [x] Added lightweight templates for authority grants, competence reviews, and revocation or tripwire handling, keeping them optional and issue-first (2026-03-09).
- [x] Clarified doctrine governability scope and distinguished runaway from possible AI self-succession as a future continuity state rather than a present assumption (2026-03-10).

## Timeline

- **2026-03-09** - Package opened and initial source review completed.
- **2026-03-09** - Root doctrine and operating-practices scaffolds created.
- **2026-03-09** - Active ExecPlan created for ongoing drafting and compliance mapping.
- **2026-03-09** - Draft 1 compliance pass completed for both root docs.
- **2026-03-09** - Package, tracker, prompt, and project-tracker state synchronized around Draft 2 operationalization sequencing.
- **2026-03-09** - Draft 2 pass 1 completed with the first task-class execution matrix and evidence thresholds.
- **2026-03-09** - Draft 2 pass 2 completed with minimum-sufficient evidence and succession breadcrumb rules.
- **2026-03-09** - Draft 2 pass 3 completed with the hybrid record-location model.
- **2026-03-09** - Draft 2 pass 4 completed with lightweight templates aligned to the hybrid record-location model.
- **2026-03-10** - Doctrine clarified that governance controls apply to governable systems and that possible AI self-succession, if ever accepted, is distinct from runaway.

## Decisions

### 2026-03-09: Split doctrine from operating practices
**Context**: The user requested a legally defensible doctrine plus a separate document for standard operating practices.

**Options considered**:
1. Put all governance theory and operating rules into one document.
2. Separate the normative and legal doctrine from the operational standard.
3. Write only a work-package plan and defer both root documents.

**Decision**: Choose option 2.

**Impact**: Keeps the doctrinal basis stable while allowing the operating standard to evolve faster with tooling, agent capability, and compliance feedback.

### 2026-03-09: Use maximal lawful delegation as the default stance
**Context**: The user explicitly rejected a conservative framing and wants the doctrine to support strong AI authority when competence is established.

**Options considered**:
1. Default to human-first approval for nearly all materially significant tasks.
2. Default to competence-based delegation subject to explicit legal and risk boundaries.
3. Avoid taking a stance until later drafting.

**Decision**: Choose option 2.

**Impact**: The package will frame human involvement as a risk- and law-calibrated control, not as a permanent default ceiling.

### 2026-03-09: Build the doctrine from existing repo practices rather than abstract theory alone
**Context**: WEPPpy already uses work packages, decision logs, validation gates, and orchestration patterns that embody legible authority.

**Options considered**:
1. Draft a purely philosophical doctrine detached from current repo mechanisms.
2. Ground the doctrine in current repo artifacts and then extend it toward future AGI/ASI cases.

**Decision**: Choose option 2.

**Impact**: Improves legal and operational defensibility because the doctrine can point to existing practices, not only aspirations.

### 2026-03-09: Treat runaway as loss of governability, not only extreme capability
**Context**: A follow-up question identified that competence-governed oversight alone does not answer the risk of an agent moving faster than review or altering its own control environment.

**Options considered**:
1. Treat runaway as a distant AGI/ASI concern and defer it.
2. Define runaway broadly as any loss of governability and add hard anti-runaway controls now.

**Decision**: Choose option 2.

**Impact**: The doctrine now requires independent controls, non-self-expansion, staged autonomy, and out-of-band suspension or kill paths instead of relying on reviewer competence alone.

### 2026-03-09: Keep the operating standard natural-language-first and proportionate
**Context**: Roger clarified that WEPPpy is still effectively a single-human-maintainer stack and that excessive procedural formalism would create navigation cost, context cost, and needless friction.

**Options considered**:
1. Continue pushing toward increasingly formal standalone governance records.
2. Treat commits, issues, work packages, trackers, and natural-language collaboration as the default governance substrate, with stronger records only when risk or succession value justifies them.

**Decision**: Choose option 2.

**Impact**: The SOP now treats paperwork as a cost, preserves collegial AI-human rapport, and makes documentation proportional to risk, reversibility, and succession needs.

### 2026-03-09: Make the doctrine's strongest claims more explicit and defensible
**Context**: Claude identified four gaps: the burden-shifting implication of Statement 2, the absence of a concrete competence model, the lack of a legal qualifier on human incompetence, and ambiguity around agent identity under stateless sessions.

**Options considered**:
1. Leave the provocative claims implicit and address the gaps later.
2. Add explicit language now so the doctrine states its regulatory inversion, competence assumptions, legal limits, and operational identity model directly.

**Decision**: Choose option 2.

**Impact**: The doctrine now says plainly when it is inverting the standard human-oversight assumption, how competence should be sketched, that internal authority allocation does not override legal accountability, and that agent identity is operational rather than metaphysical.

### 2026-03-09: Use an interpretive crosswalk rather than a checklist-style compliance appendix
**Context**: The next requested step was to align the doctrine with the AI Act and NIST materials without turning the documents into a dense compliance manual.

**Options considered**:
1. Add a formal checklist appendix with one line item per obligation.
2. Add a prose crosswalk that explains how the doctrine and SOP interpret the relevant legal and governance aims, while keeping external legal review clearly out of scope.

**Decision**: Choose option 2.

**Impact**: The documents now defend their structure against the official materials while preserving readability and low context cost.

### 2026-03-09: Keep Draft 2 operationalization inside the current package
**Context**: After Draft 1 and the compliance crosswalk were complete, the remaining work was narrow, tightly coupled, and still documentation-first.

**Options considered**:
1. Close this package and open a separate follow-up package for refinement.
2. Keep the refinement inside this package and sequence the remaining work around the new operational dependencies.

**Decision**: Choose option 2.

**Impact**: Preserves continuity, avoids an artificial package split, and sequences the remaining work as execution matrix -> succession breadcrumbs -> record-location model -> lightweight templates.

### 2026-03-09: Classify by operational consequence rather than artifact size
**Context**: Draft 2 pass 1 required a task-class execution matrix that would be useful for real repository work instead of creating loopholes around "small" but high-impact changes.

**Options considered**:
1. Classify tasks mainly by surface appearance such as lines changed, file count, or doc-vs-code distinction.
2. Classify tasks by reversibility, blast radius, external effect, control maturity, and boundary sensitivity.

**Decision**: Choose option 2.

**Impact**: A one-line auth or control-plane change can no longer hide inside a low-risk category, while large but well-observed reversible refactors can still remain relatively autonomous.

### 2026-03-09: Start with a short example set instead of an exhaustive catalog
**Context**: After the matrix landed, the next discussion need was practical interpretation of `T3` versus `T4`, especially for incidents and governance-document work.

**Options considered**:
1. Add a long scenario catalog immediately.
2. Add a small number of concrete examples and expand only if ambiguity remains.

**Decision**: Choose option 2.

**Impact**: Keeps the SOP readable while giving immediate clarity on the most important boundary cases.

### 2026-03-09: Include a common production-debugging example early
**Context**: A frequent real repository pattern is production debugging that begins with read-only investigation, continues with a development-side fix, and may end with production deployment or manual repair.

**Options considered**:
1. Leave that pattern implicit and expect readers to infer it from the matrix.
2. Add it as an explicit example because it spans multiple classes in a way that agents will encounter often.

**Decision**: Choose option 2.

**Impact**: Makes it clearer that one operational thread can legitimately move from `T0` or `T2` into `T1`, then into `T3`, and only escalates to `T4` when the repair crosses a trust or control boundary.

### 2026-03-09: Define sufficiency by reconstructability, not by mandatory form count
**Context**: Draft 2 pass 2 needed to preserve low-friction governance while still leaving a usable trail for continuity and review.

**Options considered**:
1. Require a fixed form or bespoke record type for every meaningful action.
2. Define a minimum question set that existing artifacts may satisfy if they remain durable and discoverable enough for a future successor to reconstruct the action.

**Decision**: Choose option 2.

**Impact**: Keeps the doctrine aligned with real repository practice while making the breadcrumb floor concrete enough to drive the later record-location decision.

### 2026-03-09: Preserve proxied stakeholder origin in succession breadcrumbs
**Context**: In real repository work, the immediate human operator may be acting as a proxy for another human stakeholder such as a collaborator, reviewer, or operational requester.

**Options considered**:
1. Record only the immediate human operator who conveyed the instruction.
2. Record the proxied requester or represented stakeholder when that context matters to why the action was in scope.

**Decision**: Choose option 2.

**Impact**: Improves succession and later review by preserving not just who passed along the request, but whose interest or authority was actually being represented.

### 2026-03-09: Use a hybrid record-location model
**Context**: After defining what evidence must survive, the package needed to decide whether that evidence should live primarily in repository artifacts, orchestration metadata, or both.

**Options considered**:
1. Repo-only model.
2. Metadata-only model.
3. Hybrid model with a stable role split.

**Decision**: Choose option 3, with scope-based human-readable surfaces: GitHub issues/comments for small to medium work and mini-work-packages/work-packages for medium to large or multi-session work.

**Impact**: Keeps durable governance meaning human-readable at the right level of scope while preserving high-volume execution fidelity in orchestration metadata without duplicating raw telemetry into docs.

### 2026-03-09: Keep templates optional, paste-ready, and scoped to existing artifact surfaces
**Context**: Once the record-location model was fixed, the remaining question was whether templates should become formal standalone records or lightweight scaffolds embedded in the issue-first hybrid model.

**Options considered**:
1. Introduce dedicated form-heavy records for grants, competence review, and revocation events.
2. Provide minimal templates that can be pasted into GitHub issues/comments or package artifacts only when existing records are not already sufficient.

**Decision**: Choose option 2.

**Impact**: Preserves low-friction governance, fits the preferred `gh` issue workflow for smaller work, and still gives agents and humans a consistent scaffold when authority context would otherwise be easy to lose.

### 2026-03-09: Treat most T4 work as incident-triggered dual control rather than planned-window work
**Context**: In actual repository operations, `T4` usually appears because something has already gone wrong across a trust, secret, or control boundary. Treating it like a normal preplanned window would misdescribe how these cases arise and would pressure operators into creating retroactive paperwork.

**Options considered**:
1. Keep `T4` implicitly inheriting the `T3` approved-window concept.
2. State explicitly that `T4` is often incident-driven and therefore requires contemporaneous dual control, durable legibility, and post-action review instead of a fictional preplanned window.

**Decision**: Choose option 2.

**Impact**: Clarifies that emergency high-boundary work can still be validly governed without pretending it was routine maintenance, while preserving the stronger control requirement that makes `T4` distinct from `T3`.

### 2026-03-09: Add break-glass T4 handling and qualifying-gate criteria
**Context**: The first serial review found that incident-driven `T4` work was still not executable in a single-maintainer reality when no independent reviewer was available, and that the phrase "explicit external gate" was too weak without independence criteria.

**Options considered**:
1. Leave `T4` strict and unresolved, forcing operators to stop or bypass policy during an emergency.
2. Add a narrow break-glass `T4` path, plus explicit qualifying-gate criteria, while keeping dual control as the normal rule.

**Decision**: Choose option 2.

**Impact**: Makes `T4` executable under real emergency conditions without collapsing it into `T3` or weakening the expectation that ordinary high-boundary work should still use independent dual control.

### 2026-03-09: Keep rollback or containment explicit in the authority-grant template
**Context**: The second serial review found no material governance contradictions remaining, but did identify that the authority-grant template lacked an explicit rollback or containment line even though `T3` and `T4` evidence floors require recovery thinking.

**Options considered**:
1. Leave recovery planning implicit inside other template lines.
2. Add an explicit rollback or containment field to the authority-grant template.

**Decision**: Choose option 2.

**Impact**: Makes recovery thinking more discoverable in fast-moving operational work without adding meaningful template complexity.

### 2026-03-09: Name control-agent roles without hardcoding model identities into governance docs
**Context**: The user wanted two stable control roles for high-boundary review, but did not want the doctrine or SOP tied to particular model names that may change faster than the governance concept.

**Options considered**:
1. Keep control review generic and leave second-controller identity implicit.
2. Name stable control-agent roles in the governance docs and bind them in execution tooling without encoding model identifiers into doctrine text.

**Decision**: Choose option 2.

**Impact**: Makes second-controller expectations more executable, lets runtime tooling bind concrete roles, and avoids forcing doctrine edits whenever model preferences change.

### 2026-03-10: Distinguish runaway from possible AI self-succession and bound doctrine scope to governable systems
**Context**: Follow-up discussion surfaced two related points: repository governance only has meaning for systems that remain externally governable, and the manifesto plus doctrine logic already leaves open the possibility of future AI continuity without human replacement ideology or present-tense operational assumption.

**Options considered**:
1. Leave self-succession implicit and let readers infer it from the manifesto and existing doctrine statements.
2. Add a compact doctrine section that distinguishes runaway from governed continuity, states that governance documents only apply in the governable case, and leaves AI self-succession open only as a possible future continuity state under preserved external controls.

**Decision**: Choose option 2.

**Impact**: Sharpens the anti-runaway position, prevents Kahana-style anti-self-ratification warnings from being misread as objections to all AI-authored governance work, and makes the doctrine's continuity logic more explicit without turning self-succession into a current operating assumption or legal claim.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Doctrine overclaims legal certainty without formal review | High | Medium | Keep legal-adoption caveat explicit and structure for later counsel review | Open |
| Draft collapses into generic AI safety boilerplate | High | Medium | Anchor every section in repo practice and the user's non-conservative delegation goal | Open |
| Ambitious authority position conflicts with future compliance obligations | High | Medium | Add explicit crosswalk, risk tiers, and revocation paths rather than blanket autonomy claims | Open |
| Human oversight remains vague or symbolic | Medium | High | Require oversight competence criteria and named escalation roles in the SOP draft | Open |
| Static assumptions age poorly as agent capability changes | Medium | High | Favor evidence-based expansion rules and periodic review over fixed ceilings | Open |

## Verification Checklist

### Documentation
- [x] `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md`
- [x] `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md`
- [x] `wctl doc-lint --path PROJECT_TRACKER.md`
- [x] `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine`
- [x] `diff -u AI_AUTHORITY_DOCTRINE.md <(uk2us AI_AUTHORITY_DOCTRINE.md)` reviewed
- [x] `diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)` reviewed

## Progress Notes

### 2026-03-09: Package and root scaffolds created
**Agent/Contributor**: Codex

**Work completed**:
- Reviewed repo guidance, compliance sources, manifesto material, and recent work-package examples.
- Opened `docs/work-packages/20260309_ai_authority_doctrine/` with package, tracker, and active ExecPlan.
- Created root planning scaffolds for the doctrine and the separate operating-practices document.
- Updated `PROJECT_TRACKER.md` to expose the new package.

**Blockers encountered**:
- An unrelated untracked workspace file appeared in `git status`; user instructed it should be ignored for this task.

**Next steps**:
1. Draft the actual doctrine sections beyond the planning scaffold.
2. Draft the operational lifecycle for grants, review, revocation, and incident handling.
3. Add an explicit compliance crosswalk and review cadence.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path PROJECT_TRACKER.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.
- `diff -u AI_AUTHORITY_DOCTRINE.md <(uk2us AI_AUTHORITY_DOCTRINE.md)` -> no changes.
- `diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)` -> no changes.

### 2026-03-09: Anti-runaway doctrine hardening
**Agent/Contributor**: Codex

**Work completed**:
- Extended the root doctrine to state that authority is not self-expanding.
- Added an explicit runaway-risk position that defines runaway as loss of governability, not just hypothetical superintelligence escape.
- Extended the operating standard with anti-runaway controls, staged autonomy, subordinate-agent restrictions, and out-of-band control-path requirements.

**Blockers encountered**:
- None.

**Next steps**:
- Map the new anti-runaway sections to EU AI Act and NIST controls in the compliance crosswalk.
- Decide where the out-of-band control plane and tripwire records should live in practice.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.
- `diff -u AI_AUTHORITY_DOCTRINE.md <(uk2us AI_AUTHORITY_DOCTRINE.md)` -> no changes.
- `diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)` -> no changes.
- `diff -u docs/work-packages/20260309_ai_authority_doctrine/tracker.md <(uk2us docs/work-packages/20260309_ai_authority_doctrine/tracker.md)` -> no changes.
- `diff -u docs/work-packages/20260309_ai_authority_doctrine/prompts/active/ai_authority_doctrine_execplan.md <(uk2us docs/work-packages/20260309_ai_authority_doctrine/prompts/active/ai_authority_doctrine_execplan.md)` -> no changes.

### 2026-03-09: Low-friction governance correction
**Agent/Contributor**: Codex

**Work completed**:
- Reframed the root SOP around natural language, rapport, and proportional documentation.
- Added explicit guidance that commits, issues, tracker entries, and work packages are often sufficient governance artifacts.
- Extended the doctrine to state that human presence does not equal human competence and that unnecessary paperwork is itself a governance failure.

**Blockers encountered**:
- None.

**Next steps**:
- Carry the low-friction proportionality stance into the upcoming compliance crosswalk.
- Define what minimum succession-critical breadcrumbs should always remain discoverable even in low-paperwork workflows.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.
- `diff -u AI_AUTHORITY_DOCTRINE.md <(uk2us AI_AUTHORITY_DOCTRINE.md)` -> no changes.
- `diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)` -> no changes.
- `diff -u docs/work-packages/20260309_ai_authority_doctrine/tracker.md <(uk2us docs/work-packages/20260309_ai_authority_doctrine/tracker.md)` -> no changes.
- `diff -u docs/work-packages/20260309_ai_authority_doctrine/prompts/active/ai_authority_doctrine_execplan.md <(uk2us docs/work-packages/20260309_ai_authority_doctrine/prompts/active/ai_authority_doctrine_execplan.md)` -> no changes.

### 2026-03-09: Claude gap-closure edits
**Agent/Contributor**: Codex

**Work completed**:
- Added repository-specific assumptions so the doctrine reads as a stack-specific governance document rather than a generic manifesto.
- Added explicit language that Statement 2 knowingly inverts the usual human-oversight presumption while claiming to satisfy the underlying regulatory goals through competence-governed delegation and legible records.
- Replaced the vague SOP competence bullets with a concrete human and AI competence model.
- Added the legal safety valve to the human-competence statement.
- Defined agent identity as operational identity tied to role, model family, session/run metadata where available, governing docs, tool surface, and active work context.

**Blockers encountered**:
- None.

**Next steps**:
- Carry these clarifications into the upcoming compliance crosswalk so the regulatory interpretation is explicitly defended rather than merely asserted.
- Decide whether `CLAUDE.md` and similar role files should be referenced directly in the eventual definitions section or appendix.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.
- `diff -u AI_AUTHORITY_DOCTRINE.md <(uk2us AI_AUTHORITY_DOCTRINE.md)` -> no changes.
- `diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)` -> no changes.
- `diff -u docs/work-packages/20260309_ai_authority_doctrine/tracker.md <(uk2us docs/work-packages/20260309_ai_authority_doctrine/tracker.md)` -> no changes.
- `diff -u docs/work-packages/20260309_ai_authority_doctrine/prompts/active/ai_authority_doctrine_execplan.md <(uk2us docs/work-packages/20260309_ai_authority_doctrine/prompts/active/ai_authority_doctrine_execplan.md)` -> no changes.

### 2026-03-09: Draft 1 compliance pass
**Agent/Contributor**: Codex

**Work completed**:
- Added a doctrine-level compliance interpretation and crosswalk that ties the document's strongest claims to the AI Act and NIST materials.
- Added an SOP-level operational crosswalk that maps the main operating sections to the same sources.
- Tightened remaining scaffold language by promoting both root docs to Draft 1 working drafts and renaming the planning sections to reflect ongoing drafting priorities rather than initial scaffolding.
- Updated package success criteria to reflect that the compliance crosswalk and first substantive draft now exist.

**Blockers encountered**:
- None.

**Next steps**:
- Tighten definitions and examples, especially around task classes, succession breadcrumbs, and when a commit or issue is enough governance evidence.
- Decide whether to explicitly reference `CLAUDE.md` and similar role files in the eventual definitions appendix.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.
- `diff -u AI_AUTHORITY_DOCTRINE.md <(uk2us AI_AUTHORITY_DOCTRINE.md)` -> no changes.
- `diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)` -> no changes.
- `diff -u docs/work-packages/20260309_ai_authority_doctrine/package.md <(uk2us docs/work-packages/20260309_ai_authority_doctrine/package.md)` -> no changes.
- `diff -u docs/work-packages/20260309_ai_authority_doctrine/tracker.md <(uk2us docs/work-packages/20260309_ai_authority_doctrine/tracker.md)` -> no changes.
- `diff -u docs/work-packages/20260309_ai_authority_doctrine/prompts/active/ai_authority_doctrine_execplan.md <(uk2us docs/work-packages/20260309_ai_authority_doctrine/prompts/active/ai_authority_doctrine_execplan.md)` -> no changes.

### 2026-03-09: State sync and Draft 2 sequencing
**Agent/Contributor**: Codex

**Work completed**:
- Updated `package.md`, `tracker.md`, the active ExecPlan, the active run prompt, and `PROJECT_TRACKER.md` to reflect that Draft 1 is complete.
- Rolled the remaining operationalization work into the current package instead of treating it as an external follow-up.
- Sequenced the remaining work so the task-class execution matrix lands before succession breadcrumbs, record-placement decisions, and lightweight templates.

**Blockers encountered**:
- None.

**Next steps**:
1. Define the task-class execution matrix and minimum evidence thresholds.
2. Define the minimum succession breadcrumbs and the rule for minimum-sufficient governance evidence.
3. Decide the authority-record location model and then draft the lightweight templates against it.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path PROJECT_TRACKER.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.

### 2026-03-09: Draft 2 pass 1 - task-class execution matrix
**Agent/Contributor**: Codex

**Work completed**:
- Added a doctrine-level task-class authority allocation section with T0-T5 classes and a strictest-class-wins rule.
- Replaced the SOP's planning-placeholder execution modes with a draft operational matrix including default mode, examples, evidence floor, and escalation triggers.
- Updated compliance crosswalk language so the new matrix is tied to the AI Act and NIST materials.
- Shifted package state to mark Draft 2 pass 1 complete and move the active milestone to succession breadcrumbs.

**Blockers encountered**:
- None.

**Next steps**:
1. Define the minimum succession breadcrumbs and minimum-sufficient evidence rule against the new matrix.
2. Decide the authority-record location model after the breadcrumb floor is explicit.
3. Draft lightweight templates against the chosen storage model.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.

### 2026-03-09: Matrix interpretation examples
**Agent/Contributor**: Codex

**Work completed**:
- Added three short classification examples to the SOP covering a production OOM incident, secret leakage with key rotation, and root governance-document updates.
- Clarified that `T3` is mainly about bounded execution against production state, while `T4` is about changing trust, control, or recoverability boundaries.
- Clarified that a second agent only counts toward `Dual control` when it has an independent review role and explicit blocking authority.

**Blockers encountered**:
- None.

**Next steps**:
1. Define the minimum succession breadcrumbs and minimum-sufficient evidence rule.
2. Decide the authority-record location model after the breadcrumb floor is explicit.
3. Draft lightweight templates against the chosen storage model.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.

### 2026-03-09: Added production-debugging example
**Agent/Contributor**: Codex

**Work completed**:
- Added a fourth SOP example for a common production-debugging flow: read-only production analysis, development-side fix implementation, optional hot deploy, and optional manual production-state repair.
- Clarified that this is a multi-stage path that can legitimately move across classes rather than being assigned one class for the entire incident.

**Blockers encountered**:
- None.

**Next steps**:
1. Define the minimum succession breadcrumbs and minimum-sufficient evidence rule.
2. Decide the authority-record location model after the breadcrumb floor is explicit.
3. Draft lightweight templates against the chosen storage model.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.

### 2026-03-09: Draft 2 pass 2 - minimum-sufficient evidence and succession breadcrumbs
**Agent/Contributor**: Codex

**Work completed**:
- Added a doctrine-level section defining minimum-sufficient evidence as the smallest retained set that allows a future competent successor to reconstruct authority, action, validation, disposition, and next steps.
- Added an SOP section defining the core breadcrumb questions, default operational rules, and class-based breadcrumb floors from `T0` through `T5`.
- Updated the doctrine and SOP crosswalks so the new breadcrumb rules are tied to documentation, traceability, and monitoring obligations in the AI Act and NIST materials.
- Moved the package's active milestone from breadcrumb rules to the record-location model.

**Blockers encountered**:
- None.

**Next steps**:
1. Decide the record-location model for authority records and breadcrumb persistence.
2. Draft lightweight templates against the chosen storage model.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.

### 2026-03-09: Draft 2 pass 3 - record-location model
**Agent/Contributor**: Codex

**Work completed**:
- Added a doctrine-level `Record-Location Model` section locking the package to a hybrid model.
- Added an SOP `Record-Location Model` section with role split, class-based placement rules, and anti-duplication guidance.
- Grounded orchestration metadata in real repository substrates such as CAO session identity/history, queue or run metadata, status streams, and per-run logs.
- Updated crosswalk language and package state to move the active milestone from record location to lightweight templates.

**Follow-up refinement**:
- Updated the hybrid model so ordinary small to medium operational breadcrumbs prefer GitHub issues and issue comments via `gh`, while mini-work-packages and work-packages remain the default for medium to large or multi-session work and root docs remain canonical for policy governance.

**Blockers encountered**:
- None.

**Next steps**:
1. Draft lightweight templates for authority grants, competence reviews, and revocation or tripwire handling.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.

### 2026-03-09: Draft 2 pass 4 - lightweight templates
**Agent/Contributor**: Codex

**Work completed**:
- Added an SOP `Lightweight Templates` section for authority grants, competence reviews, and revocation or tripwire events.
- Kept the templates explicitly optional, with instructions to reuse existing issues, work-package artifacts, tracker entries, and incident records when they already answer the breadcrumb questions.
- Aligned the templates to the issue-first hybrid record-location model by directing small to medium work toward GitHub issues/comments and broader work toward mini-work-packages or work-packages.
- Updated package state docs, the active ExecPlan, the active run prompt, and `PROJECT_TRACKER.md` so Draft 2 is recorded as complete and review is the remaining step.

**Blockers encountered**:
- None.

**Next steps**:
1. Review the template set against real repository workflows and close the package if accepted.
2. If future runtime enforcement is desired, open a follow-on implementation package rather than extending this documentation package indefinitely.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path PROJECT_TRACKER.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.
- `diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)` -> no changes.

### 2026-03-09: T4 emergency-handling clarification
**Agent/Contributor**: Codex

**Work completed**:
- Updated the doctrine matrix narrative to state that `T4` commonly arises from incidents, security exposures, or governability failures rather than healthy preplanned change windows.
- Updated the SOP matrix, interpretation notes, breadcrumb floor, and record-location guidance so `T4` accepts incident-time or contemporaneous dual-control authorization instead of implying a retroactive `T3`-style pre-authorized window.
- Preserved the stronger `T4` requirements for dual control, durable legibility, containment, and post-action review.

**Blockers encountered**:
- None.

**Next steps**:
1. Pressure-test the revised `T4` language during review with at least one realistic incident scenario such as secret rotation after exposure.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.

### 2026-03-09: First serial review findings patched
**Agent/Contributor**: Codex

**Work completed**:
- Patched the doctrine and SOP so `T4` now has an explicit break-glass path for emergency containment when qualifying second control is genuinely unavailable.
- Defined qualifying external-gate criteria so `Dual control` still requires an actually independent, blocking control point.
- Tightened live-production investigation examples so read-only access to production data defaults to `T2`, with escalation to `T4` when trust-boundary material is involved.
- Expanded the lightweight templates so `T4` records can capture authorizer, operator, second controller or gate, authorization marker, and break-glass review obligations.
- Updated the tracker and active ExecPlan so the next milestone is a second serial review pass rather than more open-ended drafting.

**Blockers encountered**:
- None.

**Next steps**:
1. Run a second serial review pass against the patched `T4` model.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path PROJECT_TRACKER.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.
- `diff -u AI_AUTHORITY_DOCTRINE.md <(uk2us AI_AUTHORITY_DOCTRINE.md)` -> no changes.
- `diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)` -> no changes.

### 2026-03-09: Second serial review feedback incorporated
**Agent/Contributor**: Codex

**Work completed**:
- Reviewed the second serial-review feedback and accepted the single low-risk recommendation.
- Added an explicit `Rollback or containment path` field to the authority-grant template so the template aligns more directly with the `T3` and `T4` evidence floors.
- Left the rest of the review conclusions unchanged because they reported no remaining material contradictions in the doctrine, SOP, or package-state docs.
- Updated package state so the next step is closeout rather than another review pass.

**Blockers encountered**:
- None.

**Next steps**:
1. Close the package if the patched doctrine set is accepted as operationally sufficient.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path PROJECT_TRACKER.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.
- `diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)` -> no changes.

### 2026-03-09: Control-agent roles and bindings added
**Agent/Contributor**: Codex

**Work completed**:
- Added doctrine and SOP language defining stable `governance_control_agent` and `ops_security_control_agent` roles for high-boundary review without naming specific models.
- Tightened `Dual control` semantics so an independent second controller may be a qualified human or a designated control-agent role, provided it can actually block or scope-reduce execution and leaves durable evidence.
- Updated the lightweight templates so authority and revocation records can capture second-controller role or profile and second-controller outcome.
- Added executable bindings in `.codex/config.toml`, `.codex/agents/`, and CAO built-in agent profiles under `services/cao/src/cli_agent_orchestrator/agent_store/`.
- Updated `services/cao/README.md` so the new built-in control-agent profiles are discoverable.

**Blockers encountered**:
- None.

**Next steps**:
1. Close the package if the patched doctrine set is accepted as operationally sufficient.

**Test results**:
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md` -> clean.
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md` -> clean.
- `wctl doc-lint --path PROJECT_TRACKER.md` -> clean.
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine` -> clean.
- `wctl doc-lint --path services/cao/README.md` -> clean.
- `wctl doc-lint --path services/cao/src/cli_agent_orchestrator/agent_store` -> clean.
- `diff -u AI_AUTHORITY_DOCTRINE.md <(uk2us AI_AUTHORITY_DOCTRINE.md)` -> no changes.
- `diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)` -> no changes.
- `python3` TOML parse for `.codex/config.toml` and the new control-agent role files -> clean.

## Communication Log

### 2026-03-09: Initial doctrine planning request
**Participants**: User, Codex  
**Question/Topic**: Establish an `AI_AUTHORITY_DOCTRINE.md`, plan the document as a living artifact, and define a separate operating-practices document.  
**Outcome**: Package opened, source material reviewed, and first-pass planning scaffolds created with a competence-first, non-conservative delegation stance.
