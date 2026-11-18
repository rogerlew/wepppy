# Shape-converter final5 qualification

## Exact candidate

- Image: `wepppy/shape-converter:vector-upload-m2-final5`
- Image ID: `sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`
- Runtime user: `10001:10001`
- Parser source revision: `e172f9f8a23c10774f87828181048c72188ba78a`
- GeoParquet binary SHA-256: `160854839d237acb4c369bc15f97d5e51ae3841aaaca37777ba2353cfdd79c47`
- GeoParquet Cargo.lock SHA-256: `ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`
- Publication and deployment: not performed.

Final5 supersedes and disqualifies final4. Final4 named a nonexistent source
revision and must not be published. The final5 revision resolves in Git, and
all seven source-file hashes in the embedded GeoParquet sidecar match `git show`
at that revision byte-for-byte. The Shapefile and GeoParquet binary hashes are
unchanged from the reviewed final3 implementation.

## Runtime and receiving-boundary evidence

The candidate ran as UID/GID 10001 with a read-only root, no new privileges,
all capabilities dropped, a 64-PID limit, one CPU, 768 MiB memory, an isolated
development network and a bounded `noexec,nosuid` scratch mount. Readiness
returned `status=ok`, `check=ready`, `geoparquet_parser=ready`, and the exact
binary, lock and source identities above.

The shape-converter suite passed 315 tests while bound to the exact parser
binaries and sidecars copied from final5. Ten exact-image integration selections
passed: five shared normalizer workflows and the actual Roads, AgFields, Omni
run, Omni dry-run and Batch HTTP boundaries. Every selection exercised GeoJSON,
Shapefile ZIP, `.parquet`, and `.geoparquet`, then parsed canonical GeoJSON and
compared properties plus Shapely geometry equality.

The first attempted rerun used stale first-generation Parquet fixtures and
correctly failed those Parquet cases as `invalid_vector`. The qualified rerun
used the retained final3-qualified fixture generation. Its GeoParquet SHA-256
values are `a084494cfefb81d29590a9380f7559aad90d8a7b10944c99f3b9a6ca42cc0890`
for the line and `039eba296e7c190a9235cb8ca9caa3d754cb2084054630dd0e4966229d9c1e17`
for the polygon. No failed run is counted as green.

## Daemon-free supply-chain evidence

`docker save` produced `/tmp/wepppy-shape-converter-final5.tar`, SHA-256
`c5b9f42ccf194780ef9b1099cb81f3fd605577bbeec89b6f10569d34db7cedbb`.
Its manifest config digest rehashes to the exact image ID above.

- SPDX 2.3: `20261117_m2_final5_image.spdx.json`, 103 packages and 2,845
  files, SHA-256 `bd4b97c3ea517e214626f2371aaa0fca399e8a8f08354ed91625ea1258305fed`.
- Grype 0.121.3: `20261117_m2_final5_grype.json`, SHA-256
  `5b21d0f4b905f00c10b306a2bfc8167e88e8700628c742009c6afa1501c89878`.
- Grype records: 59 High, 70 Medium, 17 Low, 50 Negligible and 16 Unknown.

The package graph and findings match final3/final4, so the reachability and
no-available-fix dispositions in `20261116_m2_validation.md` remain applicable.
A fresh publication-time scan remains mandatory.

## Disposition

Final5 is the local exact candidate for successor review. It is unpublished and
undeployed. Registry publication, remote-host parity, production integration
and deployment remain separately authorized gates.
