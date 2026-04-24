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
- **Observation window**: default 14-30 days unless package states otherwise.

### 4) Implementation and Validation Gates (Required)

Hardening changes must be minimal and explicit:

- prefer explicit failures over silent fallback,
- add regression tests for exact failure mode,
- add contract/config tests when infra behavior is changed,
- preserve auth/security/locking boundaries.

Required gates:

- targeted tests for touched surfaces,
- pre-handoff sanity (`wctl run-pytest tests --maxfail=1`) unless blocked (document blocker),
- independent code review and QA review for medium/high-risk packages,
- dedicated security review artifact when security impact triage is `high`.

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
- docs drift from compose/runtime behavior,
- complexity rises without measurable reliability gain,
- mitigations accumulate but are never retired.

## Callus Softening Protocol (Required for Removal/Simplification)

Callus softening is expected. Defensive layers should not be permanent by default.

### Eligibility Gate

Softening is allowed only when all are true:

- regression risk is low to moderate,
- target incident class has remained stable or reduced over the observation window,
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
- [ ] Wrote hypothesis, health signals, guardrails, and observation window.
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
