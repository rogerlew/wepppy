# WEPPcloud image and Compose compatibility inventory

## Evidence boundary

- Baseline WEPPpy source: `2dedf916cb5ba430454dccc437ff0eb8fcb11daa`.
- Inventory date: 2026-08-13 UTC.
- Protected files were read only. Their baseline/current Git blob hashes are identical and are recorded below.
- Secret names and mount destinations were inspected from tracked configuration. No secret file under `docker/secrets/` was opened, copied, or generated.
- The local smoke build used the working-tree Docker context. Final acceptance also exercised the exact GHCR digest built from source `ed1b538df02a8db0d709257ea9dacc330c56b9d9`.

## Production service inventory

The protected base file `docker/docker-compose.prod.yml` defines a broad production system. The common `docker/Dockerfile` image is used by `weppcloud`, `browse`, `download`, `dtale`, `profile-playback`, `elevationquery`, `metquery`, `wmesque`, `wmesque2`, `query-engine`, `shape-converter`, `rq-engine`, both ordinary RQ workers, the fork/archive worker, and `scheduler`. Other images provide `fcgiwrap`, `weppcloudr`, `webpush`, `status`, `preflight`, `cap`, `caddy`, `f-esri`, `redis`, `postgres`, and `postgres-backup`.

| Surface | Production contract | Private-canary compatibility disposition |
| --- | --- | --- |
| Caddy | Host port 8080 in the base stack; ports 80/443 in the wepp1 override. Routes health, static files, WEPPcloud, multiple microservices, Git/FCGI, data browsing, CAP, dashboards, and reports. | Keep only loopback HTTP 18080 to container 8080, `/health`, `/weppcloud/health`, `/weppcloud/static/*`, `/weppcloud` redirect, and `/weppcloud/*` proxy. No hostname or public route. |
| WEPPcloud | Gunicorn on 8000; host port 8000 by default; health check `/health`; 4 workers/2 threads in the base and 10 workers/4 threads on wepp1. | One worker/two threads on internal port 8000; no host port. Caddy-proxied `/weppcloud/health` and root are exercised. |
| Redis | Host/container 6379, password file, named persistent volume, append-only and snapshot settings, health check authenticated `PING`. | Digest-pinned Redis on internal network only, no host port, no persistence, synthetic required password, authenticated health check. |
| PostgreSQL | Host/container 5432, password file, persistent data volume, backup service, and `pg_isready`. | Not included. Smoke uses disposable SQLite because this phase is prohibited from using production PostgreSQL credentials. A reviewed external PostgreSQL connection remains a live-canary prerequisite. |
| Static files | Caddy bind-mounts tracked WEPPcloud and usersum static trees. | Caddy bind-mounts one tracked compatibility fixture read-only; proves the route and file-server contract without production storage. |
| Storage | Common services mount `/wc1` and `/wc1/geodata` (or `/geodata/wc1` and `/geodata` on host overrides); Caddy exposes selected geodata paths. | App receives ephemeral `tmpfs` at `/wc1` (writable by UID 1000/GID 993) and `/geodata` (mode 0550); no NFS or host dataset. Caddy has no geodata route. |
| Workers/sockets | `rq-worker` and `rq-worker-batch` mount `/var/run/docker.sock` in the base, wepp1, and worker stack. Worker-only Compose also requires Redis, PostgreSQL, Flask, external-data, and Discord inputs. | Every worker and scheduler is absent; `/var/run/docker.sock` is absent. Worker compatibility is deferred. |
| Auxiliary ports | FCGI 9000; browse 9009; download 9011; D-Tale 9010; profile playback 8070; elevation 8002; meteorology 8004; WMesque 8003; WMesque2 8030; query engine 8041; shape converter 8060; RQ engine 8042; WEPPcloudR 8050; status 9002; preflight 9001; CAP 3000. | All absent. Requests needing them are not claimed by the compatibility contract. |

## Secret and startup inventory

The durable operator contract is now
[`docs/infrastructure/weppcloud-web-runtime-contract.md`](../../../infrastructure/weppcloud-web-runtime-contract.md).
This section records the compatibility investigation that led to it.

The production base declares these secret IDs: `redis_password`, `discord_bot_token`, `postgres_password`, `flask_secret_key`, `flask_security_password_salt`, `wepp_auth_jwt_secrets`, `agent_jwt_secret`, `wepp_mcp_jwt_secret`, `dtale_internal_token`, `cap_secret`, `oauth_github_client_secret`, `oauth_google_client_secret`, `zoho_noreply_email_password`, `opentopography_api_key`, `climate_engine_api_key`, and `admin_password`.

The minimum web process requires non-empty Flask `SECRET_KEY` and `SECURITY_PASSWORD_SALT`. The smoke contract also supplies a separate synthetic `AGENT_JWT_SECRET` and password-protected Redis. OAuth, SMTP, CAPTCHA/CAP, WEPP JWT, MCP JWT, D-Tale, admin, and external-data credentials are omitted.

The first smoke boot exposed a legacy import-time requirement: `weppcloud2.discord_bot.discord_client` opens `/workdir/weppcloud2/weppcloud2/discord_bot/.bot_token` while web blueprints import RQ modules, even when Discord notifications are disabled. No real Discord credential is required. The smoke stack follows the existing worker convention and mounts `/dev/null` at that exact path. This coupling is an unresolved startup design need for the later Kubernetes canary: supply an empty file or fix the upstream import boundary; do not inject a Discord token.

The web root and health route start with SQLite for this bounded smoke. Database-backed user actions are not claimed. The live canary must provide reviewed PostgreSQL connectivity and schema before those paths can pass.

## Caddy route reduction

Production Caddy returns its own `/health` and `/weppcloud/health`, serves multiple static/data trees, and proxies many auxiliary applications. The compatibility Caddy keeps `/health` as proxy health, but sends `/weppcloud/health` through the normal `/weppcloud/*` strip-prefix and reverse-proxy path to prove the Flask process is reachable. It also proves the static route with `/weppcloud/static/compatibility.txt`. Every other production Caddy route is intentionally absent, including `/git`, `/cap`, query/RQ engines, browse/download/D-Tale, public geodata/share trees, profile playback, status/preflight, and external redirects.

## Image build inputs and reproducibility limits

The GitHub workflow builds repository context `.` with `docker/Dockerfile` for `linux/amd64` and the existing production-compatible identity arguments `APP_USER=roger`, `APP_GROUP=docker`, `APP_UID=1000`, and `APP_GID=993`. The output tag is `ghcr.io/<lowercase-owner>/wepppy:sha-<full-source-SHA>` and the workflow reports `ghcr.io/<lowercase-owner>/wepppy@sha256:<digest>`.

The publication run pinned the Dockerfile frontend, both base images, uv `0.12.3`, and all five sibling Git repositories. The exact inputs are recorded in `.github/workflows/publish-weppcloud-image.yml`. Debian package indexes and DuckDB's downloaded `spatial` extension remain externally resolved, so independently repeated builds are not guaranteed byte-identical. The published artifact itself is immutable at `ghcr.io/rogerlew/wepppy@sha256:ee92666229df8fdffe4b06b1dff2cfd0e9e06823ada59915c8b492d8a468eb51`.

### Git LFS hydration correction (2026-08-20)

The original publication workflow checked out source without hydrating Git LFS.
The resulting image copied pointer stubs into the runtime tree. In particular,
`wepppy/climates/cligen/2015_stations.db` was a 131-byte pointer rather than the
356,352-byte SQLite catalog. WEPPpy consequently entered its development
fallback and selected `tests/neverland_.par` (Lewiston) for a Lake Tahoe run.
The original digest is therefore invalid for climate-station selection and must
not be promoted further.

The corrected publication contract is fail-closed at two boundaries:

1. GitHub Actions explicitly enables Git LFS, runs `git lfs install --local`,
   pulls and checks out every tracked object, and verifies every path reported
   by `git lfs ls-files` before invoking BuildKit.
2. `docker/Dockerfile` scans the copied repository tree for pointer headers and
   fails the build if any remain. Vendored sibling repositories now use a hard
   `git lfs pull` and receive the same copied-tree scan; LFS download failure is
   no longer ignored.

At correction time the repository inventory contained 639 LFS objects totaling
approximately 1.26 GB. A complete local hydration and checkout succeeded, all
639 tracked paths passed verification, and the hydrated Cligen catalog opened
as SQLite with 2,765 station rows. A new immutable digest still must be
published and deployed before climate integration testing resumes.

GitHub Actions run `31739217249` built source `ed1b538df02a8db0d709257ea9dacc330c56b9d9`, pushed tag `ghcr.io/rogerlew/wepppy:sha-ed1b538df02a8db0d709257ea9dacc330c56b9d9`, and reported digest `sha256:ee92666229df8fdffe4b06b1dff2cfd0e9e06823ada59915c8b492d8a468eb51`. An authenticated digest pull succeeded. An unauthenticated manifest request returned HTTP 401, demonstrating that the package was not publicly readable without changing repository or package settings.

## Protected-file non-mutation evidence

`git diff --exit-code 2dedf916cb5ba430454dccc437ff0eb8fcb11daa -- <protected files>` returned success. Current blob hashes:

| Protected file | Git blob hash |
| --- | --- |
| `docker/docker-compose.prod.yml` | `b1ac1703e7a72b96cf8a1f0f31f2f2cd5637475f` |
| `docker/docker-compose.prod.wepp1.yml` | `c33cc347c218c3195887e9751b18831f80531547` |
| `docker/docker-compose.prod.wepp3.yml` | `20cefbc8809f3c4a834298042d306f5be114874c` |
| `docker/docker-compose.prod.worker.yml` | `523d3c724bc6800734039c332b2f364d33eb8326` |
| `docker/docker-compose.prod.worker.override.yml` | `c15dd40914bd243e8f727b0fdbca8bf47f43a3aa` |
| `docker/docker-compose.prod.worker.forest.override.yml` | `2cd10dfca414173080d3e41c6da718538655c4ff` |
| `docker/caddy/Caddyfile` | `2bf78e60e2ea66618f8cc45dec52d423d1d2d695` |
| `docker/caddy/Caddyfile.wepp1` | `61c0f816be66c69e0e46a6ad32a3828f0f93601f` |

## Compatibility matrix

| Check | Compose smoke | Future Kubernetes canary | Result/need |
| --- | --- | --- | --- |
| Common image starts as UID 1000/GID 993 | Exact GHCR digest | Same GHCR image by digest | Compose pass after ephemeral mount ownership fix. |
| Caddy health | Loopback `/health` | Private ingress to Caddy `/health` | Compose pass. |
| Flask health through Caddy | `/weppcloud/health` | Same path | Compose pass. |
| WEPPcloud root through Caddy | `/weppcloud/` | Same path | Compose HTTP 200. |
| Static asset | Compatibility fixture | Reviewed packaged/static mount | Compose pass; Kubernetes mount/image strategy remains to render. |
| Redis | Passworded, internal, ephemeral | Passworded ClusterIP, `emptyDir`, isolated | Compose pass. |
| `/wc1` | Ephemeral writable `tmpfs` | Canary-owned disposable storage | Compose write pass; live storage not authorized here. |
| `/geodata` | Ephemeral mode-0550 `tmpfs` | Representative read-only NFS | Compose write denial pass; live NFS not authorized here. |
| PostgreSQL | SQLite startup surrogate | Reviewed external PostgreSQL | Live prerequisite unresolved by design. |
| Discord fixed path | `/dev/null` | Empty file or upstream import fix | No credential required; startup coupling documented. |
| RQ/Docker socket | Absent | Absent | Negative check pass. |
| Public exposure | Loopback-only host bind | Private-only ingress later | Compose contract pass; no live route created. |
