# WP12D Reader-Floor Forest Acceptance

**Observation time**: 2026-08-28 00:41 UTC
**Host**: `forest`
**Domain**: `wc.bearhive.duckdns.org`
**Compose topology**: `docker/docker-compose.dev.yml`
**Reader-floor revision**:
`80f4810b7be59d90a64b4771f587eb360987a820`
**Checkpoint ancestor**:
`596ff5758ca83e6077b97f953431c2c881219840`
**Production scope**: none; production remains reserved for WP12

## Deployment

The precheck confirmed hostname `forest`, branch
`feature/project-owned-config`, the development Compose topology, and source
mounts from `/home/workdir/wepppy` into both application services. The exact
reader-floor revision was pushed before restart.

Only `weppcloud` and `rq-engine` were force-recreated with:

    docker compose --env-file docker/.env \
      -f docker/docker-compose.dev.yml up -d \
      --no-build --no-deps --force-recreate weppcloud rq-engine

The services retained image digest
`sha256:6ac7e71030467a10e5d73dc18893cbd85c9202976d4b1b561a19dbb0d7ef2b75`.
No image build, dependency recreation, orphan removal, worker restart,
registry operation, or production action occurred. Container identities
changed from `e5789e2eece4` and `37e7ac43a6cc` to `8f4d801bf32f` and
`8b3eb5f523f6`, respectively.

Both services reported Git revision `80f4810b7be59d90a64b4771f587eb360987a820`.
Direct WEPPcloud and rq-engine health checks returned HTTP 200 with `"OK"` and
`{"status":"ok","scope":"rq-engine"}`. Neither service logged a recent
error, traceback, critical event, or startup failure.

## Reader and Rollback Proof

Both application processes loaded all six checked-in structural records. A
real NoDb reopen through `Ron.getInstanceFromRunID(..., ignore_lock=True)` and
the production `capability_authority(...)` reader returned:

- historical schema-v2 run `matted-smooth`, Continental US, structure
  `aa548c9c4bc792b44fc89b97e2b71270d2bbf1002cc960aac005b6d52c351bc6`;
  and
- schema-v3 run `biomedical-sharp`, Continental US, structure
  `5296d3519d578164b6a5874a820991c935b394e5336aba41fe3e8f8d0dd4e29b`.

The post-restart structural selection ran inside `weppcloud` and passed all 10
selected tests. It covered historical identity, all five current schema-v3
identities, provider/default exclusion, genuine two-identity evolution through
the full validator, stored/live isolation, and production rejection of an
unknown self-consistent structure.

The capability-refresh writer remains absent: no refresh action, route, job,
transaction, browser control, or implementation symbol exists in the runtime
source. Existing project-config amendment and Builder flags retain their
preexisting development values but cannot expose the absent refresh operation.

Revision `80f4810b7be59d90a64b4771f587eb360987a820` is therefore the minimum
WP12D rollback floor for any later capability-refresh writer. A writer may be
implemented only as a descendant of this revision and must never persist a
structure absent from this reader's append-only catalog.
