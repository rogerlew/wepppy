# Owned native dependency repairs

The common-image build performs two bounded repairs before resolving Python
requirements. These are build steps, not deployment or incident recovery steps.
Use the existing Compose build/deploy entry points. No deployment-resume bypass
is enabled. Stale NFS handles still require manual intervention without waiting.

## MariaDB client

`docker/native_security/rebuild_mariadb_client.py` uses the hash-pinned Debian
MariaDB 11.8.6 source and applies the three Big5 unsigned-byte corrections from
upstream Connector/C commit `1f168de4e09838ffe14da061142ed387541aa25d`.
Both source-file hashes are checked. Review of the matching Debian patch series
(`84da78759f1de6452e19cbc24eaa3855ed352fc9306eb12fa9c8f30832d1613b`)
found no patches to the client runtime subtree. The Debian parent build's large
file define, charset, TLS, external zlib, socket and disabled dynamic-column
settings are preserved in the bounded client build.

The original three client packages are downloaded through authenticated APT
metadata at their exact installed version. Only the shared and static client
libraries change. Existing headers, plugins, compatibility links, service
archive, modes and ownership remain in the original package trees. All three
packages receive the `+wepp1` revision; only their exact dependency links follow
that revision. Checksums and installed sizes are regenerated. The build rejects
import/export ABI, SONAME or shared dependency changes. This qualification is
for amd64; other architectures and newer Debian package versions fail explicitly
until requalified.

Package-owned provenance lives at
`/usr/share/wepppy/dependency-provenance/mariadb-big5-backport.json`.
The path survives the slim base image's documentation exclusions. An absent
provenance file is not accepted merely because installation succeeded.

Acceptance requires the original Big5 regression and boundary controls through
both installed libraries, consistent package dependencies, unchanged plugin
loading, and a real GDAL/Fiona artifact roundtrip. The original libraries fail
the same Big5 inputs. Full server rebuilding is unnecessary for this demonstrated
client defect.

## Pillow and bundled Brotli

`docker/native_security/build_pillow_wheel.py` pins the official Pillow 13.0.0
wheel and Brotli 1.2.1 source by SHA-256. The official wheel alone is insufficient:
its bundled decoder still contains the demonstrated unfixed Brotli code. The
helper builds only the decoder/common pair and verifies their exported ABI,
loader dependencies, private aliases, GLIBC requirements and baseline x86 ISA.
The other 24 ELF members remain byte-identical to the official wheel. Existing
codec/font features must be preserved.

The resulting distribution is `pillow==13.0.0+wepp1`. `PIL.__version__` and the
native core remain `13.0.0`, as required by Pillow's equality check. Private
library names ending in `.1.2.0` remain compatibility aliases; actual source is
1.2.1 and exact output hashes are recorded in the installed dist-info
`wepppy-native-repair.json`. The original CycloneDX files describe upstream
inputs and are not complete SBOMs for the repaired output.

Docker installs the exact locally built wheel before resolving the pinned
requirements. It does not cache the vulnerable input wheel, and removes build
staging. Never replace the local pin with upstream 13.0.0 to make resolution
succeed. For a local Python environment, build the wheel with the helper, install
that local wheel, then resolve `docker/requirements-uv.txt`; do not run the
MariaDB package installer on the host as part of virtualenv setup.

Acceptance covers actual mapped decoder/common hashes, WOFF2 rendering without
silent layout fallback, native codec/ICC/multiframe outputs, bounded upstream
malformed-input regressions and the real PATH report. RAQM is absent from the
qualified baseline; requesting it and receiving BASIC fallback is not RAQM
coverage. A valid WOFF2 render is consumer evidence, not an exact malformed-stream
CVE reproduction.

## Updating or retiring these repairs

Retain input hashes, build receipts, original negative controls, package/wheel
readback and independent review for each candidate. Run
`wctl run-pytest tests/test_mariadb_charset.py tests/test_pillow_consumers.py`
against the exact new image before the complete required Python/frontend gates.
Fresh inventory and scans must cover installed and cached copies. Version names
or passing focused tests alone do not clear advisory findings.

When upstream packages include the same fixes, prove the original negative
controls pass with those actual artifacts, preserve consumer and ABI behavior,
and remove the corresponding helper, local pin and Docker wiring together.
The F6 work package retains trial receipts; this document owns the ongoing build
and maintenance contract.
