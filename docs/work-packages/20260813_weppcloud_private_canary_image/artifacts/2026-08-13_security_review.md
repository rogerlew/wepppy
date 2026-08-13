# Security Review - WEPPcloud private-canary image compatibility

## Metadata

- **Package**: `docs/work-packages/20260813_weppcloud_private_canary_image/`
- **Reviewer**: Codex
- **Date**: 2026-08-13
- **Scope reviewed**: GHCR workflow, Dockerfile input hooks, isolated Compose/Caddy contract, tests, and package evidence
- **Commit/branch context**: working tree on `weppcloud-private-canary-image`; baseline `2dedf916cb5ba430454dccc437ff0eb8fcb11daa`
- **Related artifacts**: `artifacts/compatibility_inventory.md`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: the workflow grants package publication to `GITHUB_TOKEN`, creates an external image artifact, and defines runtime secret/network/filesystem boundaries.
- **Threat model assumptions**:
  - GitHub-hosted runners execute the checked-out repository commit; no self-hosted runner or production host is involved.
  - GHCR package settings are not changed by this package. Publication must be read back as private before the artifact is accepted.
  - Local smoke values are synthetic and ephemeral. No file under `docker/secrets/` is read.
- **Valid states that controls must preserve**: manual dispatch and master push publish the exact checked-out commit; a missing smoke input fails Compose rendering; valid synthetic inputs start only the isolated three-service stack; no live deployment state is changed.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | CI authority | Image publication must not receive repository-write, identity-token, or unrelated secret authority. | Workflow top-level permissions are exactly `contents: read` and `packages: write`; login uses only `secrets.GITHUB_TOKEN`. | Keep exact permissions and verify the run. | Resolved pending run readback |
| SEC-02 | High | Supply chain | Floating Action refs or workload tags could execute or deploy changed content. | All four Actions use verified 40-character release SHAs; Caddy/Redis use platform digests; output includes the pushed manifest digest; tests reject floating Action refs. | Verify GHCR digest and consume by digest. | Resolved pending run readback |
| SEC-03 | Medium | Build provenance | The existing Dockerfile used floating sibling Git branches and base tags. | Workflow supplies full Git SHAs, base image digests, and a versioned uv installer through default-preserving Dockerfile build args. The frontend syntax is digest-pinned. | Record pins and remaining apt/DuckDB external resolution limits. | Resolved |
| SEC-04 | High | Secrets | Full WEPPcloud imports a fixed Discord token path even when notifications are disabled. | First smoke failed at `discord_client.py`; retry succeeded with `/dev/null` mounted at the fixed path. | Never inject Discord credentials into the web-only canary; retain empty-file workaround or repair upstream import coupling later. | Resolved for smoke; follow-up documented |
| SEC-05 | High | Network/privilege | Workers, sockets, host datasets, or broad host ports would exceed authority. | Rendered model has only Caddy/WEPPcloud/Redis; Caddy binds `127.0.0.1`; Redis/web have no host ports; no Docker socket; backend network is internal. | Keep negative assertions. | Resolved |
| SEC-06 | Medium | Filesystem | Root-owned smoke volumes initially prevented security logging and could mask storage incompatibility. | Final stack uses UID/GID-scoped ephemeral `tmpfs`; `/wc1` write succeeds and `/geodata` write fails. | Future Kubernetes manifests must express equivalent ownership/read-only controls. | Resolved |
| SEC-07 | Medium | Dependency baseline | Existing frontend install reported 1 low, 1 moderate, and 3 high npm audit findings. | Local Docker build transcript at static-builder `npm ci`. | Do not weaken build; track remediation separately because this package changes no dependency. | Accepted residual risk; pre-existing |

Risk acceptance authority: the package owner must acknowledge any accepted risk. SEC-07 is existing dependency state and is not introduced or suppressed by this change.

## Verdict

- **Gate status**: fail pending GHCR workflow/digest/privacy readback
- **Unresolved findings**:
  - High: 2 evidence gates (SEC-01 and SEC-02 run readback)
  - Medium: 0 implementation findings; SEC-07 is a recorded pre-existing residual risk
  - Low: 0
- **Release recommendation**: hold final ready-for-review status until the branch workflow completes and the package is confirmed private.

## Surface Checks

### Secrets and credential handling

- [x] No production secret file was opened, copied, generated, mounted, or logged.
- [x] Workflow login uses only repository `GITHUB_TOKEN`.
- [x] Compose requires synthetic values and stores no plaintext credential value in Git.
- [x] Discord import coupling uses `/dev/null`, not a credential.

### File system and worker boundaries

- [x] `/wc1` is disposable and writable only inside the smoke container.
- [x] `/geodata` denies writes.
- [x] RQ workers, subprocess worker services, and Docker socket mounts are absent.

### Network and external integrations

- [x] Redis and WEPPcloud expose no host ports.
- [x] Caddy publishes only a loopback-bound smoke port.
- [x] No public hostname, OAuth, SMTP, CAPTCHA, external-data API, or production database is configured.
- [x] Build-only egress is limited to the existing Dockerfile dependency sources and GHCR publication.

### CI/CD and supply chain

- [x] GitHub-hosted runner selected; self-hosted runner scope unchanged.
- [x] Workflow token permissions are minimal.
- [x] Actions are pinned by full commit SHA.
- [x] Caddy and Redis smoke images are pinned by digest.
- [x] Common image uses a full source-SHA tag and reports its immutable digest.
- [ ] Successful workflow, private-package visibility, and digest readback recorded.

### Logging and rollback

- [x] Workflow summary reports source, tag, digest, Dockerfile, context, and platform without secrets.
- [x] Smoke teardown uses an explicit project name and removes only disposable resources.
- [x] Existing production Compose inputs have an empty baseline diff.

## Validation Evidence

- Local common image build: pass; local manifest digest `sha256:f70d212bd5d75ade2d183f807899bd00bf7f6c89b65029ae196dc53a1e626296`, unpacked size 2,663,253,220 bytes. This was built from the working tree and is not the GHCR acceptance digest.
- Compose render/static contract: pass; exactly `caddy`, `redis`, and `weppcloud`.
- Runtime: pass after documented empty Discord path and mount ownership corrections.
- HTTP: `/health`, `/weppcloud/health`, `/weppcloud/static/compatibility.txt`, and `/weppcloud/` pass; root returns 200.
- Negative boundaries: no worker/socket/host data; `/wc1` write pass; `/geodata` write denied; Redis/web host ports absent.
- Focused pytest: workflow check `1 passed, 1 deselected`; Compose check executed directly because host `wctl` is absent and the built runtime does not contain the Compose plugin.
- Caddy: configuration valid and formatted.
- Protected production files: empty diff from baseline; exact hashes in compatibility inventory.

## Residual Risk

- **Accepted residual risks**:
  - Existing npm audit output (1 low, 1 moderate, 3 high) is visible and unchanged. Owner acknowledgment is pending PR review.
  - Debian package indexes and the DuckDB extension download mean same-source rebuilds are not guaranteed byte-for-byte identical; the published artifact itself is immutable by digest. A deeper hermetic-build effort is follow-up scope.
- **Follow-up packages/issues**:
  - Paired live-canary package must render Kubernetes security, network, PostgreSQL, and storage controls and complete a new pre-apply review.
  - Worker/Docker-socket behavior remains a separate successor package.

## Sign-off

- **Security reviewer**: pending final workflow readback
- **Package owner**: pending PR review
