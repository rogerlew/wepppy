# Runtime dependency drift control

The first canonical rebuild resolved newer allowed dependencies than the running
forest baseline: FastAPI0.143.1 to0.162.0, narwhals2.27.1 to2.28.0,
pkginfo1.13 to1.13.3, python-dateutil2.9.0.post0 to3.0.0. These changes are
unrelated to RQ. Pinning their existing runtime versions in the authoritative
input prevents that drift; it does not upgrade those dependencies. RQ2.12 and
croniter6 remain the only intended installed-distribution delta. The initial
resolver comparison used freshly resolved old/new inputs, so it could not reveal
this difference from the actual installed baseline.

Evidence: `baseline-installed-packages.json` and `build-main.log`. A new canonical
build and final distribution comparison are required before cutover. Dashboard
retains gunicorn23.0.0, redis5.2.0 and its other existing pins; new croniter6 uses
pytz2022.1, matching the primary input. Python3.12 replaces dashboard3.8 because
RQ2.12 requires at least3.10. No runtime identity or mount changes.
