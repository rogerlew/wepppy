# Bounded pilot deployment preparation
Historical source-only preparation. The later operator-authorized full canonical deployment and bounded pilot are complete; see [current acceptance](20261027_shared_pilot_acceptance.md). The retained baseline/backport instructions below were not the selected activation path. General async remains disabled.
Production remains at `813d912be1c8f6f13b6fc60cecebbef9259cd36e` on both hosts,
with clean tracked source (read back before staging). The detached local
candidate checkout starts at that revision; only the task delta is backported.
It excludes the unrelated current-HEAD runtime-secret validator additions.

The exact backport passed targeted batch plan and fenced execution checks for
both full and worker-only presets through `wctl`. Main checkout deployment
regressions: 55 passed. The native image derivation was exercised against local
owned images, preserving runtime configuration, selected native package hashes,
Python distributions and source file ownership/modes. Local image evidence is
mechanism validation; each production image still requires its own exact-base
build and parity acceptance.

## Source staging and recovery

The final reviewed payload is one Git patch against the retained baseline,
containing exactly the five approved Python files plus the canonical deployment
script and its source-image helper. Before applying, retain the original bytes,
absence, owner/group/mode, host identity, revision and service/container/image
identities in a private host staging directory. Require clean tracked source,
`git apply --check`, exact baseline hashes and reviewed candidate hashes. Apply
with `git apply`; verify the complete seven-path hash/absence manifest and the
actual targeted Compose plan before activation. No pull or branch change.

Use the canonical entry point with each host's exact-base source manifest.
Wepp1 precedes wepp2. The default/batch active-job gate remains mandatory.
A build/tag or activation failure retains rollback image references and evidence;
never prune during this operation.

Recovery restores only the five application paths using the reverse reviewed
patch after checking their candidate hashes. Restore the original service image
tag from its retained immutable image ID, then use the still-installed canonical
`--targeted-batch --batch-rollback-image-id` path. After original runtime acceptance,
reverse the two deployment-tool paths last. Unexpected source drift blocks
restoration for explicit reconciliation; backups are never overwritten.
