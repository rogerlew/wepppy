# SURF-04A Skip-Mode Amendment Review

**Date**: 2026-08-02
**Scope**: post-checkpoint skip/undisturbify contract amendment

## Contract Review

The first pass rejected the amendment because the root-target preflight rule
conflicted with intentionally excluded `wepp/runs` targets, the normalizer mode
interface was stale, the durable guide lacked a pending label, and the required
mode-matrix evidence was incomplete.

After correction, the independent contract reviewer approved with no remaining
medium or high findings. Removal mode now forbids root-target access, carries
the effective boolean explicitly, preserves materialized files, and requires
all flag combinations plus exact rollback evidence.

## Security Review

The first pass rejected direct check-then-unlink because a leaf swap could
delete a regular file. The amendment was changed to require atomic quarantine,
post-move identity verification, retained quarantine through validation, exact
rollback, commit-only cleanup, and a deterministic swap regression.

The independent security reviewer then approved with no remaining medium or
high normative findings. Final implementation review must confirm cleanup only
unlinks a verified quarantine and restore collisions never overwrite an
occupant.

## Disposition

All checkpoint findings are accepted and incorporated into the normative
contract, ExecPlan, package tracker, durable guide, and required evidence. The
amendment is approved for a standalone documentation ancestor commit before
its implementation is committed.
