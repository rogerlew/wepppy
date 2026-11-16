# Independent Rust CLI Security Review

Date: 2026-11-14

Reviewer: independent `security_reviewer` agent

Commit: `fe5ac7c1c`

Security impact: high. Dedicated review required: yes.

Verdict: **FAIL / HOLD**. Critical 0; High 0; Medium 1; Low 3.

## Threat-model conclusion

Replacing GDAL/Fiona with the narrow Rust CLI materially removes the broad
hostile native-driver failure class. Same-container UID, mount, and internal-
network authority is acceptable in principle as an explicit residual risk. It
is not second-sandbox conformance.

## Findings

| ID | Severity | Surface | Finding | Required action |
|---|---|---|---|---|
| SEC-RUST-01 | Medium | Aggregate memory/availability | Individual limits can exceed the 1 GiB container envelope when combined: 700 MiB tmpfs/request quota, 512 MiB parser address space, 100 MiB retained upload, up to 256 MiB parser payload, and parent-side bytes/text/JSON/geometry/output amplification. Existing evidence reaches only about 84 MiB parser RSS. | Derive and enforce a whole-request memory invariant and retain exact-image near-ceiling recovery evidence. |
| SEC-RUST-02 | Low | Provenance | Readiness says `provenance=verified`, but validators bind only binary name/size/hash/version and do not recompute internal manifest/lock relationships. The generator hashes the rustup launcher rather than the selected compiler artifact. | Validate relationships and actual compiler identity, or report only binary binding. |
| SEC-RUST-03 | Low | Network contract | The specification both acknowledges inherited container networking and later claims parser networking is disabled. Compose supplies an internal bridge. | State the exact inherited internal-network authority consistently. |
| SEC-RUST-04 | Low | Path confinement | Source contains root/symlink/output-parent checks, but no direct executable regression covers outside-root input, symlinked components, or escaping output parent. | Add direct CLI path-boundary regressions. |

## Positive conclusions

- No Critical or High implementation finding was identified.
- Fiona/GDAL and production fallbacks are absent from the exact runtime.
- JSON IPC, minimal child environment, fixed diagnostics, atomic output, process-
  group timeout, and OS/resource controls are materially sound.
- The 17 unique High scanner advisories are acceptably unreachable under the
  current bounded service contract.
- The sidecar is correctly treated as metadata, not publisher authentication.

#656 must remain open. After SEC-RUST-01 closes, Low findings are corrected or
dispositioned, and the package owner acknowledges same-container authority, the
reviewer supports closing #656 as superseded by GDAL/Fiona removal, not as proof
of a second sandbox.
