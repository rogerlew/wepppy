# OpenFileGDB feasibility and coupling inventory

## Confirmed host evidence

Checks ran on 2026-08-21 from `/home/workdir/wepppy`. Host identity was
confirmed before read-only inspection. The functional smoke used an isolated
temporary directory inside each batch-worker container and automatically
removed it.

| Host | Runtime container | GDAL | Driver report | Functional result |
| --- | --- | --- | --- | --- |
| `wepp1` | `docker-rq-worker-batch-1` | 3.10.3 | `OpenFileGDB ... (rw+v)` | Two layers created and reopened in update mode |
| `forest` | `wepppy-rq-worker-batch` | 3.10.3 | `OpenFileGDB ... (rw+v)` | Two layers created and reopened in update mode |

Both existing `wepppy-f-esri` containers run GDAL 3.0.0. They report
OpenFileGDB read-only and the SDK-backed FileGDB driver read/write.

The direct smoke preserved layer names, one feature per layer, text values,
geometry, and numeric values. It emitted the expected warnings that Integer64
fields become Float64 under the default broad ArcGIS compatibility mode.

## Why the driver name must change

The current helper runs:

    ogr2ogr -f FileGDB <output.gdb> <source.gpkg>

GDAL 3.10 still resolves `FileGDB` to the Esri SDK-backed driver. The direct
replacement must run:

    ogr2ogr -f OpenFileGDB <output.gdb> <source.gpkg>

GDAL 3.11 delegates FileGDB creation to OpenFileGDB, but this package must not
depend on that future-version behavior.

## Runtime call sites

- `wepppy/nodb/mods/features_export/exporters/geodatabase.py` imports
  `wepppy.f_esri`, checks container availability, and invokes conversion.
- `wepppy/nodb/mods/features_export/service.py` directly checks and invokes
  `wepppy.f_esri` for post-WEPP geodatabase co-creation.
- `wepppy/f_esri/__init__.py` owns Docker discovery/exec, timeout, conversion,
  permissions, ZIP creation, and error translation.
- `f_esri.py` reexports that compatibility surface.
- `wepppy/all_your_base/geo/geo.py` and its two stub files expose older helper
  names that have no known in-repository caller outside compatibility tests.

The persisted/request alias `f_esri` in
`wepppy/nodb/mods/features_export/contracts.py` is intentionally retained.
UI normalization and planner tests for that alias are not runtime coupling.

## Infrastructure and build coupling

- `docker/Dockerfile.f-esri` downloads and builds the Esri SDK stack.
- Dev, HPC, base production, wepp1, and worker Compose files define or depend
  on `f-esri`.
- Common dev/production Dockerfiles install an `f_esri.pth` vendor path.
- `.github/workflows/publish-weppcloud-image.yml` pins `F_ESRI_REF`; its
  Docker contract test asserts that input.
- `scripts/setup_host_venv.sh` installs the vendor path.
- `services/cao/scripts/weppcloud_deploy.sh` clones the external repository.
- Docker/configuration/bare-metal/operator documentation describes the
  service or environment variables.

## Test coupling

- Exporter and service tests mock the f-esri capability/conversion boundary.
- `tests/test_f_esri_timeout.py` and `tests/test_f_esri_permissions.py` cover
  the container helper and should be replaced by direct conversion tests.
- `tests/test_0_imports.py` treats the compatibility import as optional.
- Planner/UI tests for the legacy `f_esri` format alias should remain.

## Accepted caveats and overlooked-risk checklist

- OpenFileGDB output is not expected to be byte-identical to SDK FileGDB.
- Default Integer64-to-Float64 conversion is accepted; exactness still needs
  representative-value verification.
- An `ogrinfo` capability line is insufficient; use create, readback, archive,
  and external-client evidence.
- Preserve timeout behavior by using a bounded direct subprocess unless a
  comparably cancelable GDAL API boundary is proven.
- The old helper repairs group read/write and directory traversal bits after
  conversion. Direct writes must be tested under real worker UID/GID and umask.
- The ZIP layout must work for normal extraction and external clients, not
  merely pass the current filename-based cache validator.
- Empty layers, geometryless tables, null fields, field-name laundering,
  dates/times, CRS/precision grids, mixed geometry dimensions, and long strings
  need characterization.
- Conversion failures must not leave a cache-valid partial archive or stale
  `.gdb` directory.
- Existing cached/downloaded artifacts remain valid and should not be
  regenerated solely because the backend changed.
- Removal must cover worker-only and HPC Compose variants, build cache inputs,
  host venv paths, and deployment clones—not only the main Compose service.
- Docker-socket mounts may have other consumers. Remove the mount only where a
  complete per-service inventory proves f-esri was the last requirement.
