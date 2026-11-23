# Hold the follow-up production image

Decision date 2026-11-23 UTC. **Hold activation on wepp1, wepp2 and wepp3.** One fix-listed High advisory, CVE-2026-49014, affects the netCDF driver in both system GDAL and Rasterio’s private GDAL. Another 385 Debian Critical or High matches have no listed fix. Roger Lew owns the decision to accept residual risk for this exact image. The operator directed continued service on the current production image.

| Artifact | Identity |
| --- | --- |
| Clean build source | `cc335e36555a8ae3af65eaba12b1080b8a16b57d` |
| Common image | `sha256:27f3c409f45318dff99756cd854b7a03395f406da82c26dd3c0b6f9efbd4135b` |
| CI image containing all 29 common-image layers | `sha256:dcaf680cbf0557620ad54b946c770510d12f2fcc68347f1e9aad8897d1a44672` |
| Imported scan manifest | `8a9c94370963e38f84c136c43e5fc6d073e2e249f8519afa2244f6b5102a9b7f` |

## Security outcome

The same-database comparison found 2,299 primary Grype rows, down from 2,824 on the serving image and 2,497 on the first candidate. Both comparisons added zero finding groups. The raw Critical and High counts fell from 87 and 619 on the serving image to 49 and 342. After artifact-specific review, 386 Critical or High rows remain open across 98 advisory IDs. No applicable scanner-flagged known-exploited findings remain. The four original High npm findings are fixed. The full-lock audit reports 12 Moderate and one Low package records. [Independent security review](20261123_followup_security_review.md)

The private GDAL repair passed scientific readbacks but removes Rasterio’s ARG driver and adds 67 drivers. Available options are to qualify that driver change, maintain a repair that preserves the driver set, wait for compatible upstream packages or approve a time-limited exception. Any release decision also needs to cover the remaining Debian findings and the limits of scientific native coverage. [GDAL qualification](20261123_gdal_followup.md)

## Workflow verification

Forest1 built the clean source with production Compose settings and the recorded base image digests. The isolated CI stack on forest used the exact transferred image identities and the spatial extension packaged in the image. Frontend lint, 1,109 Jest tests and nine Node tests passed. The PATH and DEVAL reports, all 15 Rosetta objects, four external scientific source trees and 18 shared frontend assets passed independent readback. The only incidental Python runtime upgrade outside the reviewed vendor changes was Blosc2 4.15.0 to 4.16.1. Its installed native binaries matched the published wheel and both ordinary array and HDF5 roundtrips passed. [Independent correctness review](20261123_correctness_review.md) · [Native verification](20261123_followup_security_review.md)

The first full Python run stopped after 14,545 passes when the timestamp adapter’s p95 exceeded the legacy helper’s by 70 ms against a 50 ms limit. Three unchanged isolated reruns passed, with adapter p95 near 2.1 ms and legacy p95 between 28.7 and 29.6 ms. Both the original result and the reruns are retained.

The protected wepp2 bundle is indexed by the manifest above under `grype-remediation-cc335e365/`. Forest retains build, test, review and comparison evidence under `grype-remediation-20261123/gate2/` in the private deployment evidence store.
