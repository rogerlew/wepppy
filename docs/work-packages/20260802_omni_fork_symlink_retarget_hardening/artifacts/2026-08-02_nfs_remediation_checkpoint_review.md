# SURF-04A NFS Remediation Checkpoint Review

**Date**: 2026-08-02
**Trigger job**: `c4a6e8cc-a2cf-48bc-9d77-e97e7727a53b`
**Production failure**: NFSv4.2 returned `EINVAL` for
`renameat2(RENAME_NOREPLACE)`

## Contract Review

The first pass found stale renameat2 instructions, an inaccurate completed
status, and no executable actual-NFS evidence procedure. After correction, the
independent contract reviewer approved with no remaining medium/high findings.

## Security Review

The first pass identified that a raced directory cannot be restored with an
exclusive hard link. The contract now fails closed, confines that object to the
unpublished failed destination, forbids overwriting rename-back, and requires
whole-destination discard plus a fresh retry. The independent security reviewer
approved with no remaining medium/high findings.

## Disposition

The remediation uses ordinary rename into a newly created private quarantine,
exclusive hard-link restoration for hardlinkable objects, explicit failure for
non-hardlinkable races, and mandatory actual-NFS parity evidence. This
documentation checkpoint is approved as the implementation ancestor.
