# WP12C Forest Acceptance

**Host**: `forest`
**Domain**: `wc.bearhive.duckdns.org`
**Compose topology**: `docker/docker-compose.dev.yml`
**Repository revision**: `187a856d47e522cfd7ed489a53d06007ed8e1bf7`
**Implementation candidate**: `b31eeb6252f5d5a1ac171277b0b2c9ea019354a5`
**Production scope**: none; production remains reserved for WP12

## Reader-First Deployment

The precheck confirmed exact host `forest`, the expected development Compose
topology, a source bind mount from `/home/workdir/wepppy` to `/workdir/wepppy`,
and repository HEAD `187a856d4`. Existing unrelated dirty files were not staged,
modified, or deployed as image content.

Only `weppcloud` and `rq-engine` were recreated. The command explicitly used
`--no-build --no-deps --force-recreate` and set
`WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED=false`; no image build, registry
operation, dependency recreation, orphan removal, worker restart, or production
action occurred.

Before recreation, the service container IDs were `08687d8adf04` for
`weppcloud` and `36e7af52fd52` for `rq-engine`. After recreation they were
`1be34cdc32e6` and `692e1eba223f`. Both containers reported exact repository
HEAD `187a856d4`. Both reported the Builder writer `false`; reader, preset
writer, and update flags retained their existing development value `true`.
Direct web and rq-engine health checks returned `200` with `"OK"` and
`{"status":"ok","scope":"rq-engine"}`.

## Reader Proof and Rollback Floor

The deployed `weppcloud` container ran the exact stored-authority matrix for:

- all five schema-v3 profile graphs and default configs;
- hostile climate-method broadening rejection for all five profiles;
- frozen historical Continental-US schema-v2 reopen/preview/apply without live
  graph recomposition;
- schema-v3 update from stored authority without live recomposition; and
- absent/schema-v1 update rejection before registry resolution and without
  writes.

Result: **14 passed** in 11.16 seconds.

An authenticated PowerUser request then proved the live API boundary:

- Builder description returned `200`, description schema `2`, and exactly
  `australia`, `canada`, `continental-us`, `europe`, and `global-earth` graphs.
- Builder create while writer-disabled returned `503` with
  `error.code="builder_writer_disabled"`.

This completes the required pre-create reader proof. Revision
`187a856d47e522cfd7ed489a53d06007ed8e1bf7` is the minimum post-create rollback
floor. Any rollback after an expanded-profile project exists must retain this
five-profile schema-v3 reader and the historical schema-v2 reader; disabling
writers remains allowed, but reverting to a schema-v2-only reader does not.

## Writer and Provider Acceptance

Partially accepted on 2026-08-29. The operator created projects for all five
Builder locales and successfully delineated a watershed for each. The operator
also validated the locale-specific landuse, soil, and climate option sets. A
subsequent redeploy confirmed the corrected Australia Land Use 2010–2011
selection, and legacy projects reopened and executed tasks successfully.

Closure still requires explicit reopen evidence for each newly exposed profile,
the three Continental-US station databases, and presence/health plus
representative real execution for every advertised provider family. The
operator evidence above must not be represented as successful landuse, soil,
or climate builds unless those builds are separately executed and recorded.
