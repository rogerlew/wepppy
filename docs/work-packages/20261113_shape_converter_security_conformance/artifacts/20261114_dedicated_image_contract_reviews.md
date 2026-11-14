# Dedicated image contract reviews

## Correctness review

Independent review found one High and two Medium contract gaps before
implementation:

- Stale executable plan text still prohibited the dedicated GDAL upgrade.
- The known wepp1 shared-image regression test and merged Compose assertions were
  not named in the validation plan.
- Direct pins did not constrain compatibility-critical transitive dependencies,
  including NumPy.

Resolution: the plan and tracker now distinguish the unchanged common image from
the dedicated candidate, name the Docker regression and merged-configuration
checks, and require a fully resolved hash-locked dependency inventory.

## Security review

Independent review found no Critical or High security issue and four Medium
contract gaps before implementation:

- The base and Python supply-chain inputs were not immutably identified.
- Vulnerability disposition addressed only reachable Critical findings.
- Health acceptance could be misconstrued as second-sandbox evidence.
- Secret isolation covered resolved Compose but not build context, final image,
  or running-container inspection.

Resolution: the base is digest-pinned, Python inputs must be hash-locked, every
reachable Medium-or-higher finding requires remediation or explicit operator
risk acceptance, readiness-string evidence is explicitly nonconformant for M4,
and a Dockerfile-specific allowlist plus image/runtime inspection is required.

Both reviews therefore permit implementation only after these amendments. The
amendments are now part of the active ExecPlan, canonical specification, tracker,
and dedicated-image decision artifact.
