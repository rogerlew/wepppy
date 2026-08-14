# Build and prove the WEPPcloud private-canary image contract

This ExecPlan is a living document maintained under `docs/prompt_templates/codex_exec_plans.md`. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must remain current.

## Purpose / Big Picture

After this work, reviewers can publish the repository's existing common WEPPpy runtime image to private GitHub Container Registry (GHCR) with a source-commit tag, retrieve its immutable content digest, and exercise the same image with the smallest useful local web stack. The proof is deliberately non-live: it starts no existing production/test-production stack and changes no protected production Compose default.

## Progress

- [x] (2026-08-13 19:36 UTC) Read governance, paired-package authority, and relevant Docker/workflow sources.
- [x] (2026-08-13 19:36 UTC) Create branch and paired WEPPpy work-package scaffold from source `2dedf916cb5ba430454dccc437ff0eb8fcb11daa`.
- [x] (2026-08-13 20:02 UTC) Complete and record the service/port/mount/secret/health/Caddy/socket inventory.
- [x] (2026-08-13 20:02 UTC) Implement the full-SHA-pinned GHCR workflow with minimum token permissions, a commit-derived tag, digest reporting, and immutable build inputs.
- [x] (2026-08-13 20:02 UTC) Implement additive Compose/Caddy smoke configuration and focused assertions.
- [x] (2026-08-13 20:02 UTC) Build and exercise the image on `dev-01`; capture and resolve two smoke-only startup/network issues.
- [x] (2026-08-13 20:02 UTC) Run focused checks, protected-file comparison, preliminary security review, and secret-sensitive diff review.
- [x] (2026-08-13 20:20 UTC) Commit/push, observe successful publication, pull and smoke the exact digest, and finalize security evidence.
- [x] (2026-08-13 20:25 UTC) Open ready-for-review PR https://github.com/rogerlew/wepppy/pull/611 and record its URL.

## Surprises & Discoveries

- Observation: The production base Compose file combines the common image with many services and secrets, while host overrides also add Docker-socket-mounted workers.
  Evidence: `docker/docker-compose.prod.yml` declares the common `x-wepppy-image`; `docker/docker-compose.prod.wepp1.yml` and `docker/docker-compose.prod.worker.yml` mount `/var/run/docker.sock` for RQ workers.

- Observation: The Docker build context was about 2.66 GB and the unpacked local image was 2,663,253,220 bytes.
  Evidence: Docker build transferred 2.66 GB and `docker image inspect` returned the exact unpacked size. This is a performance/CI-duration risk, not a reason to weaken the build.

- Observation: Web startup imports a vendored Discord module that unconditionally opens a fixed token file even when notifications are disabled.
  Evidence: The first Gunicorn worker exited at `weppcloud2/discord_bot/discord_client.py`; mounting `/dev/null` at that exact path allowed the web-only app to start without a credential.

- Observation: Docker did not activate a loopback port publish while Caddy was attached only to an `internal: true` network.
  Evidence: Caddy was healthy and its HostConfig listed port 18080, but NetworkSettings had no published port and host curl failed. Attaching only Caddy to a second edge network made `127.0.0.1:18080` reachable while Redis/web remained internal.

- Observation: Dockerfile build arguments used by multiple `FROM` instructions must be declared before the first `FROM` to remain globally available.
  Evidence: GitHub run `31739044295` failed with `base name (${RUNTIME_BASE_IMAGE}) should not be blank`. Moving both image arguments above the first stage fixed their BuildKit scope; run `31739217249` then succeeded.

- Observation: GitHub's package metadata API requires a `read:packages` user-token scope that the local token does not carry, but registry authentication and artifact pull use the workflow-created package authorization successfully.
  Evidence: the metadata API returned 403, authenticated digest pull succeeded, and an anonymous manifest request returned 401. No repository or package setting was changed.

## Decision Log

- Decision: Implement a standalone compatibility Compose file instead of an override layered onto production Compose.
  Rationale: A standalone additive file can render and run without resolving production secrets, mounts, or auxiliary services and cannot change production defaults by merge behavior.
  Date/Author: 2026-08-13 / Codex

- Decision: Treat the compatibility target as a focused scaffold/surrogate for the later private canary, not full production service parity.
  Rationale: This phase intentionally excludes PostgreSQL live credentials, NFS administration, workers, external services, and public routing. Acceptance proves image startup and minimum routing only; it does not claim production cutover readiness.
  Date/Author: 2026-08-13 / Codex

- Decision: Expose default-preserving Dockerfile build arguments and pin them only in the GHCR workflow.
  Rationale: This retains every production Compose default while allowing the published artifact to use base digests, a versioned uv installer, and exact sibling Git commits. Debian repositories and the DuckDB extension remain non-hermetic and are reported explicitly.
  Date/Author: 2026-08-13 / Codex

## Outcomes & Retrospective

Implementation and artifact acceptance are complete. GitHub run `31739217249` published source `ed1b538df02a8db0d709257ea9dacc330c56b9d9` as `ghcr.io/rogerlew/wepppy:sha-ed1b538df02a8db0d709257ea9dacc330c56b9d9` with digest `sha256:ee92666229df8fdffe4b06b1dff2cfd0e9e06823ada59915c8b492d8a468eb51`. The exact digest passed the three-service runtime contract and the security gate. PR https://github.com/rogerlew/wepppy/pull/611 is ready for review.

## Context and Orientation

`docker/Dockerfile` builds the common runtime used by the production Compose services. `docker/docker-compose.prod.yml` supplies the base stack; `docker/docker-compose.prod.wepp1.yml`, `docker/docker-compose.prod.wepp3.yml`, and `docker/docker-compose.prod.worker.yml` specialize host and worker behavior. These production files are protected inputs during this package.

The minimum compatibility stack has three services. Caddy is the HTTP reverse proxy and static-file server. WEPPcloud is the Flask application served by Gunicorn on container port 8000. Redis is an in-memory key/value service used for Flask sessions; its smoke instance is ephemeral and isolated. The stack must contain no RQ worker and no Docker socket. Synthetic test-only secret values may be injected solely into the ephemeral local stack; production secret files must never be opened, copied, or generated.

The image workflow lives as a manually triggerable and branch-capable workflow under `.github/workflows/`. It checks out the exact source commit, authenticates to `ghcr.io` with `github.actor` and `GITHUB_TOKEN`, builds `docker/Dockerfile` from repository context, tags the image using the full Git commit SHA, pushes it, and emits the digest. Workflow-level permissions are only `contents: read` and `packages: write`; every `uses:` reference is a 40-hex-character commit SHA.

## Plan of Work

First, record an inventory artifact that distinguishes the broad production contract from the web-only compatibility contract. Include services, internal and host ports, mounts, secret IDs (never values), health paths, Caddy routes, Docker sockets, image build arguments, and unresolved startup needs.

Second, add the GHCR workflow. Use the existing repository root as build context and `docker/Dockerfile`; preserve its current default build arguments unless the compatibility matrix requires explicit existing values. Compute the image name in lowercase because GHCR names require lowercase. Use a tag formed only from the immutable full source commit, and expose the pushed digest through the job summary and job output.

Third, add an independent smoke Compose file and minimum Caddyfile. The smoke stack builds or accepts the common image, uses only container-internal ports by default except a loopback-bound Caddy test port, uses disposable named volumes or temporary bind paths, and creates no Docker socket mount. Add a focused test script or pytest module that renders the model and asserts the forbidden surfaces remain absent. Exercise Caddy health, WEPPcloud health through the `/weppcloud/` proxy boundary, a static asset, and Redis isolation where startup permits.

Finally, run focused repository checks and compare protected production files against the baseline commit with both Git diff and hashes. Review the complete patch for likely credentials, unpinned Actions, mutable workload tags, public binds, worker services, and socket mounts. Update the tracker, ExecPlan, inventory, and security review with exact evidence before committing and opening the PR.

## Concrete Steps

Work from `/home/roger/src/wepppy`.

Inspect and render without production secrets:

    docker compose -f docker/docker-compose.canary-smoke.yml config
    <focused static test command selected during implementation>

Build and smoke only the additive project, using an explicit project name that cannot collide with production:

    docker compose --project-name weppcloud-canary-smoke -f docker/docker-compose.canary-smoke.yml build weppcloud
    docker compose --project-name weppcloud-canary-smoke -f docker/docker-compose.canary-smoke.yml up --detach --wait
    <HTTP checks>
    docker compose --project-name weppcloud-canary-smoke -f docker/docker-compose.canary-smoke.yml down --volumes

Validate protected files and the patch:

    git diff --exit-code 2dedf916cb5ba430454dccc437ff0eb8fcb11daa -- docker/docker-compose.prod.yml docker/docker-compose.prod.wepp1.yml docker/docker-compose.prod.wepp3.yml docker/docker-compose.prod.worker.yml
    git diff --check
    wctl doc-lint --path docs/work-packages/20260813_weppcloud_private_canary_image

Observed local results: build passed with local manifest digest `sha256:f70d212bd5d75ade2d183f807899bd00bf7f6c89b65029ae196dc53a1e626296`; the final HTTP checks returned `OK`, JSON string `"OK"`, the static compatibility text, and HTTP 200 for `/weppcloud/`. `/wc1` accepted a write, `/geodata` rejected one, and neither Redis nor WEPPcloud published a host port. The explicit project teardown removed its containers and networks; two stale volumes created by the first pre-`tmpfs` revision were removed by exact name.

Published-artifact results: run `31739217249` succeeded in 7m22s. An authenticated pull of `ghcr.io/rogerlew/wepppy@sha256:ee92666229df8fdffe4b06b1dff2cfd0e9e06823ada59915c8b492d8a468eb51` succeeded; the exact image then passed the same HTTP, storage, socket, port, and cleanup checks. Anonymous manifest access returned 401.

## Validation and Acceptance

The Compose file must render without accessing `docker/secrets/`. Static assertions must show exactly Caddy, WEPPcloud, and Redis; no worker, Docker socket, host filesystem production mounts, external data credential, OAuth, SMTP, CAPTCHA, or public route may appear. Caddy `/health` and `/weppcloud/health` must return HTTP 200, `/weppcloud/` must traverse to the Flask application, and at least one packaged static asset must be served. Redis must be ephemeral and reachable only on the private Compose network.

The workflow must parse as YAML, declare only the two required token permissions, contain no repository secret reference or personal token, pin all Actions by full SHA, build the existing common Dockerfile, use a full-SHA-derived image tag, push only from an authorized event, and report the immutable digest. A successful GitHub run and digest readback are required for full closeout; if publication is unavailable or fails, the package stays open and records the exact external blocker.

All protected production Compose files must have an empty diff against source `2dedf916cb5ba430454dccc437ff0eb8fcb11daa`. Relevant focused tests and documentation lint must pass. The security artifact must contain no unresolved medium or high finding before the PR is declared ready for review.

## Idempotence and Recovery

The smoke stack uses the explicit project name `weppcloud-canary-smoke`; repeated render/build/up/down operations address only that isolated project. Always use `down --volumes` after runtime checks. If startup fails, capture `docker compose ... ps` and `docker compose ... logs --no-color`, then tear down only that explicit project. Never invoke `up`, `restart`, `down`, or `rm` against a production Compose file or an unspecified project.

Workflow retries republish the same commit-derived manifest content under the same immutable source tag only when the build inputs are unchanged; reviewers consume the recorded digest, never the tag alone. Reverting the additive files removes this capability without affecting existing deployment files.

## Artifacts and Notes

Baseline source SHA:

    2dedf916cb5ba430454dccc437ff0eb8fcb11daa

Protected production Compose files:

    docker/docker-compose.prod.yml
    docker/docker-compose.prod.wepp1.yml
    docker/docker-compose.prod.wepp3.yml
    docker/docker-compose.prod.worker.yml

## Interfaces and Dependencies

Use Docker Compose v2 already installed on `dev-01`, Caddy's existing `caddy:2-alpine` family pinned to an immutable digest in the smoke workload, the current common `docker/Dockerfile`, and GitHub-hosted Actions pinned by commit. Do not add a language/runtime dependency. The future Kubernetes phase consumes the resulting common image strictly by `ghcr.io/<owner>/<image>@sha256:<digest>` and separately supplies reviewed runtime secrets and storage.

Revision note (2026-08-13 19:36 UTC): Initial self-contained plan created from the dispatch, repository governance, and paired private-canary package.

Revision note (2026-08-13 20:02 UTC): Recorded completed inventory/implementation/local validation, immutable publication inputs, observed startup/network surprises, and the remaining GitHub publication/PR milestone.

Revision note (2026-08-13 20:07 UTC): Recorded the first CI build's global Dockerfile ARG failure and its minimal scope correction; publication remains pending retry.

Revision note (2026-08-13 20:20 UTC): Recorded successful GHCR publication, exact tag/digest, authenticated pull, anonymous privacy probe, digest-pinned runtime acceptance, and final security sign-off.

Revision note (2026-08-13 20:25 UTC): Recorded ready-for-review PR #611 and completed every planned non-live milestone.
