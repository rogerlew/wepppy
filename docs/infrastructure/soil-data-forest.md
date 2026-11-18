# Forest soil-data Compose integration

The dev Compose file owns soil-api and soil-db under profile soil-data. The API
joins the existing wepppy-net; PostgreSQL uses a separate internal network and has
no published port. The API uses its existing UID 10001, a read-only filesystem,
dropped capabilities and bounded resources. No client startup dependency on API
health is added: SDA fallback must work during mirror outages.

The initial release is forest-id-20261001-vi-20161013-v1: official Idaho SSURGO
(October 2026) plus Virgin Islands STATSGO2 (2016). Its manifest carries source URLs,
hashes and scope. It is regional coverage; missing mirror components permit SDA
fallback. Comprehensive live SDA validation is deferred until upstream recovery.

## Configuration and startup

SOIL_DATA_SOURCE_DIR selects the local soil-data-access checkout (default sibling
repository). SOIL_CODE_REVISION identifies its immutable compiled source revision.
SOIL_DATA_RELEASE pins the expected release. The API readiness probe requires that
release to be active and returns failure for missing data, wrong release or timeout.

Create soil_import_password, soil_serve_password and soil_database_url in the
ignored docker/secrets directory. The database URL uses role soil_serve, host
soil-db and database soil. Use host files with owner read/write only and named-user
read ACLs for UID 999 (two database password files) or UID 10001 (database URL).
Keep credentials outside /wc1, command arguments, logs and Git. Replacing files
must preserve those ACLs. Existing-volume password rotation requires coordinated
database-role and file changes; changing a file alone does not rotate a role.

Use wctl against docker/docker-compose.dev.yml for targeted dev orchestration.
Starting soil-db and soil-api does not refresh existing workers or web services.
Generate import SQL with soil-data-access/scripts/import_official.py and execute
with the database's soil_import role and psql ON_ERROR_STOP=1. Import validates
counts and relationships before atomically changing the active release. Never
import with the serving role or rewrite an existing release ID.

## Default activation and recovery

Set SOIL_DATA_MODE=mirror-first, SOIL_DATA_ENDPOINT=http://soil-api:8080/Tabular/post.rest
and the pinned SOIL_DATA_RELEASE in forest's deployment environment. All services
using the shared dev environment receive these settings on their next controlled
refresh. Preserve shared worktrees and drain affected workers before activation;
do not remount the task checkout into another task's running services.

New projects persist the default identity and policy. Existing unconfigured projects
resolve the deployment default without rewriting saved state. Existing saved
identities remain explicit. Opt an existing project in with the locked
configure_soil_data_source(..., fallback_to_sda=True) method. Setting the deployment
mode back to legacy-xml affects new/unconfigured projects only; explicitly restore
saved projects with configure_soil_data_source() when needed. Retain both caches.

The soil API/database are running for forest qualification. Global client-default
activation is a separate deployment step after integration approval. The Compose
file is a protected policy path: exact candidate SHA/digest approval is required by
the integration-history standard before merge. No forest1 or production activation
is included. Their deployment remains governed by scripts/deploy-production.sh.

## Acceptance evidence

Use real RQ jobs with the forest worker image, UID/GID and /wc1 mount. Read back base
soil sidecars and final wepp/runs/p*.sol files. Qualification uses a separate Redis
and queue; controlled DNS failure is confined to that worker. Direct official-file
reference caches retain unknown historical origin and are not represented as live
SDA retrievals. Compare bytes excluding only Build Date and Source File values.
Retain primary cold/warm, SDA warm-cache fallback and dual-failure results. Cold
XML fallback is additionally exercised against controlled verified TLS peers.
