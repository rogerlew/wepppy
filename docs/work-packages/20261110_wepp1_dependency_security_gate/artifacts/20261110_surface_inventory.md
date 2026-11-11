# Surface inventory - wepp1 dependency security gate

**Status**: Initial source inventory; update with image evidence  
**Date**: 2026-11-11 UTC

| Surface | Source/build path | Runtime relationship | F6 disposition |
| --- | --- | --- | --- |
| Common Python environment | `docker/requirements-uv.txt` -> `/opt/venv` in `docker/Dockerfile` | Shared by web, browse, download, D-Tale, query/RQ and workers using `wepppy:latest` | Included; exact-image SBOM/scan and direct inventory |
| Common Debian environment | `python:3.12-slim` plus apt installs in `docker/Dockerfile` | Shared native/runtime libraries and tools | Included; OS scan and direct `dpkg-query` reconciliation |
| Primary frontend | `static-src/package-lock.json` -> static-builder output | Built JavaScript/CSS served to browsers; Node modules not copied wholesale | Included; exact-lock audit, clean build, lint and full tests |
| Base images | `STATIC_BUILDER_IMAGE`, `RUNTIME_BASE_IMAGE` | Supply the build and runtime roots | Included; immutable/recorded references and digest-bound results |
| Vendored Git repositories | Rosetta, WEPPcloud2, WBT, WEPPpyo3 build args | Copied into common image outside Python package metadata | Included in provenance/inventory; scanner coverage explicit |
| Git-sourced Brotli | `docker/requirements-uv.txt` | Installed into `/opt/venv` without an ordinary exact version pin | Included; resolve source commit and scanner identity |
| DuckDB spatial extension | Dockerfile install step | Downloaded executable extension loaded at runtime | Included in provenance/coverage assessment |
| Quarto and Docker CLI | Dockerfile download/install steps | Report execution and worker-side Docker client | Included in provenance and OS/binary coverage assessment |
| FCGI wrapper image | `docker/Dockerfile.fcgiwrap` based on common image | Inherits common dependencies, adds two Debian packages | Common inheritance covered; added layer inventoried separately |
| Test image | `docker/Dockerfile.test` | Supplies dependency environment for canonical full pytest | Included; must derive from reviewed candidate image |
| CAP image | `services/cap/Dockerfile` | Distinct Node service/image | Named exclusion; separate package if findings arise |
| Status/preflight images | Go service Dockerfiles | Distinct Go binaries/images | Named exclusion; separate package |
| WEPPcloudR image | `weppcloudR/Dockerfile` | Distinct R runtime/image | Named exclusion; separate package |
| Caddy/Redis/PostgreSQL | Upstream images in Compose | Distinct infrastructure images | Named exclusion; separate image-governance package |

## Initial Evidence Gaps

- No raw report supports the audit's 168-record summary.
- No SBOM/scanner tool or policy is integrated in the repository.
- No exact running/candidate wepp1 image was scanned during the audit.
- The full-baseline workflow does not trigger for the production requirements
  manifest and its test Dockerfile is pinned to an existing image digest.
- Default local production builds use Dockerfile tag/branch defaults unless
  overridden; resolved base and vendored identities must be captured.
- Python/OS scanners may not recognize vendored repositories, DuckDB extensions,
  downloaded binaries, or emitted browser bundles without supplemental evidence.

## Completion Rule

Update every included row with an exact artifact identity, tool coverage,
finding count, disposition artifact, and validation receipt. Do not describe a
named exclusion as scanned or verified. Any newly discovered shared common-image
surface enters this matrix before package closure.
