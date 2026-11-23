# Hold the production common-image candidate

Decision date 2026-11-23 UTC. Hold activation on wepp1, wepp2 and wepp3. The repairs removed the applicable known-exploited Starlette finding, but 111 Critical or High rows still have a listed fix and unresolved applicability. Roger Lew owns production risk acceptance. This candidate has no approved exceptions.

| Artifact | Verified identity |
| --- | --- |
| Serving common image | `sha256:b6e0462f8a749eabb168ea398a4f8056c46305f2a003e04b026c0d5623567c94` |
| Candidate source | `65084ea5a1587cde24f8f9612ed87e70d5a8fd6b` |
| Candidate common image | `sha256:a116e2d21457a0e33a6070ab42518be0adead13ea9b53db5c55d9f7dfa8871d0` |
| Candidate bundle manifest | `8454e58f061d10774b960835e5bb51d281e2c8ebeea311b3aab9ed63ccd44a84` |
| Grype database used for both images | `cb2940548440e727d0614b801e7e9d634931107592117c5feae46e085f533faa` |

## Exposure and operator action

| Primary Grype rows | Serving image rematch | Candidate |
| --- | ---: | ---: |
| Critical | 87 | 59 |
| High | 619 | 445 |
| Medium | 533 | 428 |
| Low | 151 | 131 |
| Negligible | 1,431 | 1,431 |
| Unknown | 3 | 3 |
| Total | 2,824 | 2,497 |

The comparison removed 322 normalized finding groups and added zero. Both scans suppressed 334 rows. Of 504 remaining Critical or High primary rows, four have artifact-specific exclusions. Of the 500 open rows, 108 concern embedded Go components with a listed fix, three concern Python packages with a listed fix, and 389 are Debian findings without a listed fix. The two remaining known-exploited flags refer to a patched Python Brotli binary and an absent SSH daemon. The image audit found 12 moderate and one low npm dependency records, with zero High or Critical. These include four inherited advisory URLs.

Before releasing this candidate, resolve the three Python findings and establish reachability or qualify replacements for the affected Docker CLI, git-lfs and Quarto esbuild components. Review the Debian residuals and incomplete native coverage with the risk owner. The GDAL netCDF driver is present. Any exception requires an image-scoped operator decision under the existing release policy. Any repair that changes the image requires a new artifact identity, scan and qualification.

The current serving approval expires **2026-11-24 06:23:17.979322 UTC**. Roger Lew must address that expiry separately. The previous GDAL exception covers its original image only. Production continues on the recorded serving image.

## Evidence

The protected wepp2 store retained the candidate under `/workdir/weppcloud-deployments/.local/dependency-security/evidence/grype-remediation-65084ea5/<candidate bundle manifest>/bundle`. Forest retains the same-database rematch, original repair and build records and regression receipts under `/workdir/weppcloud-deployments/.local/dependency-security/evidence/grype-remediation-20261123/`. The independent correctness reviewer verified signed OAuth and rejection paths, actual PATH and DEVAL reports, compressed transfers, and scientific inputs and outputs. [Correctness review](20261123_correctness_review.md) · [Security review](20261123_security_review.md)
