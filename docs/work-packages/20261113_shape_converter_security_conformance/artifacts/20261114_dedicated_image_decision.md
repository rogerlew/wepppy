# Dedicated shape-converter image decision

## Decision

Use a dedicated image for the existing `shape-converter` Compose service. Base
it on the official GDAL 3.12.4 Ubuntu-small image pinned as
`ghcr.io/osgeo/gdal:ubuntu-small-3.12.4@sha256:9acfdf967ece13a9a1d9622a494d726aad6b9759aeaae40bbd4d8cb74c843971`,
retain Python 3.12, and source-build Fiona 1.10.1 against the base image's
`gdal-config`. Do not change the common WEPPpy image or the public service/API
topology.

This decision implements the image split already required by the canonical
shape-converter container specification. It does not add a library or replace an
owned WEPPpy performance component, so the new-dependency adoption workflow is
not applicable. Qualification still covers the changed native dependency stack.

## Rationale

The existing shared image contains the whole application, unrelated native and
Python packages, application secrets, datastore configuration, and host data
mount assumptions. The shape converter needs only its ASGI layer, Fiona/GDAL,
PyProj, Shapely, PyArrow, UTM helpers, and safe observability utilities.

GDAL 3.12.4 is the bounded candidate because its official Ubuntu-small image is
based on Ubuntu 24.04 with Python 3.12, matching the current service Python major
version. GDAL 3.13 would also change the operating-system and Python baselines,
expanding compatibility risk without evidence that this service needs that
larger jump. Fiona is built from source so its native extension links to the
selected image GDAL instead of a wheel-bundled copy.

## Security effect and limits

The dedicated image reduces the package and secret blast radius and prevents the
service from inheriting Redis/Postgres dependencies, `/wc1` and `/geodata`
mounts, and unrelated environment configuration. Existing non-root, read-only,
capability, resource, tmpfs, and internal-network controls remain required.

This is defense in depth. A compromised Fiona/GDAL parser still shares the
service container's user and namespaces with its parent, so the image split does
not satisfy the contract's effective second-sandbox requirement. Issue #656 and
the production release gate remain open.

## Qualification gate

Before rollout, use a Dockerfile-specific allowlist build context and a
hash-locked resolved Python dependency set, including compatibility-critical
transitives such as NumPy. Retain the exact base reference, resolved package
inventory, and built image ID; prove the GDAL and Fiona-linked GDAL versions;
inspect native linkage; run real-worker GeoJSON and GeoParquet artifact readback
plus hostile IPC tests; and verify the resolved Compose, final image files,
history/config, and running container contain no inherited secrets, mounts, or
configuration. Every reachable Medium, High, or Critical scan finding requires
remediation or explicit operator risk acceptance.

Health checks may prove that the image starts and its toolchain is usable, but a
`200` response caused only by matching `container/container` mode strings is not
sandbox evidence or release acceptance. Production readiness remains
nonconformant until M4. Deployment requires separate operator authorization.
