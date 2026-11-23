# GDAL native repair qualification, 2026-11-23

**Decision. Keep CVE-2026-49014 open.** The candidate has two independent GDAL libraries that register and successfully read through the affected netCDF driver. The prior private backport contains the upstream repair. A trial with the private system library and private Rasterio wheel passed ordinary scientific reads but changed Rasterio's available formats. The supported package channels tested did not yield a compatible replacement for both libraries. The trial used read-only mounts in disposable containers running the exact common candidate image `sha256:a116e2d21457a0e33a6070ab42518be0adead13ea9b53db5c55d9f7dfa8871d0`.

## Coverage of the installed software

| Consumer | Engine and evidence |
| --- | --- |
| GDAL CLI, OSGeo Python, Fiona 1.10.1 | Debian GDAL 3.10.3, SHA-256 prefix `6dcf0cf936e0`. The runtime registers netCDF. |
| Rasterio 1.3.10 | Private GDAL 3.8.4, SHA-256 prefix `11430c2a8473`. The runtime registers netCDF. The published wheel contains the identical library. |
| Pyogrio 0.13.0 | Its GDAL 3.12.4, SHA-256 prefix `d1a3bcc47a3b`, supports the ordinary GeoJSON read. The loaded engine has no registered netCDF driver. |
| DuckDB 1.1.1 spatial | The extension with SHA-256 prefix `8654b3af846c` reads the same GeoJSON point. Its 54 advertised vector drivers omit netCDF. ELF inspection found no netCDF dependency or registration symbol. |
| OGDI 4.1 | The similarly named OGDI module depends on libogdi and libc. It delegates GDAL registration through a function pointer. |

The Debian tracker identifies the fix in GDAL 3.13.1 and still lists trixie 3.10.3+dfsg-1 as vulnerable. Direct checks of the trixie, updates, security and backports amd64 package indexes found only the original trixie GDAL packages. Installing newer Python GDAL bindings also requires a matching native library. The previous exception for an HDF advisory has a different identifier. [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2026-49014) · [upstream correction](https://github.com/OSGeo/gdal/commit/c49254dc6380af2f02ff43ca79e3cf7c1bc82f01)

## Ordinary scientific workflows

The prior source receipt at commit `967a085f4` pins all three changed netCDF sources and the backport patch. Its added source includes all upstream added lines in the three files after trimming whitespace. Additional lines were braces and whitespace from adapting to GDAL 3.10.3. The privately retained Debian package yielded the previously recorded corrected library SHA-256 prefix `67d92bc35ff7`. OSGeo, Fiona and the private Rasterio 1.3.10+wepp1 wheel each mapped that exact library in the trial.

Both the original and corrected configurations returned the four expected netCDF cells, preserved those values and their affine transform through a GeoTIFF write/read, and produced matching EPSG:3857 coordinates. Both preserved a GeoJSON point and its numeric attributes. The GDAL CLI checksum was 10 in both. Rasterio's two-thread reprojection returned all 1,048,576 expected cell values in both. These checks used ordinary generated files and the image's original PROJ setting.

| Public Rasterio wheel | Bundled GDAL | Result under the candidate's scientific configuration |
| --- | --- | --- |
| 1.4.4 | 3.10.3 | Read netCDF, then failed to write an EPSG:4326 GeoTIFF. |
| 1.5.0 | 3.12.1 | Same failure. Declares NumPy 2 or later. |
| 1.5.1 | 3.12.4 | Same failure. Declares NumPy 2 or later. |
| 1.5.2 | 3.12.2 | Same failure. Declares NumPy 2 or later. |

Each CPython 3.12 Linux x86-64 wheel matched its published PyPI digest. Each requires PROJ database layout minor version 6 or higher for this write, while the image provides 5. The candidate ships NumPy 1.26.0. The newest wheel also predates the first fixed GDAL release by native version. [Rasterio release files and requirements](https://pypi.org/project/rasterio/1.5.2/)

## Scope of the remaining choice

- **Re-use the privately corrected Debian package pair and system-linked Rasterio.** This is the smallest demonstrated two-consumer repair. It requires ownership of the native backport and the Rasterio compatibility patch. Rasterio gains 67 drivers and loses ARG, changing the total from 155 to 221. Integration requires an explicit decision on the driver change and maintenance, followed by a clean production-recipe build, full scientific regression, installed-library readback and scan. The historical source and qualification record describe the prior deferral. [Previous qualification](../../20261110_wepp1_dependency_security_gate/artifacts/20261113_gdal_qualification.md)
- **Preserve the original Rasterio driver and PROJ contract.** The official 1.3.10 CPython wheel SHA-256 begins `f9cd757e11cf`. Its 29 bundled libraries include the exact deployed GDAL. An upstream April 2024 workflow for this release selects the Rasterio release branch and builds GDAL 3.8.4, PROJ 9.3.1, netCDF and their native dependencies. Public source provides a recipe, while the exact historical runner and wheel-to-run attestation remain unverified. Keeping the original 155 drivers calls for a maintained ABI-34 repair in addition to the Debian ABI-36 backport. This requires recreating the native build inputs and verifying the bundled loader identities, driver set, coordinates and scientific data against the original wheel. [Upstream build recipe](https://github.com/rasterio/rasterio-wheels/tree/9988d31b3a863b964e29978e556d925bf3516685) · [original wheel](https://pypi.org/project/rasterio/1.3.10/#files)
- **Retain the hold pending supported fixed artifacts.** Recheck the Debian trixie channels and Rasterio's wheel when their native package contents change. A finding-specific risk decision would need independent review against the exact image and applicable exception policy.

Private reproduction inputs, original-wheel identity, source provenance, per-consumer library maps, wheel metadata, package indexes and normal-file readbacks are retained in the approved evidence store under `grype-remediation-20261123/gdal/`.
