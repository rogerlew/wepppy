# National soil service on wepp.cloud

## Authorized scope

The operator requests a full application deployment, including committed local-master
changes and required database migrations, in wepp1, wepp2, wepp3 order. Forest1 is
deferred. The CILogon registration and credential activation hold remains in force.
Use `scripts/deploy-production.sh` and the installed `wctl` preset; retain approved
release evidence and the prior images/configuration. Do not clear queues or caches.

## Soil service contract

Run one PostGIS database and Rust API on wepp1 using the `soil-data` Compose profile.
Publish the API only at the wepp1 Tailscale address, port 18080; the database has no
published port and uses a private internal network. All production clients select
`mirror-first` with endpoint `http://100.127.248.45:18080/Tabular/post.rest` and release
`forest-us-ssurgo-20261001-statsgo2-20161013-v1`. The historical release name identifies
the same immutable national content, not regional coverage. Preserve explicit project
source selections. SDA fallback remains bounded and visible in provenance.

Reuse the validated national import SQL and receipts from soil-data-access. Transfer
the import with a checksum and append a guarded activation transaction; mount the
result through PostgreSQL's initialization directory. Initialization is only for a
new empty soil volume. Existing volumes require inspection, never deletion or silent
reinitialization. Retain source revision, input checksum, row counts, active release,
and host-specific runtime identities. Fresh production credentials remain outside git.
Allow sufficient first-start time for the validated 22,073,263-row import; readiness
must use PostgreSQL TCP and the API's pinned-release health check.

## Application migration compatibility

Production was upgraded from `f6b8d27a901c` to `a7c1106e42b9` on 2026-11-18 UTC. The combined candidate adds
`a7c1106e42b9`, preserving legacy users while adding account provenance columns and
a unique normalized-email index. Read-only preflight found zero duplicate normalized
email groups among 5,482 users. Back up the application database and rehearse upgrade
on a restored copy, asserting both configured database and `current_database()`
before execution. Compare legacy user values, roles, OAuth links, and memberships.
Do not activate CILogon credentials. Apply the migration once on wepp1 before new
application code starts. Retain additive schema on compatible application rollback;
do not invoke destructive downgrade against newly created account state.

## Acceptance and recovery

Check all service health and worker registrations, authenticated application access,
and existing login workflows after the full rollout. Exercise real queued SSURGO
and STATSGO2 soil builds using disposable production canaries, verify base provenance
hashes and prepared soil artifacts, and confirm clients on all three hosts reach the
pinned national release. Reuse source parity receipts; full live SDA parity remains
deferred. Preserve old images and configuration and use canonical deployment recovery.
Migration rehearsal passed on a restored production backup: all pre-existing
table-column hashes match, including 5,482 user rows. See the retained
[receipt](../work-packages/20261118_ssurgo_json_provenance/artifacts/production-migration-rehearsal.json).
Live migration passed with 5,482 legacy account defaults verified. All three hosts
completed canonical activation; see the [production activation receipt](../work-packages/20261118_ssurgo_json_provenance/artifacts/production-activation.json)
for immutable image identities and generated-output checks.

## Deploying the same images across hosts

Build once on wepp1 with `--build-retained-candidate`. Preserve its private source
receipt and SHA-256. Export the exact common and renderer image IDs with Docker
save, transfer the archives with checksums, and load them on the worker hosts. Loading an archive saved by image ID does not
move Compose tags. Before candidate creation, explicitly tag each verified imported
ID with its configured Compose image name (for example `docker tag <common-id>
wepppy:latest`). Preserve the currently running images for rollback. Candidate
activation rejects tags that still resolve to the old release.
No registry is required. The worker hosts use the same architecture and runtime
identity (1002:130); confirm their effective configuration before activation.

Create a host-local candidate from loaded images using:

    scripts/deploy-production.sh --retain-images-from /private/source-receipt.json --source-receipt-sha256 <sha256> --skip-pull --skip-docker-prune

This validates the source receipt checksum, clean source/application equivalence,
image coverage, and availability of every exact image ID. It does not rebuild,
retag images, activate services, or inherit the source host's release approval.
Create the local release binding and resume its newly generated receipt through
`--resume-retained-candidate`. Host-specific configuration and rollback remain
part of the canonical script. Do not use an arbitrary `--skip-build` to bypass
these checks.

Export `COMPOSE_PROFILES=soil-data` when invoking the script on wepp1: retained
activation calls raw Docker Compose, which does not inherit wctl’s temporary
env file. Use `WCTL_COMPOSE_TIMEOUT_SECONDS=1800` for the first national import.
Confirm the raw activation service list includes both soil services.

For the first wepp1 soil installation, include `--new-service soil-db --new-service
soil-api` on both candidate creation and resume. These declarations are retained
in deployment options. A missing service without a declaration, a stopped existing
container, or an inventory error fails before cutover. The script records verified
absence with a zero-count rollback row and checks it again before stopping services.
On failure it removes only introduced containers, without deleting volumes, and
restores existing images. Failed cleanup or restoration retains the queue fence.
Inspect retained soil data and import logs before retrying; never automatically
remove a partially initialized database volume.

The first retained build completed at application source `9a50ccbf7d7ef279c1b13c41d3b72eeff77e7a39`.
The script-only repair may reuse those images after separately reviewed tooling
integration; it does not require another application build. Application migration
and all three host activations completed on 2026-11-18 UTC.

## Local firewall and shared source identity

All hosts retain the same Tailscale endpoint so a saved project can move between
workers without changing its source identity. On wepp1, Docker bridge traffic to
its own published Tailscale port reaches host INPUT; UFW initially dropped it.
The Compose-local API URL works only on wepp1 and must not become the persisted
project endpoint. Keep the database unpublished and the API bound to Tailscale.

The deployed persistent UFW rule allows only TCP from the production backend
bridge/subnet to the Tailscale address and port 18080:

    ufw allow in on br-86834dd1c298 from 10.20.0.0/24 to 100.127.248.45 port 18080 proto tcp comment soil-api-local-clients

Verify the actual backend bridge before recreating the Docker network; a recreated
network can have a different interface name. Rollback removes precisely this rule
with `ufw delete` and the same arguments. Retain the prior firewall snapshot and
check the API from actual application/worker containers on all hosts. This rule
does not allow public-interface clients or expose the soil database. The deployment
used a temporary root diagnostic container with only NET_ADMIN and SYS_CHROOT;
host files were read-only except `/etc/ufw` and `/run/ufw.lock` for the UFW update.
UFW also requires a writable temporary directory; provide ephemeral `/tmp` for
that command and verify both the active rule and `/etc/ufw/user.rules` afterward.
No application container privileges or host-wide firewall defaults changed.
