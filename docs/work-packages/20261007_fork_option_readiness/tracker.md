# Tracker: Fork Option Availability and Readiness

Timezone: UTC. Updated: 2026-10-07 23:09 UTC.
Base: `918b3ca0a1639c0ec057decbf4fd1b6bac25b10b`.
Phase: proposed contract checkpoint; runtime files untouched.

## Progress

- [x] Diagnose all three affected forks from wepp1 logs, RQ, and filesystem.
- [x] Draft capability/readiness contract, decision, and execution plan.
- [x] Operator accepted the concrete checkpoint, checkpoint commit, two
  independent reviewer agents, and implementation on 2026-10-07 UTC.
- [ ] Complete independent reviews and commit the standalone checkpoint.
- [ ] Implement, validate, review, and document the bounded change.

## Decisions and findings

The UI restrictions do not replace backend no-op compatibility. Distinguish
unused/empty Omni from configured or retained scenario/contrast state. Preserve
strict checks on existing controllers and unsafe filesystem entries.
All additional details and rationale are in the draft current contract.

The operator explicitly approved the checkpoint, reviewers, and implementation
on 2026-10-07 UTC. No production action is included.

## Validation

All six touched/new Markdown files pass documentation lint; diff checks pass.
No implementation or new runtime tests yet.
Existing production diagnosis is not evidence that the proposed fix is deployed.
