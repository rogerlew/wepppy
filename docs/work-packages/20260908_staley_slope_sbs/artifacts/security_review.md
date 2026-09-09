# Security review: StaleySlopeSbs

## Findings

| ID | Severity | Surface and exploit path | Required remediation | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | Medium | Malformed local TIFF metadata passed byte-range preflight into panic-prone GeoKey parsing, unit lookups, and multi-tiepoint regression. The original entry point could terminate without its explicit input-error contract. | Check known metadata shapes before decoding; contain remaining legacy decoder panics at the documented input boundary. Directly reject malformed fixtures without publishing products. | Resolved; final release CLI checks pass. |
| SEC-02 | Medium | Inflated overlapping strip byte counts caused repeated reads/allocations unrelated to the accepted cell payload. Aliased metadata tags could allocate gigabytes while the source file stayed small. GeoKey references independently expanded one shared ASCII region for every key. | Require exact uncompressed strip payload lengths, bound aggregate metadata, and cap/validate GeoKey counts and referenced ranges before decoding. | Resolved; exact strip, aggregate metadata and GeoKey bound checks pass. |
| SEC-03 | Medium | `Raster::new` rewrites NaN/Inf NoData and every nonfinite sample to -32768. NaN NoData therefore hides legitimate -32768 elevations; F32 overflow from a finite F64 NoData declaration reaches the same path. | Reject nonfinite declared NoData and F32 NoData overflow before decoding; document finite-sentinel preparation. | Resolved; both inputs fail preflight without products, and both canonical contracts state the finite-sentinel restriction and rationale. |

No high findings. Review does not authorize an upload endpoint or shared-host
service. Resource findings concern input-controlled work in this local tool,
not a demonstrated remote exploit.

## Metadata and triage

- Reviewer: independent `security_review` agent, 2026-09-09 UTC.
- Package: `20260908_staley_slope_sbs`.
- Source baseline: WBT `01381f54c469564abc6776ff97d70b4966340726`, plus
  uncommitted implementation reviewed during execution.
- Scope: WBT `whitebox-tools-app/src/tools/hydro_analysis/staley_slope_sbs.rs`,
  registration, `docs/staley_slope_sbs.md`, and `staley_slope_sbs` in both
  `whitebox_tools.py` and `WBT/whitebox_tools.py`. Read the relevant owned TIFF
  decoder, GeoKey helpers, and existing binding subprocess implementation.
- Security impact: **high** under the package process because file parsing and
  publication are new boundaries; dedicated review is required.
- Related correctness artifact: [correctness_review.md](correctness_review.md).
  Correctness/QA acceptance remains separate from this security gate.

Threat assumptions: callers select immutable trusted local regular files and
control a non-hostile existing output parent. No new route, upload, NoDb state,
RQ task, production binary installation, or authenticated service is introduced.
Canonicalized input symlinks are permitted under that local-file contract;
concurrent replacement by another principal is outside it.

## Evidence and validation

The independent stdlib-only probe is WBT
`tools/validate_staley_slope_sbs_security.py`. It builds tiny TIFFs directly,
invokes the actual release CLI with a 15-second per-case timeout, verifies return
codes and publication state, and writes `security_results.json`. Reproduce with:

```bash
python tools/validate_staley_slope_sbs_security.py \
  --binary target/release/whitebox_tools \
  --output /tmp/staley-security-review-fresh
```

Final direct verification passed **24/24 cases** using binary SHA-256
`6647d55c2d8d28680addd16adc4d9d406857a7ccb394cd4260a2d61d7d8ffc42`.
The exact case results are retained in
[security_validation.json](security_validation.json). The review Markdown
passed `wctl doc-lint` with zero errors/warnings; the probe passed `py_compile`.
A valid aligned 3×3 F64 UTM fixture completed, created all four products, and
reserved its directory with mode `0700`. Invalid GeoKey headers/counts/references,
unknown units, BYTE width, incorrectly typed scale, multiple tiepoints, invalid
UTF-8 NoData, and oversize cell dimensions returned code 1 without a new output
directory. Remaining legacy unit panics were caught and translated to
`InvalidInput`; Rust's default panic hook still printed its diagnostic.

Existing file and populated directory contents were preserved byte-for-byte;
an existing dangling output symlink stayed a symlink and its target was not
created. Missing parents failed explicitly. A subprocess-local `RLIMIT_FSIZE`
of 500 bytes forced a real buffered raster write failure: return code 1, private
reserved directory containing partial `slope.tif`, and no `summary.json`.
All three source SHA-256 values remained unchanged.

Resource-specific checks rejected a 128-byte strip for a 72-byte pixel payload
and five aliased 14 MiB tags sharing one file region. A bounded 128-key ASCII
reference expansion succeeded; static tracing established the previously
uncapped expansion to gigabytes. The follow-up implementation limits the
directory to 256 GeoKeys and validates references. The probe includes both a
permitted 128-extra-key fixture and a rejected 257-extra-key fixture, avoiding
an actual exhaustion attempt.

Evidence locations in WBT source: `preflight` enforces byte/layout bounds;
`GeoKeys::get_ifd_map` in `whitebox-raster/src/geotiff/geokeys.rs` explains the
reference expansion; the tool's deliberate `catch_unwind` handles residual
legacy metadata failures. Output publication uses `DirBuilder::create` followed
by fallible raster writes and `create_new` for the final summary. The owned
writer explicitly flushes its buffer before reporting success.

Final-binary follow-up inspected the empty-working-directory path correction,
whitespace handling in declared NoData, single-band PlanarConfiguration 2, and
the NoData conversion boundary. Whitespace NoData and planar-2 scalar inputs
complete successfully. A direct 3×3 flat DEM with valid -32768 elevations and
NaN NoData originally completed with zero valid slopes because of
`whitebox-raster/src/lib.rs`, `Raster::new` normalization. F32 NoData `1e100`
reached the same normalization despite a postdecode infinity check. Both now
fail before decoding. The **Numerical and input contract** sections in WBT
`docs/staley_slope_sbs.md` and WEPPpy
`wepppy/nodb/mods/postfire_debris_flow/docs/slope_sbs.md` require finite declared
NoData and finite Float32 representation, with the decoder-specific rationale.
The final maintained probe independently verified all 24 cases at
`/tmp/staley-security-final24`; its report replaces the earlier 20-case evidence.

## Surface checks

| Surface | Assessment |
| --- | --- |
| Valid-state preservation | Fresh valid products succeed; source files, populated outputs and expected missing output state retain their contracted behavior. A failed write remains visibly incomplete. The correctness review separately establishes scientific outputs and actual binding execution. |
| Auth/session/CSRF and run scope | No changed network or run-scoped API. Arbitrary operator-selected local paths are intentional, not a run-root authorization helper. |
| Secrets and logging | No credentials added. Summary records canonical source paths and noncryptographic fingerprints as documented. Residual decoder diagnostics can include metadata; keep this interface local. |
| Input and raster parsing | Narrow TIFF format, grid, unit, class, finite-data, and resource checks; findings above required additional metadata bounds. Explicit errors preserve prior products. |
| Filesystem publication | Atomic directory reservation rejects existing objects, including dangling symlinks. Private directory and fixed filenames contain writes under the trusted-parent assumption. Summary is the last completion marker. |
| Python/subprocess | Both additions pass argv entries through existing `Popen(..., shell=False)`; no shell interpolation or new executable selection mechanism. |
| Queue, NoDb, agent/MCP permissions | No change. |
| Network, external integrations, CI/CD | No new egress, dependency, build privilege, deployment, or supply-chain surface. |
| Integrity and concurrency | No source writes. Fresh-directory reservation handles competing ordinary invocations; hostile parent replacement is explicitly unsupported. FNV is diagnostic, not authentication. |

## Verdict and residual risk

**Gate: pass for the frozen local backend.** Unresolved findings: zero high,
zero medium, zero low. All three medium findings were closed through
implementation changes and direct checks of the rebuilt release CLI.
Scientific correctness, QA, terrain comparison and package-wide completion
remain separate gates.

The supported path remains memory-intensive near its declared raster limit;
these finite limits are not a service-level quota. The tool does not defend
against other principals replacing trusted inputs or parent directories, and
does not claim crash durability across power loss. Remaining decoder panics are
converted to input errors but may emit the default Rust diagnostic. None of
these limits authorizes future public parsing without a new security review.

Final security sign-off: independent `security_review` agent, 2026-09-09 UTC,
for release executable SHA-256
`6647d55c2d8d28680addd16adc4d9d406857a7ccb394cd4260a2d61d7d8ffc42`.
No risk acceptance has been requested or recorded; package-owner closeout is
recorded separately in the tracker.
