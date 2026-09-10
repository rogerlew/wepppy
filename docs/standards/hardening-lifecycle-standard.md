# Hardening and Callus-Softening Standard

Standard lifecycle for incident-driven hardening work and for later simplification ("callus softening") of temporary mitigations.

## Purpose

Use this standard to keep reliability hardening disciplined, testable, and reversible. It defines:

- how to scope and document incident hardening,
- how to identify health vs danger signals,
- where to discover prior hardening efforts,
- and how to run hypothesis-driven softening with test/review gates.

## Applies When

Apply this standard when any of the following are true:

- recurring production or test-production failures need remediation,
- operators request startup/readiness/retry/failover hardening,
- code introduces temporary defensive logic, toggles, delays, or wrappers,
- a team wants to remove or reduce prior defensive complexity.

## Authority and Working Behavior

The requested task defines the agent's authority. Preserve existing working
behavior unless the operator requests its change. Image publication, dependency
updates, cleanup, refactoring, and generic security advice do not authorize
additional changes to runtime identities, permissions, authentication, isolation,
report outputs, defaults, or established user workflows. Do not bundle such
changes into otherwise authorized work. Existing explicit authorization remains
valid; routine implementation within that scope does not require another approval.

Before proposing an unrequested security change, identify the reachable threat
in the actual deployment, the attacker's required access, existing protections,
and the incremental benefit relative to compatibility and operational cost.
A best-practice label, scanner recommendation, or reviewer preference is not a
substitute for that explanation or for operator approval. Retaining the working
design is a valid outcome. Prepare a concrete proposal and seek approval before
implementing the additional behavior change; continue independent authorized work.

Reviewers must reject unauthorized scope expansion and regressions in valid user
behavior even when a security checklist passes. A security review cannot grant
operator authority or substitute for workflow correctness. Do not weaken these
requirements by changing the contract to match an unrequested implementation.

Rationale: the August 2026 auxiliary-image publication work changed the DEVAL
renderer identity without preserving access to existing run data. Group repairs
and a future-write permission fix left existing owner-only inputs broken. The
September 2026 recurrence demonstrated that generic hardening and isolated green
checks can impose substantial operational harm without establishing an
application-specific benefit. These rules constrain scope, not ordinary bug fixes;
they do not introduce a new review framework or require approval for every edit.

## Terms

- **Hardening**: targeted changes that reduce recurrence, blast radius, or operator toil for a confirmed failure mode.
- **Callus**: a defensive layer added during hardening (for example retry logic, startup delays, fallback branches, feature flags, safety wrappers).
- **Callus softening**: controlled reduction/removal of calluses when evidence shows risk is now low enough.
- **Hypothesis**: explicit statement predicting measurable outcomes from a hardening or softening change.
- **Sunset criteria**: conditions and date that define when a temporary callus must be reviewed for removal.

## Lifecycle (Required)

### 1) Trigger and Scope Freeze

Capture concrete failure evidence before coding:

- job id(s), route(s), stack traces, timestamps, host/environment,
- incident signature text (exact error class/message),
- user/operator-visible impact.

Capture the valid-state baseline that reached the failure. Explicitly classify
whether relevant resources were absent, empty, populated, legacy, or malformed.
Normal absence or a never-used optional feature is a product state, not an
attack case.

Write a one-sentence scope boundary:

- "Fix confirmed failure path X without broad refactor Y."

### 2) Precedent Discovery (Required)

Before implementing, discover prior similar hardening work.

Primary places to look:

- `PROJECT_TRACKER.md` (In Progress and Done sections),
- `docs/work-packages/*/package.md` and `tracker.md`,
- `docs/mini-work-packages/`,
- `docs/standards/`.

Useful discovery commands:

```bash
rg -n "hardening|incident|retroactive|retry|fallback|startup delay|readiness" PROJECT_TRACKER.md docs/work-packages docs/mini-work-packages docs/standards -S
```

Required output in package docs:

- list of related prior packages/standards,
- what was reused,
- what was intentionally different and why.

### 3) Hardening Hypothesis and Signals (Required)

For each hardening change, record:

- **Hypothesis**: "If we change A, then signal B should improve within window W."
- **Primary health signal(s)**: recurrence rate, error class frequency, queue backlog recovery time, operator retries, etc.
- **Guardrail signal(s)**: latency, startup time, false-positive retries, config complexity, flake rate.
- **Valid-state guardrail(s)**: false rejection or new user-visible exceptions
  for absent, empty, populated, and supported legacy states.
- **Observation window**: default 14-30 days unless package states otherwise.

When no durable monitoring owner or scheduler exists, a package may use a
**stateless recurrence-triggered observation model** instead of an elapsed-time
window. That model must:

- capture a bounded pre/post-rollout signal snapshot before closure;
- promote exact health and danger signals into the canonical operator or
  subsystem documentation;
- define which future events require a new incident/work package that cites and
  reassesses the prior hardening; and
- retain or retire recovery material by an observable lifecycle event, not by
  somebody remembering a calendar date.

Do not reopen or mutate a closed work package. A recurrence creates a new
execution record and uses the prior package as precedent.

### 4) Implementation and Validation Gates (Required)

Hardening changes must be minimal and explicit:

- prefer explicit failures over silent fallback,
- add regression tests for exact failure mode,
- add contract/config tests when infra behavior is changed,
- preserve auth/security/locking boundaries.
- prove security and containment controls do not interfere with valid user
  states.

Required gates:

- targeted tests for touched surfaces,
- a direct, unmocked regression at the boundary that produced the incident,
- a valid-state matrix covering absent, empty, populated, supported legacy,
  and hostile states where applicable,
- pre-handoff sanity (`wctl run-pytest tests --maxfail=1`) unless blocked (document blocker),
- independent code review and QA review for medium/high-risk packages,
- dedicated security review artifact when security impact triage is `high`.

### Recurrence and Restoration

The first recurrence after a claimed fix invalidates that fix's completeness.
Reassess the original change and the full failing boundary before adding another
patch. Prioritize restoring the known working workflow; consider a scoped reversal
of the causal change within existing authorization when safer than accumulating
mitigations. Do not automatically roll back unrelated work or weaken unrelated
access controls. Create a new incident record rather than editing a closed package.

Distinguish a recovered job from a durable fix. One-file repairs, successful health
checks, cached reports, and fresh empty fixtures cannot establish compatibility
with existing projects. Completion requires the previously failing workflow with
representative legacy data, newly generated data, every participating execution
identity/host, and actual output readback. Verify the fix is retained by supported
restart and deployment paths. Preserve the regression at the responsible test or
deployment boundary and block that rollout when the workflow check fails; reuse
existing validation entry points rather than adding a new framework by default.

Report what was recovered, what was permanently corrected, and any unverified
rollout scope separately. Do not call the incident fixed while necessary coverage
or rollout remains incomplete, or use a large unrelated test count as its proof.

### 5) Documentation Expectations (Required)

For hardening packages, documentation is part of the deliverable.

In `package.md` include:

- trigger/failure signatures,
- scope boundary and non-goals,
- health and danger signals,
- sunset criteria for temporary calluses,
- related prior packages.

In `tracker.md` include:

- timeline from incident to fix,
- decision log with rationale,
- signal snapshots (baseline vs post-change),
- unresolved risks and explicit owner.

In `artifacts/` include at minimum:

- code review findings + disposition,
- QA review findings + disposition,
- security review findings + disposition (required when triage is `high`).

In `PROJECT_TRACKER.md` include:

- lifecycle state updates,
- concise summary with concrete outcomes and validation evidence.

Retroactive packages are acceptable and should include exact timestamps and validation evidence captured after implementation.

## Health vs Danger Signals

Use these signals to evaluate whether hardening is healthy.

### Health Signals

- recurrence of the target error class decreases,
- same incident requires fewer manual operator steps,
- regression tests clearly cover the incident signature,
- contracts are explicit and validated by tests,
- review findings are dispositioned (not deferred without owner/date),
- docs and runtime behavior remain aligned.

### Danger Signals

- same incident signature reappears after "hardening",
- knobs/retries/delays increase without owners or sunset dates,
- silent fallback paths mask root causes,
- safety controls reject expected absence or other valid user states,
- review evidence covers hostile states but omits the zero-data or never-used
  feature path,
- docs drift from compose/runtime behavior,
- complexity rises without measurable reliability gain,
- mitigations accumulate but are never retired.

## Callus Softening Protocol (Required for Removal/Simplification)

Callus softening is expected. Defensive layers should not be permanent by default.

### Eligibility Gate

Softening is allowed only when all are true:

- regression risk is low to moderate,
- target incident class has remained stable or reduced over the declared
  elapsed-time window, or the recurrence-triggered package has current rollout
  evidence and a new package dedicated to the proposed softening,
- rollback path is documented and fast,
- tests cover both current behavior and intended softer behavior,
- code + QA review gates are planned (and security review if surface is high-impact).

### Softening Plan

Document a hypothesis-driven plan:

- callus being reduced/removed,
- expected benefit (simpler flow, lower latency, lower operator toil, fewer false alarms),
- guardrail metrics and fail conditions,
- canary or phased rollout approach,
- rollback trigger and command path.

### Acceptance

Softening is accepted only if:

- guardrails stay within thresholds,
- no medium/high unresolved review findings remain,
- post-change signals match or improve from baseline,
- package docs capture the final keep/reduce/remove decision.

## Agent-Manageable Checklists

### Hardening Checklist

- [ ] Captured incident signature and impact.
- [ ] Searched and linked prior hardening precedent.
- [ ] Wrote hypothesis, health signals, guardrails, and either an elapsed-time
  or stateless recurrence-triggered observation model.
- [ ] Added regression tests for exact failure path.
- [ ] Ran required validation and review gates.
- [ ] Updated package docs, artifacts, and `PROJECT_TRACKER.md`.

### Softening Checklist

- [ ] Confirmed eligibility gate (low-moderate risk + stable signals).
- [ ] Wrote softening hypothesis and rollback criteria.
- [ ] Added/updated tests proving both safety and simplification intent.
- [ ] Completed required review gates.
- [ ] Recorded keep/reduce/remove outcome with evidence.

## References

- `AGENTS.md`
- `docs/work-packages/README.md`
- `docs/prompt_templates/package_template.md`
- `docs/prompt_templates/tracker_template.md`
- `docs/prompt_templates/security_review_template.md`
