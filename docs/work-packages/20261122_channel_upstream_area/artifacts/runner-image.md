# Runner image promotion

The operator approved the protected WBT publication-pin change on 2026-11-23 UTC. PR 730 and master both used commit `5c8f767c8ad06861cf6cc5e49763fbafb6f0285e`, policy digest `f6e7a961bdf1b1486ec772deb405bd64f1873e6ee05daa1d25907d2e3bd6d0be`. Required PR checks and the exact master publication check passed. [Master integration receipt](wbt-image-pin-master.json)

The [common-image build](https://github.com/rogerlew/wepppy/actions/runs/45113341283) published `ghcr.io/rogerlew/wepppy@sha256:a3ab4594f2c45dd05e22fd31d4ca29ccfec6fc66faed54d9a6930b35a17acc4c`. On runner-02, pulled by digest, read the expected source revision label, and executed the baked native components with networking disabled. The installed WEPPpyo3 preflight passed with extension SHA-256 `9c16555afa70595c3a4031eb8bab94a1cdc6a7ea23637f40aff6120ab83520f9`. The WhiteboxTools dispatcher matched `fad79e67c4307eb76b3661245afe23de05b12adcc8546c7216868ac7660db94c`. Running HillslopesTopaz on the twelve-cell watershed produced 10,000, 70,000 and 20,000 m² for TOPAZ 34, 24 and 44 respectively.

The default in docker/Dockerfile.test selects this immutable common image for new CI builds.
