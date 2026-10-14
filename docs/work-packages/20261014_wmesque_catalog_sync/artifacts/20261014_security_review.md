# Security Review — WMesque Catalog Synchronization

Status: implementation review approved; rollout remains separately gated.
Reviewer: independent security_reviewer agent (`contract_security`).
Date: 2026-10-14 UTC. Scope: publisher/sync paths, client artifact validation,
RQ admission, SSH options, and server metadata. Contract checkpoint: `193df8b8c`.

## Findings and Disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| SEC-I01 | High | VRT dependency detection by suffix allowed disguised nested VRT content to bypass containment | Resolved: content-based VRT detection at publication and verification; direct regression |
| SEC-I02 | High | Downloaded VRT content could be opened as a TIFF | Resolved: OpenEx restricts driver to requested GTiff/AAIGrid/PNG; direct regression |
| SEC-I03 | Medium | Catalog symlinks could be followed or treated as missing | Resolved: contained nonsymlink descriptor check; existing and dangling cases covered |

Independent post-fix review ran seven relevant regression tests with no skips and
approved closure of all three findings. No open medium/high findings in reviewed
scope. Shared catalog locking, transactional admission, SSH host verification,
and disabled scheduling were reviewed without further findings.

## Boundary Evidence and Residual Risk

Tests cover valid nested/sibling VRTs alongside rejected external references,
real GDAL pixels, malformed catalogs, symlinks, rollback after local write failure,
and slow response headers. Forest acceptance exercises actual batch job identity,
shared files, corrupt-copy failure/recovery, and process death during staged copy.
Credentials remain outside repository artifacts. Sources are administrator-selected,
not browser inputs. No public bulk-transfer API or permission expansion was added.

Future master SSH export, source-family sidecars, tailnet task reachability, and
Kubernetes writer placement require rollout evidence. Existing public legacy
retrieval is preserved; this review does not claim general WMesque hardening.
Model/run provenance remains in ordinary raster .meta and existing EDDE records;
no new hidden-only run record is introduced.

## Sign-off

Independent reviewer: approved current fixes on 2026-10-14 UTC.
Independent packaging follow-up approved the Dockerfile-only addition of
`openssh-client`: no daemon startup, credentials, mounts, permissions, or runtime
identity changes. New image execution is recorded separately in forest acceptance.
Package owner rollout approval: not requested; M6–M8 remain outside execution.
