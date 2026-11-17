# Shape-converter final4 qualification

## Exact candidate

- Image: `wepppy/shape-converter:vector-upload-m2-final4`
- Image ID: `sha256:ec801ab0c90e595dcc1a4f58b9be52398b8073a75a72591c34149b543a73ce03`
- Runtime user: `10001:10001`
- Parser source revision: `e172f9f8a11bd43e8471b96323add18af1559516`
- GeoParquet binary SHA-256: `160854839d237acb4c369bc15f97d5e51ae3841aaaca37777ba2353cfdd79c47`
- GeoParquet Cargo.lock SHA-256: `ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`
- Publication and deployment: not performed.

Final4 differs from the previously qualified final3 only in the application
readiness response: it exposes the already verified GeoParquet parser provenance
so receiver activation can compare the exact qualified binary, lock and source
revision. The parser dependency graph and binaries remain bound by the sidecar.

## Runtime and receiving-boundary evidence

The candidate ran as UID/GID 10001 with a read-only root, `no-new-privileges`,
all capabilities dropped, a 256 PID limit, 1.5 CPU limit, 1536 MiB memory limit,
and bounded `noexec,nosuid,nodev` scratch mounts. `/health/ready` returned
`status=ok`, `check=ready`, `geoparquet_parser=ready`, and the exact provenance
above.

The exact-image shared normalizer suite passed 5 tests. Additional real HTTP
receiving-boundary tests passed for Roads, AgFields, Omni run, Omni dry-run and
Batch Runner. Each boundary accepted GeoJSON, Shapefile ZIP, `.parquet`, and
`.geoparquet`; tests parsed the authoritative canonical GeoJSON and compared
properties plus Shapely geometry equality. Roads and AgFields controller tests
also injected receipt-commit failure and proved prior canonical bytes and
persisted state after a detached reload.

## Supply-chain evidence

The denied Docker-socket scan was replaced with a daemon-free scan of
`docker image save` output.

- SPDX 2.3: `20261117_m2_final4_image.spdx.json`, 103 packages and 2,845 files,
  SHA-256 `08ca9f99d6adcb94e1308e10233c0de81b8c5371ff8e35c8c5327305dff86860`.
- Grype 0.121.3: `20261117_m2_final4_grype.json`, SHA-256
  `ea3f87b8a648ca036f7ca1e3055463c692423170fe335706e384d40a1a0fd556`.
- Grype records: 59 High, 70 Medium, 17 Low, 50 Negligible and 16 Unknown.

The counts match final3 because the package and OS layers did not change. The
existing reachability/fix dispositions in `20261116_m2_validation.md` therefore
remain applicable. A fresh publication-time scan remains mandatory.

## Disposition

Final4 supersedes final3 as the local exact candidate. It is qualified for the
local receiver/review gate only. Registry publication, remote-host parity,
production integration and deployment require separate authorization.
