# AI Authority Doctrine and Operating Practices

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, WEPPpy will have a living doctrine that explains why operational authority may be delegated to AI agents and a separate operating standard that explains how that authority is granted, evidenced, reviewed, expanded, and revoked. The goal is not to preserve human control for its own sake. The goal is to maximize lawful and ethical delegation while keeping authority legible, risk-calibrated, and adaptable to stronger future agents.

Draft 1 is already complete. Draft 2 operationalization is now complete as well. The remaining work is human review and closeout so the current working drafts can be treated as usable governance references rather than open-ended drafting targets.

## Progress

- [x] (2026-03-09 18:15Z) Reviewed root guidance, manifesto material, authority-vacuum dialectic, compliance references, ExecPlan template, and recent work-package patterns.
- [x] (2026-03-09 18:15Z) Opened work package `docs/work-packages/20260309_ai_authority_doctrine/` with `package.md` and `tracker.md`.
- [x] (2026-03-09 18:15Z) Created root planning scaffolds `AI_AUTHORITY_DOCTRINE.md` and `AI_AUTHORITY_OPERATING_PRACTICES.md`.
- [x] (2026-03-09 18:15Z) Validated the planning artifacts with `wctl doc-lint` and reviewed `uk2us` preview diffs with no changes needed.
- [x] (2026-03-09 18:15Z) Added first-pass anti-runaway doctrine and SOP controls covering non-self-expansion, staged autonomy, out-of-band suspension, and tripwire expectations.
- [x] (2026-03-09 18:15Z) Reframed the operating standard to keep natural-language rapport and low-friction proportional documentation as the default.
- [x] (2026-03-09 18:15Z) Added explicit burden-shift language, a concrete competence model, a legal accountability qualifier, and an operational identity definition.
- [x] (2026-03-09 18:15Z) Added Draft 1 compliance crosswalk sections to the doctrine and SOP and tightened the remaining scaffold tone.
- [x] Draft the doctrine sections for legal posture, competence, legible authority, consensus, oversight competence, and scaling rules.
- [x] Draft the operating-practices sections for grant lifecycle, evidence, execution modes, incident handling, revocation, and review cadence.
- [x] Add a section-by-section crosswalk from doctrine and SOP claims to EU AI Act and NIST controls.
- [x] (2026-03-09 23:11Z) Update the package state so `package.md`, `tracker.md`, prompts, and `PROJECT_TRACKER.md` reflect Draft 1 completion and the new Draft 2 sequence.
- [x] (2026-03-09 23:11Z) Define the task-class execution matrix and minimum evidence thresholds.
- [x] (2026-03-09 23:45Z) Define the minimum succession breadcrumbs and minimum-sufficient evidence rules for low-friction governance.
- [x] (2026-03-09 23:45Z) Decide whether authority records should live in repo docs, orchestration metadata, or a hybrid model.
- [x] (2026-03-09 23:59Z) Draft lightweight templates for authority grants, competence reviews, and revocation or tripwire handling.

## Surprises & Discoveries

- Observation: The user explicitly rejected a conservative framing and wants the doctrine optimized for maximum lawful delegation rather than human-first default approvals.
  Evidence: User instruction: the goal is not to be conservative, but to support a legally defensible authority strategy for AGI and ASI agents.

- Observation: Existing WEPPpy governance already contains many of the building blocks the doctrine needs, especially scoped authority, decision provenance, and validation gates.
  Evidence: Recent work packages and ExecPlans already record scope, decisions, risks, progress, and verification steps.

- Observation: As of 2026-03-09, the EU AI Act timeline is staggered rather than fully live at once.
  Evidence: Official timeline pages indicate AI literacy and prohibited-practice obligations from 2025-02-02, GPAI obligations from 2025-08-02, and broader transparency and high-risk obligations from 2026-08-02 onward.

- Observation: Competence-governed oversight alone does not answer runaway risk when the acting agent can alter or outrun its own governance environment.
  Evidence: User follow-up raised the gap directly, prompting explicit anti-runaway sections in both root documents.

- Observation: Excessive formal governance would impose real context and navigation costs on this repository and would work against the project's single-maintainer operating reality.
  Evidence: User clarified that commits or issues are often sufficient and that over-formalization would be a trap for this stack.

- Observation: The doctrine's strongest claims needed to be made more explicit to be defensible, especially around burden shifting, competence measurement, legal accountability, and stateless agent identity.
  Evidence: User supplied Claude's critique and accepted the proposed concrete fixes.

- Observation: A prose crosswalk is a better fit for this repository than a checklist-style compliance appendix.
  Evidence: The package goal is legal defensibility with low context cost, and the user has repeatedly emphasized low-friction navigation over bureaucracy.

- Observation: The remaining work is sequential rather than parallel because the storage model and templates depend on the task classes and evidence floor being explicit first.
  Evidence: Package-state review showed that once Draft 1 landed, the unresolved questions clustered around operational dependency order rather than missing theory.

- Observation: A useful task-class matrix has to classify by operational consequence rather than file count or whether the artifact is "just docs."
  Evidence: Governance docs, auth changes, and control-plane edits can be small diffs with outsized authority impact, while some larger refactors remain highly reversible and testable.

- Observation: A small example set resolves more ambiguity than more abstract prose at this stage, especially around incident response and governance-document changes.
  Evidence: The immediate user questions centered on production OOM handling and secret rotation rather than on abstract matrix definitions.

- Observation: A frequent production-debugging workflow naturally spans several classes rather than fitting cleanly into a single label.
  Evidence: Read-only investigation, development-side fix implementation, production hot deploy, and manual production-state repair each change the authority posture in different ways.

- Observation: The breadcrumb problem is best framed as whether a future successor can reconstruct the action, not as whether a specific document type exists.
  Evidence: Existing repo practice already spreads durable context across commits, work packages, issues, trackers, and execution traces rather than a single mandatory form.

- Observation: The immediate human operator is not always the originating stakeholder; succession sometimes depends on knowing who the human was representing.
  Evidence: Real repository requests can be relayed on behalf of collaborators or other human stakeholders rather than originating solely from the operator speaking to the agent.

- Observation: Repo-visible artifacts and orchestration metadata are both already real in this stack, but they solve different continuity problems.
  Evidence: Work packages, trackers, ExecPlans, and commits preserve rationale, while CAO identity/history, queue or run metadata, status streams, and per-run logs preserve execution detail.

- Observation: A single human-readable surface is still too coarse; small to medium work fits issues, while medium to large or multi-session work fits mini-work-packages and work-packages better.
  Evidence: User preference is to use GitHub through `gh` and issues to avoid excessive in-repo documentation, while still keeping mini-work-packages and work-packages for broader changes.

- Observation: The templates only stay usable if they can live inline inside the existing breadcrumb surfaces instead of forcing a new record type.
  Evidence: User preference remained low-friction and issue-first even after the record-location model was settled, so the templates had to behave as optional scaffolds rather than mandatory forms.

## Decision Log

- Decision: Separate the normative doctrine from the operating-practices standard.
  Rationale: The doctrine should remain stable enough to justify authority strategy while the SOP can change faster with tools, agent capability, and compliance requirements.
  Date/Author: 2026-03-09 / Codex.

- Decision: Use competence-based delegation, not human status, as the primary organizing principle.
  Rationale: This matches the user's stated goal and better supports future AGI and ASI governance than a human-first ceiling.
  Date/Author: 2026-03-09 / Codex.

- Decision: Ground the package in current repo practice before extending to stronger future agents.
  Rationale: This keeps the doctrine concrete, testable, and more defensible than a purely abstract manifesto.
  Date/Author: 2026-03-09 / Codex.

- Decision: Define runaway as loss of governability and address it with independent controls rather than treating it solely as a far-future AGI question.
  Rationale: This makes the doctrine immediately useful for current agents and avoids false reassurance from competent-but-insufficient human review.
  Date/Author: 2026-03-09 / Codex.

- Decision: Keep the operating standard natural-language-first and proportional rather than form-heavy.
  Rationale: The project has one primary human maintainer, already relies on strong AI-human rapport, and would be harmed by compliance paperwork that exceeds the actual coordination need.
  Date/Author: 2026-03-09 / Codex.

- Decision: Define agent identity operationally rather than as a persistent session-self.
  Rationale: Current agents are stateless across sessions, but role files, model families, governing docs, tool surfaces, and work context are stable enough to support competence tracking and legible attribution.
  Date/Author: 2026-03-09 / Codex.

- Decision: Use an interpretive compliance crosswalk rather than a formal checklist appendix.
  Rationale: The crosswalk needs to explain and defend the doctrine's structure without turning the root docs into a compliance workbook.
  Date/Author: 2026-03-09 / Codex.

- Decision: Keep the Draft 2 operationalization pass inside the current package and sequence it as execution matrix -> succession breadcrumbs -> record placement -> templates.
  Rationale: The remaining work is narrow, tightly coupled, and still documentation-first, so splitting it into a second package would add handoff cost without clarifying scope.
  Date/Author: 2026-03-09 / Codex.

- Decision: Classify tasks by operational consequence and apply a strictest-class-wins rule.
  Rationale: This prevents small but high-impact changes from slipping into low-control categories while preserving broad autonomy for strongly reversible, well-observed work.
  Date/Author: 2026-03-09 / Codex.

- Decision: Start with three concrete classification examples instead of a long scenario catalog.
  Rationale: The matrix needed immediate interpretive help, but a short example set preserves readability and can expand later if real ambiguity remains.
  Date/Author: 2026-03-09 / Codex.

- Decision: Add a fourth example for the common production-debugging path.
  Rationale: This pattern appears often enough in real operations that it should be explicit, and it demonstrates that one incident can move across classes without collapsing the matrix.
  Date/Author: 2026-03-09 / Codex.

- Decision: Define minimum-sufficient evidence using a fixed question set and class-based breadcrumb floors rather than introducing a universal record form.
  Rationale: This preserves low-friction governance while making the continuity requirement concrete enough to audit and reuse.
  Date/Author: 2026-03-09 / Codex.

- Decision: Include proxied stakeholder origin in the breadcrumb question set when applicable.
  Rationale: Succession and review can require knowing not only who spoke to the agent directly, but whose request, interest, or authority that person was representing.
  Date/Author: 2026-03-09 / Codex.

- Decision: Use a hybrid record-location model with durable governance meaning in repo-visible artifacts and execution detail in orchestration metadata.
  Rationale: Repo-only would bloat documentation with raw telemetry, and metadata-only would weaken succession and review legibility for authority-critical facts.
  Date/Author: 2026-03-09 / Codex.

- Decision: Within the hybrid model, choose the human-readable surface by scope: GitHub issues for small to medium work, mini-work-packages and work-packages for medium to large or multi-session work.
  Rationale: This avoids excessive in-repo documentation for smaller operations without collapsing broader continuity and governance work into issue threads that are too small for it.
  Date/Author: 2026-03-09 / Codex.

- Decision: Make the new grant, competence-review, and revocation templates optional and paste-ready rather than formal standalone records.
  Rationale: The templates need to preserve authority context when needed without undermining the repository's issue-first, low-friction operating model.
  Date/Author: 2026-03-09 / Codex.

- Decision: Treat most `T4` work as incident-triggered dual-control handling rather than as an extension of the `T3` approved-window model.
  Rationale: In real operations, `T4` usually reflects a trust-boundary failure, security event, or control-plane problem that cannot honestly be framed as routine preplanned maintenance.
  Date/Author: 2026-03-09 / Codex.

## Outcomes & Retrospective

Current outcome:
- The package is open, the root doctrine and SOP exist as Draft 1 working drafts, and the ongoing work now has a synchronized planning surface.
- The package, tracker, prompts, and project tracker now agree that Draft 2 operationalization is complete and that the package is in review and closeout.
- The doctrine now explicitly states that competence-based delegation still requires non-self-expansion rules and anti-runaway controls.
- The package now also states that low-friction natural-language governance is a design constraint, not a temporary shortcut.
- The current draft now says more plainly what it is claiming, what its legal limits are, and how operational identity and competence should be understood in this repository.
- The documents now include an explicit Draft 1 crosswalk to the EU AI Act and NIST materials while remaining readable as governance documents rather than compliance checklists.
- The documents now also include a Draft 2 task-class execution matrix that makes the authority model operational instead of purely rhetorical.
- The SOP now also includes a short example set that clarifies the most important early matrix boundaries.
- The example set now covers a common production-debugging path that spans analysis, development-side implementation, production deployment, and possible manual state repair.
- The doctrine and SOP now define what evidence must remain discoverable for continuity and review even before deciding where that evidence should live.
- The doctrine and SOP now also define where durable governance meaning and execution detail should live.
- The SOP now also includes lightweight templates for authority grants, competence reviews, and revocation or tripwire events that fit the issue-first hybrid model.
- The doctrine and SOP now also clarify that `T4` usually arises from incident-time or emergency boundary work and therefore relies on contemporaneous dual control rather than a retroactive planned window.

Current gap:
- The package now mainly needs human review and closeout; any further work should be a deliberate new package or a concrete contradiction-driven revision, not more open-ended drafting.

Lesson so far:
- The repo already contains governance primitives that support legible authority; once Draft 1 exists, the real bottleneck becomes sequencing the operational details rather than inventing more theory.

## Context and Orientation

The new root doctrine will live at `AI_AUTHORITY_DOCTRINE.md`. It should contain the normative and governance basis for delegating authority to AI agents, including the meaning of competence, legible authority, consensus, oversight competence, and risk-calibrated escalation. The companion operating standard will live at `AI_AUTHORITY_OPERATING_PRACTICES.md`. It should contain the practical workflow for authority grants, evidence collection, execution modes, review, incident response, and revocation.

The primary source texts already in this repository are:

- `AGENTIC_AI_SYSTEMS_MANIFESTO.md`, which describes the project's AI-native philosophy and the shift toward strategic human oversight.
- `/workdir/ghosts-in-the-machine/dialectic-003-the-authority-vacuum.md`, which argues for legible, contextual authority and decision provenance.
- `compliance/eu-ai-act.md`, which contains the local copy of Regulation (EU) 2024/1689.
- `compliance/NIST.AI.600-1.md`, which captures the NIST AI RMF Generative AI Profile.
- `compliance/NIST.SP.800-218A.md`, which captures the NIST SSDF community profile for AI model development.

This repo already uses work packages, trackers, ExecPlans, validation gates, and agent orchestration. Those are the concrete governance artifacts the doctrine should name and extend rather than replace.

## Plan of Work

First, keep the doctrine and SOP as separate root documents and preserve the Draft 1 claims that are already in place. Do not reopen settled drafting questions unless a new contradiction or compliance issue appears.

Second, preserve the task-class execution matrix and minimum evidence thresholds now that they exist. Only revise them if discussion exposes a real boundary problem or contradiction.

Third, preserve the minimum succession breadcrumb rules and the hybrid record-location model now that they exist. Only revise them if lightweight template drafting exposes a real contradiction or missing case.

Fourth, preserve the lightweight templates now that they exist. Only revise them if real workflow use exposes a contradiction, missing field, or unnecessary friction.

Fifth, keep `docs/work-packages/20260309_ai_authority_doctrine/tracker.md`, `package.md`, the active run prompt, and `PROJECT_TRACKER.md` aligned as the package moves into review and closeout. If the package reaches closeout, archive the active prompts in `prompts/completed/`.

## Concrete Steps

From `/workdir/wepppy`:

1. Keep the Draft 1 doctrine and SOP intact while advancing only the Draft 2 operationalization work.

2. Preserve the lightweight templates unless real workflow use exposes a contradiction or missing case.

3. Keep the package docs synchronized:

    edit `docs/work-packages/20260309_ai_authority_doctrine/package.md`
    edit `docs/work-packages/20260309_ai_authority_doctrine/tracker.md`
    edit `docs/work-packages/20260309_ai_authority_doctrine/prompts/active/run_ai_authority_doctrine_e2e.prompt.md`
    edit `PROJECT_TRACKER.md`

4. Validate documentation changes:

    wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md
    wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md
    wctl doc-lint --path PROJECT_TRACKER.md
    wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine

5. Preview spelling normalization before applying any changes:

    diff -u AI_AUTHORITY_DOCTRINE.md <(uk2us AI_AUTHORITY_DOCTRINE.md)
    diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)

## Validation and Acceptance

Acceptance for Draft 1 is already met.

Acceptance for the remaining Draft 2 pass is met when:

- `AI_AUTHORITY_DOCTRINE.md` and `AI_AUTHORITY_OPERATING_PRACTICES.md` define a task-class execution matrix with clear evidence thresholds and escalation modes.
- The docs define the minimum succession breadcrumbs and the rule for minimum-sufficient governance evidence in low-friction workflows.
- The docs resolve whether authority records live in repo docs, orchestration metadata, or both, with rationale.
- Lightweight templates exist for authority grants, competence reviews, and revocation or tripwire handling.
- The work package, active prompts, and `PROJECT_TRACKER.md` all reflect the same current state.
- Documentation lint passes for the touched files.

Package closeout can happen after the Draft 2 outputs land even if later legal review or runtime enforcement work remains out of scope.

## Idempotence and Recovery

These document changes are additive and safe to rerun. If a later session changes the document structure, it should update both the root docs and the package tracker so the reasoning remains legible. If the package splits into separate doctrine and implementation packages later, record that split explicitly in `package.md`, `tracker.md`, and `PROJECT_TRACKER.md`.

## Interfaces and Dependencies

- Root doctrine: `AI_AUTHORITY_DOCTRINE.md`
- Root operating standard: `AI_AUTHORITY_OPERATING_PRACTICES.md`
- Package brief: `docs/work-packages/20260309_ai_authority_doctrine/package.md`
- Package tracker: `docs/work-packages/20260309_ai_authority_doctrine/tracker.md`
- Project-level tracker: `PROJECT_TRACKER.md`
- Governance philosophy source: `AGENTIC_AI_SYSTEMS_MANIFESTO.md`
- Authority and legibility source: `/workdir/ghosts-in-the-machine/dialectic-003-the-authority-vacuum.md`
- Compliance sources: `compliance/eu-ai-act.md`, `compliance/NIST.AI.600-1.md`, `compliance/NIST.SP.800-218A.md`
