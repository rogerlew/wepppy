# Bounded pilot deployment correctness review

Disposition: **PASS for the deployment mechanism and exact production backport.**
Production staging, active-job gate and installed-image/pilot acceptance remain
separate required gates. Reviewer: roads_contract_review; no deployment edits or
production actions performed.

## Scope and evidence

Read the canonical pilot deployment contract, workspace deployment changes,
`build_source_overlay.py`, and the exact detached candidate deployment script
against baseline `813d912be1c8f6f13b6fc60cecebbef9259cd36e`.
The production backport contains only the opt-in batch delta; it does not copy
unrelated current-HEAD runtime-secret/CAP changes.

Independent `wctl run-pytest` execution of source-overlay, deployment-plan and
deployment-execution tests: **56 passed**, retained in
`pilot-deployment-independent-tests.log`. Exact backport shell syntax passes.
Inspected retained actual image evidence in
`20261027_source_image_local_build.json` and
`20261027_source_image_metadata_build.json`; these prove the local build
mechanism, not parity against each production image.

## Correctness findings

No unresolved deployment-mechanism finding.

- Default and other targeted behavior remains behind unchanged branches. Batch
  mode derives the effective service image/configuration, rejects unsupported or
  inactive services and conflicting/destructive options, recreates only batch
  with `--no-deps`, and skips unrelated assets, health checks and pruning.
- Existing owned global suspension, default/batch active-job checks, renewal,
  warm-stop and owned-fence recovery remain in the canonical path. The change
  does not authorize stopping active scientific work or clearing foreign fences.
- The image helper accepts exactly five approved hashed Python sources, rejects
  source/destination symlinks, derives from the inspected local running baseline,
  disables build network/pulls, and introduces no installer/vendor/native step.
  Runtime configuration, distributions, native fingerprints and source metadata
  must match. Only approved modules' stale bytecode is removed/recompiled.
- The original image receives an owned rollback reference. Result evidence is
  flushed before service-tag promotion; baseline tag/container identity is
  checked again before promotion. Rollback requires the exact original image ID
  and the same fenced batch-only cutover, preserving deployment tooling until
  original-image acceptance.

At review time two application files in the prepared detached candidate were
stale relative to final runtime fixes. Parent confirmed this is an uninstalled
preparation snapshot and will refresh it and its manifest before staging.
This review approves the deployment tooling below, not that stale application
payload. Final application hashes and all eight genuine worker registrations
remain required before pilot admission.

## Reviewed tooling SHA-256

- Workspace `scripts/deploy-production.sh`:
  `7a9c20caa07e9770d62d462260be32acec589cdf5eb85e6ae82da7f5c2c4182a`
- Exact production-backport `scripts/deploy-production.sh`:
  `74866cfb081699157134c2c7f450019adaeeeff96d6a63c95bf74dde0f4fbf92`
- `scripts/build_source_overlay.py` (identical in both checkouts):
  `b5493432a3c3cf901a0cfe0d7d4647f72658c831bb7c49afb7d9dc4553d5836f`
