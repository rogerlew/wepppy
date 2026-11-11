# Kubernetes secret handling review for F5

**Status**: Source review complete; contract input, not implementation evidence
**Date**: 2026-11-11 UTC
**Repository reviewed**: `/home/workdir/open-wepp-org`
**Live cluster contacted**: no

## Conclusion

F5 needs no Kubernetes Secret API client, SOPS integration or new secret
transport. Flux decrypts SOPS material before workload startup, and WEPPcloud
processes receive selected plaintext values through read-only files. F5 must
read only the mounted files owned by the current process during exception
rendering.

The source contract must be process-specific rather than inferred from every
configured `*_FILE` variable. Some variables describe a path that a downstream
worker will read, and one isolated service retains an unused Redis file setting
without the corresponding mount. Environment presence alone therefore cannot
prove that a source belongs to the current process.

## Kubernetes Trust Boundary

- SOPS ciphertext and the `flux-system/sops-age` identity remain outside the
  application boundary. F5 must never decrypt SOPS, query Kubernetes Secret
  objects or request permission to read Secrets.
- Application secrets are mounted under `/run/secrets/weppcloud`,
  `/run/secrets/weppcloudr-client` and `/run/secrets/weppcloudr`. The WEPPcloudR
  control plane additionally receives its Kubernetes service-account token at
  the standard projected token path.
- Secret volumes use read-only `0444` files so the existing non-root application
  identities can read them. F5 does not need a permission or ownership change.
- The ordinary `weppcloud` service account has no Secret-reading RBAC. The
  WEPPcloudR control-plane role can manage Jobs and read Pods/Pod logs but cannot
  read Kubernetes Secret objects. Preserve those restrictions.
- Kubernetes container stdout/stderr is a retained diagnostic sink. Uncaught
  interpreter output and early framework logging must be inventoried alongside
  configured Python logging handlers.

## Process-Owned Source Profiles

This table is the M0 input, not a final inventory. `Local sources` are eligible
for an exceptional-path snapshot in that process. `Excluded/pass-through`
settings must not be opened by that process.

| Process profile | Local sources and format | Excluded/pass-through evidence |
| --- | --- | --- |
| WEPPcloud web | Flask key, Flask security salt, agent JWT key, authorization JWT key ring, PostgreSQL password, Redis password and CAP secret | `WEPPCLOUDR_K8S_IDENTITY_TOKEN_FILE` names a downstream worker path but is not mounted in the web pod |
| rq-engine | Redis and PostgreSQL passwords, Flask key and salt, authorization JWT key ring and CAP secret | No directory enumeration; only declared local settings |
| Browse | Redis password, authorization JWT key ring and D-Tale internal token | Other keys in the shared Secret object are not sources |
| Download | Redis password and authorization JWT key ring | Other keys in the shared Secret object are not sources |
| Query engine | Redis password and MCP JWT key | Authorization/CAP/D-Tale keys are not mounted for this process |
| D-Tale | Redis password and D-Tale internal token | Other authentication keys are not sources |
| Elevation, metquery, wmesque and wmesque2 | Redis password | No generic mount scanning |
| RQ default and declarative worker | Redis and PostgreSQL passwords, Flask key and salt | No authentication-key sources in these pods |
| RQ batch worker | RQ-default sources plus the WEPPcloudR control-plane client token | The CA bundle is public trust material, not a secret |
| RQ fork/archive worker | Redis password | No database or Flask sources are mounted |
| Scheduler | Redis and PostgreSQL passwords | No Flask/authentication sources are mounted |
| WEPPcloudR control plane | Redis password, control-plane bearer token, TLS private key and Kubernetes service-account token | TLS certificate, Kubernetes CA and namespace files are not secrets |
| Shape converter | None | `REDIS_PASSWORD_FILE` is declared but the isolated pod has no secret mount or Redis egress; it is not a local F5 source |

Status2 and preflight2 are Go processes, and CAP is a Node process. They also
receive selected secret files, but they do not use the Python traceback module
and are not added to F5 merely because they share the deployment. Their existing
static error/log redaction remains authoritative; the Redis transport and F4
packages own the confirmed Go credential/authentication changes.

The authorization JWT key-ring file is a comma-delimited compound value.
Snapshot construction must include each non-empty constituent key, not only the
complete file text. PEM private-key handling must redact the complete value and
bounded secret-bearing body forms; the public certificate is excluded.

## Required F5 Changes

1. Define immutable source-profile metadata containing setting names, file/env
   precedence, required/optional state and a bounded decoder. This metadata is
   not a registry of secret values. Values remain local to one render call.
2. Select a source profile at each application/worker/logging adapter. Do not
   infer ownership from arbitrary environment variables or mount contents.
3. Treat a configured-but-unreadable source as fail-closed only when that source
   belongs to the selected process profile. Missing pass-through or unrelated
   paths must not degrade traceback observability.
4. Add a comma-list decoder for the authorization JWT key ring and explicit
   handling for the WEPPcloudR bearer token, TLS private key and control-plane
   service-account token.
5. Add container stdout/stderr, uncaught interpreter output and the WEPPcloudR
   control-plane reconciliation logger to the sink inventory.
6. Validate with synthetic files at production-equivalent paths, modes and
   non-root identities. Prove a subsequent exception observes a replaced file,
   while successful paths perform no reads.

## Validation Boundary

Do not decrypt or copy real SOPS values for testing. Generate unique synthetic
canaries in temporary mounts and inspect final API, file, Redis and container-log
outputs. A local production-equivalent container test belongs to F5 acceptance.
An eventual openwepp Kubernetes rollout and live `kubectl logs` canary require a
separately authorized deployment package; F5 scaffolding does not authorize it.

The repository secret-policy check completed successfully:

    scripts/check-secrets.sh
    secret policy check: PASS

`kubectl`, `kustomize`, Flux and SOPS clients were unavailable in the review
environment, so no rendered-manifest, decryption or live-cluster claim is made.

## Reviewed Evidence

- `clusters/openwepp/apps/weppcloud/web.yaml`
- `clusters/openwepp/apps/weppcloud/request-plane.yaml`
- `clusters/openwepp/apps/weppcloud/rq-worker.yaml`
- `clusters/openwepp/apps/weppcloud/scheduler.yaml`
- `clusters/openwepp/apps/weppcloud/weppcloudr-control-plane.yaml`
- `clusters/openwepp/apps/weppcloud/secrets/*.sops.yaml` metadata and key names
- `docs/operations/sops-age-secret-management.md`
- `docs/decisions/0005-gitops-secret-management.md`
- `wepppy/config/secrets.py`
- `wepppy/weppcloud/utils/auth_tokens.py`

No file in `open-wepp-org` was changed during this review.
