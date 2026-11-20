# WEPP 261027

This release establishes the authorized new Linux numerical baseline for native
Windows/Linux parity. It inherits the 261026 late dry-day soil-return repair and
the 261021 physical-water and Gregorian-calendar changes.

## Changes

- GNU builds use the shared real32 math runtime: deterministic sine/cosine and
  double evaluation followed by one real32 conversion for the other supported
  elementary functions. Scalar and four-wide GNU vector paths share the policy.
- Plant coefficient arrays now cover the declared plant-type capacity instead
  of six entries. Adjacent COMMON values remain protected by a bounds regression.
- Unread UI year/day scratch accumulators are removed. Their 30-year allocation
  previously caused out-of-bounds writes in longer simulations.

The new math policy intentionally changes some Linux results, including daily
runoff timing in long simulations. Historical 261010, 261021 and 261026 binaries
remain unchanged; this release does not promise byte parity with those editions.
No hydrologic epsilon, relaxed comparator threshold or output filtering is used
to obtain platform agreement.

Linux retains the default 45,000-hillslope/15,000-channel/60,000-element watershed
capacity and 32-OFE hillslope capacity. The native Windows release supports
4,500 hillslopes, 1,500 channels, 6,000 elements and 32 OFEs. Its matched pair is
released and vendored into wepppy-win-bootstrap. See
[Windows build and mandatory parity gates](../docs/windows-build.md) and the
[Windows validation record](../docs/ablation/20261027-native-portability/windows-release-validation.md).
All 214 small-suite and 3,443 full medium-run output files match Linux after
CRLF normalization only.

## Validation and adoption

See [the validation record](../docs/ablation/20261027-native-portability/release-validation.md)
for exact source identities, binary hashes and completed release gates. The
preceding candidate campaign passed 22 hillslope cases and ten paired physical
controls across native Linux and Windows, plus the retained math probes.

Use matching `wepp_261027` and `wepp_261027_hill` executables and regenerate all
contributing hillslope and watershed outputs. PASS component version 3 and its
paired reader requirement remain unchanged. Release validation does not select
project defaults, vendor into downstream applications or deploy services.

The inherited return-only SRC3 path still uses midnight effective support;
actual within-day occurrence and physical hillslope peaks are not reconstructed.
Mixed-source, contour and daily-water-balance eligibility restrictions remain.
Signed routing withdrawals, clipping and universal physical closure remain open.
