# Omni Fork Symlink Retarget Hardening

**Status**: Open (2026-08-02)
**Package ID**: SURF-04A
**Timezone**: UTC
**Security impact**: `high`

## Overview

Keep `rsync -a` for fork performance while making copied Omni child workspaces
self-contained. New Omni shared-input links become location-relative, and each
fork normalizes recognized legacy links into the destination before success.

## Trigger and Scope

Production run `mdobre-intensive-darling` inherited scenario links through
multiple forks. Its `prescribed_fire/climate` link still named deleted ancestor
`mdobre-facile-deviousness`, causing archive jobs
`65717fb6-db0b-47e8-aa28-602dc798a18b` and
`b4eeaff3-f2ff-4107-a0ff-418638cb15dd` to fail.

Included work preserves the current rsync command, creates relative links for
allowlisted Omni shared inputs, rebuilds copied legacy links from their semantic
destination location, validates containment, adds exact regressions, and
updates both clone producers and the composite-run compatibility helper.
Replacing rsync, generic symlink rewriting,
archive locking, queue wiring, production repair, and deployment are excluded.

## Acceptance

- [ ] New Omni shared-input links are relative and resolve inside their run.
- [ ] One- and multi-generation forks retarget recognized legacy links into the
  newest destination without requiring old targets to exist.
- [ ] Rsync flags, exclusions, heartbeat behavior, and unrelated links remain
  unchanged.
- [ ] Skip/undisturbify forks remove copied contrast-run symlinks whose root
  targets were intentionally excluded, without deleting materialized files.
- [ ] Unsafe or ambiguous recognized entries fail explicitly before fork
  success; old targets are never followed or materialized.
- [ ] Targeted and full tests, docs lint, correctness, QA, and security reviews
  pass with no unresolved medium/high findings.

## Compatibility, Security, and Signals

Link names and destination layout remain unchanged; only allowlisted targets
become destination-relative. The API and RQ envelopes remain unchanged.
Security review is required for path escape, scenario-name traversal, symlink
replacement races, special-entry collisions, cross-run disclosure, and partial
failure. Health means zero recognized links in a completed fork resolve outside
it. Normalization is bounded to `_pups/omni/{scenarios,contrasts}` and records
count/timing. The observation window is 30 days after any later deployment.

## Failure Signature and Hardening Hypothesis

Exact signature:
`FileNotFoundError: [Errno 2] No such file or directory:
'/wc1/runs/md/mdobre-intensive-darling/_pups/omni/scenarios/prescribed_fire/climate'`.

If all producers create relative destination-owned links and every fork
transactionally normalizes the exact legacy matrix before success, then no
recognized link in a completed descendant will depend on an ancestor run.
Guardrails are unchanged rsync argv/copy behavior and no material fork p50/p95
wall-time regression. Danger signals are any completed out-of-run/broken
recognized link, raw link/replace exception, temporary residue, rollback
failure, foreign-tree mutation, or material latency increase.

Baseline is two archive failures on one production descendant and confirmed
links spanning two ancestor generations. Codex owns implementation/review;
operators own post-deployment wall-time and 30-day recurrence observation. No
temporary retry, feature flag, delay, or compatibility callus is introduced;
there is therefore no sunset item.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **Decision provenance captured**: yes, in the contract decision.

## Related Work

- `../20260729_pure_ui_fork_console_contract/`
- `../20260802_archive_mutation_symlink_hardening/`
- `docs/ui-docs/weppcloud-project-forking.md`
- `wepppy/rq/project_rq_fork.py`
- `wepppy/nodb/mods/omni/omni_clone_contrast_service.py`
- `wepppy/weppcloud/utils/helpers.py`
