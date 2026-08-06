# Omni Fork Symlink Retarget Hardening

**Status**: Reopened after production NFS incompatibility (2026-08-02)
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

The first implementation passed ext4 validation but production fork job
`c4a6e8cc-a2cf-48bc-9d77-e97e7727a53b` failed because the NFSv4.2 run mount
returned `EINVAL` for `renameat2(RENAME_NOREPLACE)`. The package is reopened to
remove that unsupported filesystem primitive without weakening no-clobber
behavior.

Production fork job `8dda9f7a-310f-4a16-8bae-501a2d0106d6` later failed on
2026-08-06 with the exact signature
`NotADirectoryError: Unsupported Omni scenarios child entry:
.mulch_15_sbs_map`. The regular dot file is a legacy access-log sidecar for
the real `mulch_15_sbs_map` child directory. This remediation simply skips
all dot-prefixed collection entries during link normalization without opening
or following them. Historical rsync/archive behavior and the privacy of copied
access logs are separate surfaces and are unchanged by this patch.

Included work preserves the current rsync command, creates relative links for
allowlisted Omni shared inputs, rebuilds copied legacy links from their semantic
destination location, validates containment, adds exact regressions, and
updates both clone producers and the composite-run compatibility helper.
Replacing rsync, generic symlink rewriting,
archive locking, queue wiring, production repair, and deployment are excluded.

## Acceptance

- [x] New Omni shared-input links are relative and resolve inside their run.
- [x] One- and multi-generation forks retarget recognized legacy links into the
  newest destination without requiring old targets to exist.
- [x] Rsync flags, exclusions, heartbeat behavior, and unrelated links remain
  unchanged.
- [x] Skip/undisturbify forks remove copied contrast-run symlinks whose root
  targets were intentionally excluded, without deleting materialized files.
- [x] Unsafe or ambiguous recognized entries fail explicitly before fork
  success; old targets are never followed or materialized.
- [x] Targeted and full tests, docs lint, correctness, QA, and security reviews
  pass with no unresolved medium/high findings.

## Compatibility, Security, and Signals

Link names and destination layout remain unchanged; only allowlisted targets
become destination-relative. The API and RQ envelopes remain unchanged.
Security review is required for path escape, scenario-name traversal, symlink
replacement races, special-entry collisions, cross-run disclosure, and partial
failure. Health means zero recognized links in a completed fork resolve outside
it. Normalization is bounded to `_pups/omni/{scenarios,contrasts}` and records
count/timing. The observation window is 30 days after any later deployment.

For the access-log compatibility amendment, the hypothesis is that skipping
dot-prefixed collection entries will eliminate the exact recurrence. The
primary health signal is zero recurrences over 30 days after deployment. The
guardrail is continued rejection of ordinary unexpected collection entries.

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

The access-log baseline is one confirmed failed fork. Codex owns exact
regression and review evidence; the WEPPcloud operator owns the 30-day
production recurrence observation. This compatibility rule adds no temporary
callus or sunset action.

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

## SURF-04B Skip-Omni Reset Amendment

The bounded follow-up at `../20260806_fork_skip_omni_reset/` composes this
package's checked fork-copy boundary with SURF-04 and DOM-25A/B. When explicitly
selected, it excludes the two collection nodes themselves and creates fresh
destination-only Omni state instead of normalizing copied child links. The
unchecked SURF-04A normalization contract remains unchanged, and SURF-04A is
not reopened or advanced.
